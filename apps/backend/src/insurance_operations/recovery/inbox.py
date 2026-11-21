import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from uuid import UUID
from cryptography.fernet import Fernet, InvalidToken

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.database.models.hvac import HvacServiceRequest
from insurance_operations.database.models.recovery import RecoveryAttempt, RecoveryCase, RecoveryGrant, RecoveryPermission, RecoveryWebhook
from insurance_operations.hvac.locking import lock_business_schedule
from insurance_operations.recovery.domain import TERMINAL, audit, cancel_scheduled, channel_allowed, contact_time, permission_rows, policy_for, revoke_continuations, request_block, pending_opt_out
from insurance_operations.recovery.grants import create_grant
from insurance_operations.recovery.errors import conflict
from insurance_operations.settings import DatabaseSettings


def event_fingerprint(settings: DatabaseSettings, data: object) -> str:
    secret = settings.recovery_token_encryption_key
    if secret is None:
        raise conflict("Recovery encryption is unavailable.")
    canonical = {key: value for key, value in data.items() if not key.endswith("_ciphertext")} if isinstance(data, dict) else data
    return hmac.new(secret.get_secret_value().encode(), json.dumps(canonical, sort_keys=True).encode(), hashlib.sha256).hexdigest()


def encrypt_recipient(settings: DatabaseSettings, agency_id: UUID, phone: str) -> str:
    if settings.recovery_token_encryption_key is None:
        raise conflict("Recovery encryption is unavailable.")
    return Fernet(settings.recovery_token_encryption_key.get_secret_value().encode()).encrypt(
        json.dumps({"purpose": "recovery-webhook-recipient", "agency": str(agency_id), "phone": phone}).encode()).decode()


def decrypt_recipient(settings: DatabaseSettings, agency_id: UUID, ciphertext: str) -> str:
    if settings.recovery_token_encryption_key is None:
        raise conflict("Recovery encryption is unavailable.")
    try:
        data = json.loads(Fernet(settings.recovery_token_encryption_key.get_secret_value().encode()).decrypt(ciphertext.encode()))
        if data["purpose"] != "recovery-webhook-recipient" or data["agency"] != str(agency_id) or not isinstance(data["phone"], str):
            raise ValueError
        return str(data["phone"])
    except (InvalidToken, ValueError, TypeError, KeyError):
        raise conflict("Recovery recipient evidence cannot be decrypted.") from None


def enqueue(sessions: sessionmaker[Session], settings: DatabaseSettings, *, agency_id: UUID,
            provider: str, key: str, kind: str, data: dict[str, object], attempt_id: UUID | None = None) -> UUID:
    fingerprint = event_fingerprint(settings, {"event_kind": kind, **data})
    with sessions() as session, session.begin():
        identifier = session.execute(insert(RecoveryWebhook).values(agency_id=agency_id, provider=provider,
            event_key=key, kind=kind, data=data, attempt_id=attempt_id, fingerprint=fingerprint,
            received_at=datetime.now(UTC)).on_conflict_do_nothing(constraint="uq_recovery_webhook_identity")
            .returning(RecoveryWebhook.id)).scalar_one_or_none()
        if identifier:
            return identifier
        previous = session.scalar(select(RecoveryWebhook).where(RecoveryWebhook.agency_id == agency_id,
            RecoveryWebhook.provider == provider, RecoveryWebhook.event_key == key))
        if previous is None or previous.fingerprint != fingerprint:
            raise conflict("Provider event identity was reused with different data.")
        return previous.id


def suppress_destination(session: Session, agency_id: UUID, digest: str, evidence: str, phone: str | None = None) -> None:
    permission = session.scalar(select(RecoveryPermission).where(RecoveryPermission.agency_id == agency_id,
        RecoveryPermission.destination_digest == digest, RecoveryPermission.channel == "ALL").with_for_update())
    if permission is None:
        permission = RecoveryPermission(agency_id=agency_id, destination_digest=digest, channel="ALL")
        session.add(permission)
    permission.source, permission.evidence_reference = "VERIFIED_PROVIDER_STOP", evidence
    permission.revoked_at = permission.revoked_at or datetime.now(UTC)
    ids = select(RecoveryAttempt.recovery_case_id).where(RecoveryAttempt.agency_id == agency_id, RecoveryAttempt.recipient_digest == digest)
    query = select(RecoveryCase).where(RecoveryCase.agency_id == agency_id, RecoveryCase.status.not_in(list(TERMINAL)))
    if phone:
        query = query.join(HvacServiceRequest, (HvacServiceRequest.agency_id == RecoveryCase.agency_id) & (HvacServiceRequest.id == RecoveryCase.service_request_id)).where(HvacServiceRequest.customer_details["phone"].astext == phone)
    else:
        query = query.where(RecoveryCase.id.in_(ids))
    for case in session.scalars(query.with_for_update(of=RecoveryCase)):
        case.status, case.reason = "SUPPRESSED", "OPTED_OUT"
        cancel_scheduled(session, case)
        revoke_continuations(session, case)
    audit(session, agency_id, "LEAD_RECOVERY_OPT_OUT", {"scope": "ALL_AUTOMATED_RECOVERY"})


def process_event(sessions: sessionmaker[Session], identifier: UUID) -> None:
    with sessions() as session, session.begin():
        seed = session.get(RecoveryWebhook, identifier)
        if seed is None or seed.processed_at:
            return
        if lock_business_schedule(session, seed.agency_id, skip_locked=True) is None:
            return
        event = session.get(RecoveryWebhook, identifier, with_for_update=True)
        if event is None or event.processed_at:
            return
        settings = session.info.get("integration_settings")
        if not isinstance(settings, DatabaseSettings):
            return
        data, now = event.data, datetime.now(UTC)
        if event.attempt_id is None and event.kind == "RECEIPT":
            event.attempt_id = session.scalar(select(RecoveryAttempt.id).where(RecoveryAttempt.agency_id == event.agency_id,
                RecoveryAttempt.provider_reference == data.get("provider_reference"), RecoveryAttempt.provider == event.provider))
            if event.attempt_id is None and now < event.received_at + timedelta(minutes=10):
                event.next_attempt_at = now + timedelta(seconds=30)
                event.failure_code = "AWAITING_PROVIDER_BINDING"
                return
        if event.kind == "STOP":
            phone = decrypt_recipient(settings, event.agency_id, str(data["recipient_ciphertext"])) if data.get("recipient_ciphertext") else None
            suppress_destination(session, event.agency_id, str(data["recipient_digest"]), event.event_key, phone)
        elif event.kind in {"YES", "OTHER_REPLY"}:
            if not process_reply(session, settings, event):
                return
        else:
            process_receipt(session, event)
        event.processed_at = now


def process_reply(session: Session, settings: DatabaseSettings, event: RecoveryWebhook) -> bool:
    recent = list(session.scalars(select(RecoveryAttempt).where(RecoveryAttempt.agency_id == event.agency_id,
        RecoveryAttempt.channel == "SMS", RecoveryAttempt.provider == "TWILIO_SMS",
        RecoveryAttempt.recipient_digest == event.data.get("recipient_digest"),
        RecoveryAttempt.started_at >= event.received_at - timedelta(days=7),
        RecoveryAttempt.status.in_(["STARTED", "QUEUED", "UNKNOWN", "SENT", "DELIVERED"])).order_by(RecoveryAttempt.started_at.desc())))
    cases: dict[UUID, tuple[RecoveryCase, RecoveryAttempt]] = {}
    for attempt in recent:
        case = session.scalar(select(RecoveryCase).where(RecoveryCase.agency_id == event.agency_id,
            RecoveryCase.id == attempt.recovery_case_id).with_for_update())
        if case and case.status not in TERMINAL and case.id not in cases:
            cases[case.id] = (case, attempt)
    if len(cases) != 1:
        pending = session.scalar(select(RecoveryAttempt.id).where(RecoveryAttempt.agency_id == event.agency_id,
            RecoveryAttempt.channel == "SMS", RecoveryAttempt.recipient_digest == event.data.get("recipient_digest"),
            RecoveryAttempt.status.in_(["STARTED", "QUEUED", "UNKNOWN"]),
            RecoveryAttempt.started_at >= event.received_at - timedelta(minutes=5)).limit(1))
        if not cases and pending and datetime.now(UTC) < event.received_at + timedelta(minutes=5):
            event.next_attempt_at = datetime.now(UTC) + timedelta(seconds=30)
            return False
        event.failure_code = "REPLY_REQUEST_AMBIGUOUS" if cases else "REPLY_NO_SENT_RECOVERY"
        for case, _ in cases.values():
            case.status, case.paused, case.reason = "NEEDS_REVIEW", True, "REPLY_REQUEST_AMBIGUOUS"
            revoke_continuations(session, case)
        return True
    case, attempt = next(iter(cases.values()))
    if case.paused and case.reason != "CUSTOMER_CONTINUING_BOOKING":
        event.failure_code = "RECOVERY_PAUSED_BY_STAFF"
        return True
    if attempt.status not in {"SENT", "DELIVERED"} or not attempt.provider_reference:
        if datetime.now(UTC) < event.received_at + timedelta(minutes=5):
            event.next_attempt_at = datetime.now(UTC) + timedelta(seconds=30)
            return False
        case.status, case.paused, case.reason = "NEEDS_REVIEW", True, "REPLY_PROVIDER_OUTCOME_UNRESOLVED"
        event.failure_code = "REPLY_PROVIDER_OUTCOME_UNRESOLVED"
        return True
    request = session.get(HvacServiceRequest, case.service_request_id)
    if request is None or not channel_allowed(permission_rows(session, settings, request), "SMS"):
        event.failure_code = "RECOVERY_PERMISSION_REVOKED"
        return True
    if request_block(session, request) or pending_opt_out(session, case.agency_id, str(attempt.recipient_digest)):
        event.failure_code = "RECOVERY_REQUEST_INELIGIBLE"
        return True
    if event.kind != "YES":
        case.status, case.paused, case.reason = "NEEDS_REVIEW", True, "CUSTOMER_REPLY_REQUIRES_STAFF"
        cancel_scheduled(session, case)
        revoke_continuations(session, case)
        return True
    policy = policy_for(session, case.agency_id)
    due = contact_time(datetime.now(UTC), policy)
    if due >= case.created_at + timedelta(days=policy.expiry_days):
        event.failure_code = "RECOVERY_WINDOW_EXPIRED"
        return True
    grant = create_grant(session, attempt, active=True, expires_at=due + timedelta(minutes=30), reply_due_at=due)
    if grant.status != "ACTIVE" or grant.expires_at <= datetime.now(UTC) or grant.reply_status in {"FAILED", "UNKNOWN", "CANCELLED"}:
        case.status, case.paused, case.reason = "NEEDS_REVIEW", True, "CONTINUATION_ALREADY_REQUESTED"
        event.failure_code = "CONTINUATION_ALREADY_REQUESTED"
        return True
    case.status, case.paused, case.reason = "AWAITING_RESPONSE", True, "CUSTOMER_CONTINUING_BOOKING"
    cancel_scheduled(session, case)
    audit(session, case.agency_id, "LEAD_RECOVERY_CONTINUATION_REQUESTED", {"case_id": str(case.id), "attempt_id": str(attempt.id)})
    return True


def process_receipt(session: Session, event: RecoveryWebhook) -> None:
    if event.attempt_id is None:
        event.failure_code = "PROVIDER_EVENT_UNBOUND"
        return
    attempt = session.scalar(select(RecoveryAttempt).where(RecoveryAttempt.agency_id == event.agency_id,
        RecoveryAttempt.id == event.attempt_id).with_for_update())
    if attempt is None:
        event.failure_code = "PROVIDER_EVENT_UNBOUND"
        return
    case = session.scalar(select(RecoveryCase).where(RecoveryCase.agency_id == event.agency_id,
        RecoveryCase.id == attempt.recovery_case_id).with_for_update())
    if case is None:
        return
    reference = str(event.data.get("provider_reference") or "")
    expected_provider = "TWILIO_SMS" if event.provider == "TWILIO_SMS" else "ELEVENLABS_RECOVERY"
    if attempt.provider != expected_provider or not reference:
        event.failure_code = "PROVIDER_REFERENCE_MISMATCH"
        return
    if event.data.get("opt_out") is True and attempt.recipient_digest:
        settings = session.info.get("integration_settings")
        request = session.get(HvacServiceRequest, case.service_request_id)
        phone = str(request.customer_details.get("phone") or "") if request else None
        if phone and isinstance(settings, DatabaseSettings):
            from insurance_operations.recovery.domain import destination_digest

            if destination_digest(settings, case.agency_id, phone) != attempt.recipient_digest:
                phone = None
        suppress_destination(session, case.agency_id, attempt.recipient_digest, event.event_key, phone)
    grant = None
    if event.data.get("reply_grant_id"):
        grant = session.scalar(select(RecoveryGrant).where(RecoveryGrant.agency_id == event.agency_id,
            RecoveryGrant.id == UUID(str(event.data["reply_grant_id"])), RecoveryGrant.attempt_id == attempt.id).with_for_update())
        if grant is None or grant.reply_status is None:
            event.failure_code = "PROVIDER_EVENT_UNBOUND"
            return
        if grant.reply_provider_reference and grant.reply_provider_reference != reference:
            event.failure_code = "PROVIDER_REFERENCE_MISMATCH"
            return
        grant.reply_provider_reference = reference
        current = grant.reply_status
    else:
        if attempt.provider_reference and attempt.provider_reference != reference:
            event.failure_code = "PROVIDER_REFERENCE_MISMATCH"
            return
        attempt.provider_reference = reference
        current = attempt.status
    incoming = str(event.data.get("status") or "UNKNOWN")
    order = {"STARTED": 0, "UNKNOWN": 0, "QUEUED": 1, "SENT": 2, "DELIVERED": 3}
    if incoming == "FAILED" and current != "CANCELLED":
        if grant:
            grant.reply_status, grant.failure_code = "FAILED", "CONTINUATION_REPLY_FAILED"
        else:
            attempt.status, attempt.failure_code = "FAILED", "PROVIDER_REPORTED_FAILURE"
        if case.status not in TERMINAL:
            case.status, case.reason = "NEEDS_REVIEW", "CONTINUATION_REPLY_FAILED" if grant else "PROVIDER_REPORTED_FAILURE"
    elif current in order and incoming in order and order[incoming] > order[current]:
        if grant:
            grant.reply_status, grant.failure_code = incoming, None
            if grant.status == "ACTIVE" and case.status == "NEEDS_REVIEW" and case.reason == "CONTINUATION_REPLY_UNKNOWN":
                case.status, case.paused, case.reason = "AWAITING_RESPONSE", True, "CUSTOMER_CONTINUING_BOOKING"
        else:
            attempt.status, attempt.failure_code = incoming, None
            if case.status == "NEEDS_REVIEW" and case.reason in {"PROVIDER_OUTCOME_UNRESOLVED", "INTERRUPTED_PROVIDER_ATTEMPT", "PROVIDER_REFERENCE_MISSING"}:
                case.status, case.reason = "AWAITING_RESPONSE", None
    if event.data.get("terminal") is True:
        attempt.provider_terminal_at = datetime.now(UTC)
        if attempt.channel == "VOICE":
            voice_grant = session.scalar(select(RecoveryGrant).where(RecoveryGrant.agency_id == attempt.agency_id, RecoveryGrant.attempt_id == attempt.id).with_for_update())
            if voice_grant and voice_grant.status in {"WAITING", "ACTIVE"} and not voice_grant.approved_at:
                voice_grant.status = "EXPIRED"
                if case.status not in TERMINAL:
                    case.paused = False
    audit(session, case.agency_id, "LEAD_RECOVERY_RECEIPT_APPLIED", {"case_id": str(case.id), "attempt_id": str(attempt.id), "status": incoming, "reply": bool(grant)})
