from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.database.models.recovery import RecoveryAttempt, RecoveryCase, RecoveryGrant
from insurance_operations.errors import ApiError
from insurance_operations.hvac.locking import lock_business_schedule
from insurance_operations.recovery.configuration import channel_configured
from insurance_operations.recovery.domain import TERMINAL, audit, contact_time, destination_digest, policy_for
from insurance_operations.recovery.grants import grant_token, scope
from insurance_operations.recovery.inbox import enqueue
from insurance_operations.recovery.providers import DeliveryOutcome, RecoveryContact, sms_message
from insurance_operations.recovery.transports import ElevenLabsRecoveryVoice, SMS_STATUSES, TransportFailure, TwilioRecoverySms
from insurance_operations.settings import DatabaseSettings


def reply_body(settings: DatabaseSettings, grant: RecoveryGrant, attempt: RecoveryAttempt) -> str:
    config = attempt.dispatch_configuration or {}
    origin = str(config.get("web_origin") or "").rstrip("/")
    if not origin or origin != str(settings.recovery_web_origin).rstrip("/"):
        raise ApiError(status_code=409, code="RECOVERY_CONFIGURATION_CHANGED", message="Recovery origin changed; staff review is required.")
    return f"{config.get('business_name', 'HVAC service')}: Continue your requested booking here: {origin}/recover#token={grant_token(settings, grant)} This link expires in 30 minutes. Reply STOP to opt out."


def deliver_reply(sessions: sessionmaker[Session], identifier: UUID) -> None:
    with sessions() as session, session.begin():
        seed = session.get(RecoveryGrant, identifier)
        if seed is None or lock_business_schedule(session, seed.agency_id, skip_locked=True) is None:
            return
        grant = session.get(RecoveryGrant, identifier, with_for_update=True)
        settings = session.info.get("integration_settings")
        if grant is None or not isinstance(settings, DatabaseSettings):
            return
        if grant.reply_status == "STARTED":
            if grant.reply_started_at and grant.reply_started_at < datetime.now(UTC) - timedelta(minutes=5):
                grant.reply_status, grant.failure_code = "UNKNOWN", "CONTINUATION_REPLY_UNKNOWN"
                case = session.get(RecoveryCase, grant.recovery_case_id, with_for_update=True)
                if case and case.status not in TERMINAL:
                    case.status, case.reason = "NEEDS_REVIEW", "CONTINUATION_REPLY_UNKNOWN"
            return
        if grant.reply_status != "PENDING" or grant.reply_due_at is None or grant.reply_due_at > datetime.now(UTC):
            return
        try:
            case, attempt, request = scope(session, settings, grant)
        except ApiError:
            grant.reply_status, grant.failure_code = "CANCELLED", "RECOVERY_AUTHORIZATION_CHANGED"
            return
        policy = policy_for(session, grant.agency_id)
        if not settings.recovery_enabled or not policy.enabled or "SMS" not in policy.channels or not channel_configured(settings, grant.agency_id, "SMS"):
            grant.reply_status, grant.failure_code = "CANCELLED", "RECOVERY_AUTOMATION_DISABLED"
            return
        now = datetime.now(UTC)
        due = contact_time(now, policy)
        if due > now:
            if due >= grant.expires_at:
                grant.reply_status, grant.failure_code = "CANCELLED", "CONTINUATION_LINK_EXPIRED"
            else:
                grant.reply_due_at = due
            return
        grant.reply_status, grant.reply_started_at = "STARTED", now
    with sessions() as session, session.begin():
        lock_business_schedule(session, seed.agency_id)
        grant = session.get(RecoveryGrant, identifier, with_for_update=True)
        if grant is None or grant.reply_status != "STARTED":
            return
        settings = session.info.get("integration_settings")
        if not isinstance(settings, DatabaseSettings):
            raise RuntimeError("Recovery settings are unavailable")
        try:
            case, attempt, request = scope(session, settings, grant)
            policy = policy_for(session, grant.agency_id)
            if not settings.recovery_enabled or not policy.enabled or "SMS" not in policy.channels:
                raise ApiError(status_code=409, code="RECOVERY_DISABLED", message="Recovery is disabled.")
            if contact_time(datetime.now(UTC), policy) > datetime.now(UTC):
                raise ApiError(status_code=409, code="RECOVERY_CONTACT_WINDOW_CHANGED", message="The permitted contact window changed before delivery.")
            contact = RecoveryContact(grant.agency_id, case.id, request.id,
                str((attempt.dispatch_configuration or {}).get("business_name") or ""), str(request.customer_details["phone"]),
                f"recovery-reply:{grant.id}", attempt_id=attempt.id, configuration=attempt.dispatch_configuration)
            body = reply_body(settings, grant, attempt)
        except ApiError:
            grant.reply_status, grant.failure_code = "CANCELLED", "RECOVERY_AUTHORIZATION_CHANGED"
            return
        try:
            result = TwilioRecoverySms(settings).send(contact, body=body, reply_grant_id=grant.id)
        except Exception:
            result = DeliveryOutcome("UNKNOWN", failure_code="CONTINUATION_REPLY_UNKNOWN")
        grant.reply_status, grant.reply_provider_reference = result.status, result.provider_reference
        grant.reply_completed_at, grant.failure_code = datetime.now(UTC), result.failure_code
        if result.status in {"FAILED", "UNKNOWN"} and case.status not in TERMINAL:
            case.status, case.reason = "NEEDS_REVIEW", "CONTINUATION_REPLY_UNKNOWN" if result.status == "UNKNOWN" else "CONTINUATION_REPLY_FAILED"
        audit(session, grant.agency_id, "LEAD_RECOVERY_CONTINUATION_REPLY", {"grant_id": str(grant.id), "status": result.status})


def read_provider_outcome(settings: DatabaseSettings, attempt: RecoveryAttempt, reference: str,
                          *, grant: RecoveryGrant | None = None) -> dict[str, object]:
    config = attempt.dispatch_configuration or {}
    if attempt.provider == "TWILIO_SMS":
        if config.get("account_sid") != settings.recovery_twilio_account_sid:
            raise TransportFailure("SMS_ACCOUNT_CHANGED")
        result = TwilioRecoverySms(settings).message(reference)
        try:
            created = parsedate_to_datetime(str(result.get("date_created") or ""))
        except (ValueError, TypeError):
            raise TransportFailure("SMS_RECEIPT_MISMATCH") from None
        started = grant.reply_started_at if grant else attempt.started_at
        if started is None or created.tzinfo is None or not started - timedelta(seconds=30) <= created <= started + timedelta(minutes=5):
            raise TransportFailure("SMS_RECEIPT_MISMATCH")
        if (result.get("from") != config.get("from_number") or
            destination_digest(settings, attempt.agency_id, str(result.get("to") or "")) != attempt.recipient_digest or
            result.get("body") != (reply_body(settings, grant, attempt) if grant else sms_message(str(config.get("business_name") or "")))):
            raise TransportFailure("SMS_RECEIPT_MISMATCH")
        return {"provider_reference": reference, "status": SMS_STATUSES.get(str(result.get("status")), "UNKNOWN"),
            "terminal": False, "reply_grant_id": str(grant.id) if grant else None}
    if attempt.provider == "ELEVENLABS_RECOVERY" and grant is None:
        if config.get("agent_id") != settings.recovery_voice_agent_id:
            raise TransportFailure("VOICE_AGENT_CHANGED")
        result = ElevenLabsRecoveryVoice(settings).conversation(reference)
        variables = (result.get("conversation_initiation_client_data") or {}).get("dynamic_variables") or {}
        if variables.get("recovery_attempt_id") != str(attempt.id):
            raise TransportFailure("VOICE_REFERENCE_MISMATCH")
        return {"provider_reference": reference, "status": "FAILED" if result.get("status") == "failed" else "SENT",
            "terminal": result.get("status") in {"done", "failed"}}
    raise TransportFailure("RECOVERY_PROVIDER_UNSUPPORTED")


def reconcile_attempt(sessions: sessionmaker[Session], identifier: UUID) -> None:
    with sessions() as session, session.begin():
        attempt = session.get(RecoveryAttempt, identifier, with_for_update=True)
        settings = session.info.get("integration_settings")
        if attempt is None or not isinstance(settings, DatabaseSettings):
            return
        now = datetime.now(UTC)
        if attempt.last_reconciled_at and attempt.last_reconciled_at > now - timedelta(seconds=30):
            return
        attempt.last_reconciled_at = now
        grant = session.scalar(select(RecoveryGrant).where(RecoveryGrant.agency_id == attempt.agency_id,
            RecoveryGrant.attempt_id == attempt.id))
        references = [(attempt.provider_reference, None)] if attempt.provider_reference and (
            attempt.status in {"QUEUED", "UNKNOWN"} or attempt.channel == "VOICE" and attempt.provider_terminal_at is None) else []
        if grant and grant.reply_status in {"QUEUED", "UNKNOWN"} and grant.reply_provider_reference:
            references.append((grant.reply_provider_reference, grant))
    for reference, reply_grant in references:
        try:
            data = read_provider_outcome(settings, attempt, str(reference), grant=reply_grant)
            enqueue(sessions, settings, agency_id=attempt.agency_id, provider=str(attempt.provider), attempt_id=attempt.id,
                key=f"read:{reference}:{data['status']}:{data['terminal']}", kind="RECEIPT", data=data)
        except (TransportFailure, ApiError):
            continue


def expire_continuation(sessions: sessionmaker[Session], identifier: UUID) -> None:
    with sessions() as session, session.begin():
        seed = session.get(RecoveryGrant, identifier)
        if seed is None or lock_business_schedule(session, seed.agency_id, skip_locked=True) is None:
            return
        grant = session.get(RecoveryGrant, identifier, with_for_update=True)
        if grant is None or grant.status not in {"WAITING", "ACTIVE"} or grant.expires_at > datetime.now(UTC):
            return
        case = session.get(RecoveryCase, grant.recovery_case_id, with_for_update=True)
        if grant.approved_at:
            if case and case.status not in TERMINAL and case.reason != "BOOKING_CONFIRMATION_REQUIRES_REVIEW":
                case.status, case.paused, case.reason = "NEEDS_REVIEW", True, "BOOKING_CONFIRMATION_REQUIRES_REVIEW"
            return
        grant.status = "EXPIRED"
        if grant.reply_status == "PENDING":
            grant.reply_status, grant.failure_code = "CANCELLED", "CONTINUATION_LINK_EXPIRED"
        if case and case.status not in TERMINAL and case.reason == "CUSTOMER_CONTINUING_BOOKING":
            case.paused, case.reason = False, "CONTINUATION_EXPIRED"
        audit(session, grant.agency_id, "LEAD_RECOVERY_CONTINUATION_EXPIRED", {"grant_id": str(grant.id)})
