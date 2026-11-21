from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from functools import partial
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.database.models.hvac import Appointment, BusinessSchedule, HvacServiceRequest
from insurance_operations.database.models.identity import Agency
from insurance_operations.database.models.recovery import RecoveryAiConnection, RecoveryAttempt, RecoveryCase, RecoveryPolicy, RecoveryGrant
from insurance_operations.hvac.locking import lock_business_schedule
from insurance_operations.job_execution import check_job_deadline
from insurance_operations.recovery.domain import TERMINAL, audit, cancel_scheduled, channel_allowed, contact_time, permission_rows, policy_for, request_block, stop_for_booking
from insurance_operations.recovery.providers import DeliveryOutcome, RecoveryContact, RecoveryDeliveryProvider
from insurance_operations.settings import DatabaseSettings
from insurance_operations.recovery.transports import ConfiguredRecoveryProvider
from insurance_operations.recovery.grants import create_grant, grant_token
from insurance_operations.recovery.domain import destination_digest
from insurance_operations.recovery.domain import pending_opt_out
from insurance_operations.telephony.outbound.destinations import validate_us_destination
from insurance_operations.errors import ApiError


def eligibility(session: Session, settings: DatabaseSettings, case: RecoveryCase, provider: RecoveryDeliveryProvider, now: datetime, executing: RecoveryAttempt | None = None) -> tuple[str | None, datetime | None, str | None]:
    request = session.get(HvacServiceRequest, case.service_request_id)
    if request is None or request.agency_id != case.agency_id:
        return None, None, "REQUEST_UNAVAILABLE"
    booked = session.scalar(select(Appointment).where(Appointment.agency_id == case.agency_id, Appointment.service_request_id == request.id, Appointment.status == "CONFIRMED"))
    if booked:
        stop_for_booking(session, booked)
        return None, None, "ALREADY_BOOKED"
    block = request_block(session, request)
    if block:
        return None, None, block
    policy = policy_for(session, case.agency_id)
    schedule = session.get(BusinessSchedule, case.agency_id)
    if schedule is None or policy.timezone != schedule.configuration.get("timezone"):
        return None, None, "AGENCY_TIMEZONE_CHANGED"
    if not settings.recovery_enabled or not policy.enabled or case.paused:
        return None, None, "AUTOMATION_DISABLED"
    attempts = list(session.scalars(select(RecoveryAttempt).where(RecoveryAttempt.agency_id == case.agency_id, RecoveryAttempt.recovery_case_id == case.id).order_by(RecoveryAttempt.attempt_number)))
    attempts = [attempt for attempt in attempts if executing is None or attempt.id != executing.id]
    continuations = list(session.scalars(select(RecoveryGrant).where(RecoveryGrant.agency_id == case.agency_id,
        RecoveryGrant.recovery_case_id == case.id, RecoveryGrant.attempt_id != executing.id if executing else True)))
    if any(grant.reply_status in {"STARTED", "QUEUED", "UNKNOWN"} for grant in continuations):
        return None, None, "PROVIDER_OUTCOME_UNRESOLVED"
    if any(grant.status in {"WAITING", "ACTIVE"} and grant.expires_at > now for grant in continuations):
        return None, None, "CUSTOMER_CONTINUING_BOOKING"
    if any(a.status in {"UNKNOWN", "STARTED", "QUEUED"} for a in attempts):
        return None, None, "PROVIDER_OUTCOME_UNRESOLVED"
    if now >= case.created_at + timedelta(days=policy.expiry_days) or len(attempts) >= policy.max_attempts:
        return None, None, "ATTEMPT_LIMIT_REACHED"
    permissions = permission_rows(session, settings, request)
    phone = str(request.customer_details.get("phone") or "")
    try:
        validate_us_destination(phone)
    except ApiError:
        return None, None, "RECOVERY_RECIPIENT_INVALID"
    channels = [channel for channel in policy.channels if channel_allowed(permissions, channel)]
    if executing:
        channels = [channel for channel in channels if channel == executing.channel]
    if not channels:
        revoked = any(row.revoked_at is not None for row in permissions)
        return None, None, "OPTED_OUT" if revoked else "EXPLICIT_PERMISSION_REQUIRED"
    ai = session.get(RecoveryAiConnection, case.agency_id)
    channels = [channel for channel in channels if channel == "VOICE" or (ai is not None and ai.status == "CONNECTED")]
    if not channels:
        return None, None, "AI_MODEL_NOT_CONNECTED"
    channels = [channel for channel in channels if provider.available(case.agency_id, channel)]
    if not channels:
        return None, None, "RECOVERY_PROVIDER_UNAVAILABLE"
    digest = destination_digest(settings, case.agency_id, phone)
    if pending_opt_out(session, case.agency_id, digest):
        return None, None, "OPTED_OUT"
    recent = list(session.scalars(select(RecoveryAttempt).where(
        RecoveryAttempt.agency_id == case.agency_id, RecoveryAttempt.recipient_digest == digest,
        RecoveryAttempt.recovery_case_id != case.id, RecoveryAttempt.started_at.is_not(None),
        RecoveryAttempt.started_at > now - timedelta(hours=policy.interval_hours))))
    active_voice = session.scalar(select(RecoveryAttempt.id).where(RecoveryAttempt.agency_id == case.agency_id,
        RecoveryAttempt.channel == "VOICE", RecoveryAttempt.started_at.is_not(None),
        RecoveryAttempt.provider_terminal_at.is_(None), RecoveryAttempt.status.in_(["STARTED", "QUEUED", "SENT", "UNKNOWN"]),
        RecoveryAttempt.id != executing.id if executing else True).limit(1))
    if "VOICE" in channels and active_voice:
        channels = [channel for channel in channels if channel != "VOICE"]
        if not channels:
            return None, None, "VOICE_CONCURRENCY_LIMIT"
    today = now.astimezone(ZoneInfo(policy.timezone)).date()
    daily = list(session.scalars(select(RecoveryAttempt).where(RecoveryAttempt.agency_id == case.agency_id,
        RecoveryAttempt.started_at >= now - timedelta(days=2))))
    channels = [channel for channel in channels if sum(1 for row in daily
        if row.channel == channel and row.started_at and row.started_at.astimezone(ZoneInfo(policy.timezone)).date() == today
        and (executing is None or row.id != executing.id)) < (settings.recovery_sms_daily_limit if channel == "SMS" else settings.recovery_voice_daily_limit)]
    if not channels:
        return None, None, "AGENCY_DAILY_CONTACT_LIMIT"
    earliest = max(now, case.eligible_at)
    for previous in recent:
        if previous.started_at:
            earliest = max(earliest, previous.started_at + timedelta(hours=policy.interval_hours))
    for attempt in attempts:
        earliest = max(earliest, (attempt.started_at or attempt.scheduled_at) + timedelta(hours=policy.interval_hours))
    for hold in session.scalars(select(Appointment).where(Appointment.agency_id == case.agency_id, Appointment.service_request_id == request.id, Appointment.status == "HELD", Appointment.hold_expires_at > now)):
        earliest = max(earliest, hold.hold_expires_at + timedelta(minutes=policy.booking_delay_minutes))
    due = contact_time(earliest, policy)
    if due >= case.created_at + timedelta(days=policy.expiry_days):
        return None, None, "ATTEMPT_LIMIT_REACHED"
    return channels[0], due, None


def apply_block(session: Session, case: RecoveryCase, reason: str) -> None:
    if case.status in TERMINAL:
        return
    case.reason = reason
    if reason == "AUTOMATION_DISABLED":
        case.updated_at = datetime.now(UTC)
        return
    if reason in {"VOICE_CONCURRENCY_LIMIT", "AGENCY_DAILY_CONTACT_LIMIT"}:
        case.eligible_at = contact_time(datetime.now(UTC) + timedelta(minutes=5 if reason == "VOICE_CONCURRENCY_LIMIT" else 60), policy_for(session, case.agency_id))
        return
    case.status = "SUPPRESSED" if reason == "OPTED_OUT" else "CLOSED" if reason == "ATTEMPT_LIMIT_REACHED" else "NEEDS_REVIEW"
    cancel_scheduled(session, case)


def schedule_case(session: Session, settings: DatabaseSettings, case: RecoveryCase, provider: RecoveryDeliveryProvider, now: datetime) -> None:
    channel, due, reason = eligibility(session, settings, case, provider, now)
    if reason:
        apply_block(session, case, reason)
        return
    if channel is None or due is None:
        raise RuntimeError("Recovery scheduling eligibility is incomplete")
    attempts = list(session.scalars(select(RecoveryAttempt).where(RecoveryAttempt.agency_id == case.agency_id, RecoveryAttempt.recovery_case_id == case.id)))
    if any(a.status == "SCHEDULED" for a in attempts):
        return
    number = len(attempts) + 1
    session.add(RecoveryAttempt(agency_id=case.agency_id, recovery_case_id=case.id, channel=channel, attempt_number=number, status="SCHEDULED", scheduled_at=due, idempotency_key=f"recovery:{case.id}:{number}"))
    case.status, case.reason = "SCHEDULED", None
    audit(session, case.agency_id, "LEAD_RECOVERY_SCHEDULED", {"case_id": str(case.id), "attempt_number": number, "channel": channel})


def process_case(sessions: sessionmaker[Session], case_id: UUID, provider: RecoveryDeliveryProvider | None = None) -> None:
    with sessions() as session, session.begin():
        seed = session.get(RecoveryCase, case_id)
        if seed is None or lock_business_schedule(session, seed.agency_id, skip_locked=True) is None:
            return
        case = session.scalar(select(RecoveryCase).where(RecoveryCase.id == case_id, RecoveryCase.agency_id == seed.agency_id).with_for_update(skip_locked=True))
        settings = session.info.get("integration_settings")
        if case is None or case.status in TERMINAL or not isinstance(settings, DatabaseSettings):
            return
        adapter = provider or ConfiguredRecoveryProvider(settings)
        now = datetime.now(UTC)
        if case.status == "IN_PROGRESS":
            stale = list(session.scalars(select(RecoveryAttempt).where(RecoveryAttempt.recovery_case_id == case.id, RecoveryAttempt.status == "STARTED", RecoveryAttempt.started_at < now - timedelta(minutes=5))))
            for attempt in stale:
                attempt.status, attempt.failure_code = "UNKNOWN", "INTERRUPTED_PROVIDER_ATTEMPT"
            if stale:
                case.status, case.reason = "NEEDS_REVIEW", "PROVIDER_OUTCOME_UNRESOLVED"
            return
        if case.eligible_at > now:
            return
        attempt = session.scalar(select(RecoveryAttempt).where(RecoveryAttempt.agency_id == case.agency_id, RecoveryAttempt.recovery_case_id == case.id, RecoveryAttempt.status == "SCHEDULED").with_for_update())
        if attempt is None:
            schedule_case(session, settings, case, adapter, now)
            return
        if attempt.scheduled_at > now:
            return
        channel, due, reason = eligibility(session, settings, case, adapter, now, executing=attempt)
        if reason:
            apply_block(session, case, reason)
            return
        request = session.get(HvacServiceRequest, case.service_request_id)
        if request is None or channel is None or due is None:
            return
        if due > now:
            attempt.scheduled_at = due
            return
        check_job_deadline()
        attempt.status, attempt.started_at = "STARTED", now
        case.status = "IN_PROGRESS"
        agency = session.get(Agency, case.agency_id)
        if agency is None:
            raise RuntimeError("Recovery agency is unavailable")
        configuration = {"business_name": agency.name, "api_origin": settings.recovery_public_api_origin,
            "web_origin": settings.recovery_web_origin,
            "from_number": settings.recovery_sms_from_number if attempt.channel == "SMS" else settings.recovery_voice_from_number,
            "account_sid": settings.recovery_twilio_account_sid if attempt.channel == "SMS" else None,
            "agent_id": settings.recovery_voice_agent_id if attempt.channel == "VOICE" else None,
            "phone_id": settings.recovery_voice_phone_number_id if attempt.channel == "VOICE" else None}
        attempt.provider = "TWILIO_SMS" if attempt.channel == "SMS" else "ELEVENLABS_RECOVERY"
        attempt.recipient_digest = destination_digest(settings, case.agency_id, str(request.customer_details["phone"]))
        attempt.dispatch_configuration = configuration
        grant = create_grant(session, attempt, active=False, expires_at=now + timedelta(seconds=settings.recovery_voice_max_seconds + 120)) if attempt.channel == "VOICE" else None
        contact = RecoveryContact(case.agency_id, case.id, case.service_request_id, agency.name,
            str(request.customer_details["phone"]), attempt.idempotency_key, attempt_id=attempt.id,
            grant_token=grant_token(settings, grant) if grant else None, configuration=configuration)
        attempt_id = attempt.id
        contact_channel = attempt.channel
    # STARTED survives rollback if the process or connection disappears during I/O.
    with sessions() as session, session.begin():
        lock_business_schedule(session, contact.agency_id)
        case = session.scalar(select(RecoveryCase).where(RecoveryCase.id == case_id, RecoveryCase.agency_id == contact.agency_id).with_for_update())
        attempt = session.get(RecoveryAttempt, attempt_id, with_for_update=True)
        if case is None or attempt is None or attempt.status != "STARTED":
            return
        settings = session.info.get("integration_settings")
        if not isinstance(settings, DatabaseSettings):
            raise RuntimeError("Recovery settings are unavailable")
        if case.status in TERMINAL:
            attempt.status, attempt.completed_at = "CANCELLED", datetime.now(UTC)
            return
        _, due, reason = eligibility(session, settings, case, adapter, datetime.now(UTC), executing=attempt)
        if reason or due is None or due > datetime.now(UTC):
            attempt.status, attempt.failure_code, attempt.completed_at = "CANCELLED", reason or "CONTACT_WINDOW_CHANGED", datetime.now(UTC)
            apply_block(session, case, reason or "CONTACT_WINDOW_CHANGED")
            if case.status == "IN_PROGRESS":
                case.status = "NEEDS_REVIEW"
            return
        try:
            check_job_deadline()
            outcome = adapter.send(contact, contact_channel)
            if outcome.status in {"QUEUED", "SENT", "DELIVERED"} and not outcome.provider_reference:
                outcome = DeliveryOutcome("UNKNOWN", failure_code="PROVIDER_REFERENCE_MISSING")
        except Exception:
            outcome = DeliveryOutcome("UNKNOWN", failure_code="PROVIDER_OUTCOME_UNRESOLVED")
        attempt.status, attempt.provider_reference, attempt.failure_code = outcome.status, outcome.provider_reference, outcome.failure_code
        if attempt.channel == "VOICE" and outcome.status in {"FAILED", "CANCELLED"}:
            attempt.provider_terminal_at = datetime.now(UTC)
            from insurance_operations.recovery.grants import revoke_case_grants

            revoke_case_grants(session, case)
        attempt.completed_at = datetime.now(UTC)
        case.status = "AWAITING_RESPONSE" if outcome.status in {"QUEUED", "SENT", "DELIVERED"} else "NEEDS_REVIEW"
        case.reason = outcome.failure_code
        audit(session, case.agency_id, "LEAD_RECOVERY_ATTEMPT_RECORDED", {"case_id": str(case.id), "attempt_id": str(attempt.id), "status": outcome.status})


def collect_recovery_jobs(sessions: sessionmaker[Session], batch_size: int) -> list[Callable[[], None]]:
    from itertools import zip_longest
    from insurance_operations.database.models.recovery import RecoveryWebhook
    from insurance_operations.recovery.inbox import process_event
    from insurance_operations.recovery.delivery_jobs import deliver_reply, expire_continuation, reconcile_attempt

    with sessions() as session:
        settings = session.info.get("integration_settings")
        enabled = isinstance(settings, DatabaseSettings) and settings.recovery_enabled
        filters = or_(RecoveryCase.status == "IN_PROGRESS", and_(RecoveryPolicy.enabled.is_(True), RecoveryCase.status.in_(["PENDING", "READY", "SCHEDULED", "AWAITING_RESPONSE"]), RecoveryCase.paused.is_(False))) if enabled else RecoveryCase.status == "IN_PROGRESS"
        now = datetime.now(UTC)
        scheduled_due = select(RecoveryAttempt.id).where(RecoveryAttempt.recovery_case_id == RecoveryCase.id, RecoveryAttempt.status == "SCHEDULED", RecoveryAttempt.scheduled_at <= now).exists()
        identifiers = list(session.scalars(select(RecoveryCase.id).outerjoin(RecoveryPolicy, RecoveryPolicy.agency_id == RecoveryCase.agency_id).where(filters, RecoveryCase.eligible_at <= now,
            or_(RecoveryCase.status != "SCHEDULED", scheduled_due),
            or_(RecoveryCase.status != "IN_PROGRESS", RecoveryCase.updated_at <= now - timedelta(minutes=5)))
            .order_by(RecoveryCase.updated_at, RecoveryCase.id).limit(batch_size)))
        events = list(session.scalars(select(RecoveryWebhook.id).where(RecoveryWebhook.processed_at.is_(None),
            RecoveryWebhook.next_attempt_at <= now).order_by(RecoveryWebhook.received_at, RecoveryWebhook.id).limit(batch_size)))
        replies = list(session.scalars(select(RecoveryGrant.id).where(
            (RecoveryGrant.reply_status == "PENDING") & (RecoveryGrant.reply_due_at <= now)
            | (RecoveryGrant.reply_status == "STARTED") & (RecoveryGrant.reply_started_at <= now - timedelta(minutes=5)))
            .order_by(RecoveryGrant.created_at, RecoveryGrant.id).limit(batch_size)))
        expired = list(session.scalars(select(RecoveryGrant.id).join(RecoveryCase,
            (RecoveryCase.agency_id == RecoveryGrant.agency_id) & (RecoveryCase.id == RecoveryGrant.recovery_case_id))
            .where(RecoveryGrant.status.in_(["WAITING", "ACTIVE"]), RecoveryGrant.expires_at <= now,
            or_(RecoveryGrant.approved_at.is_(None), and_(RecoveryCase.status.not_in(list(TERMINAL)),
                RecoveryCase.reason.is_distinct_from("BOOKING_CONFIRMATION_REQUIRES_REVIEW"))))
            .order_by(RecoveryGrant.expires_at, RecoveryGrant.id).limit(batch_size)))
        pending_reply = select(RecoveryGrant.id).where(RecoveryGrant.attempt_id == RecoveryAttempt.id,
            RecoveryGrant.reply_status.in_(["QUEUED", "UNKNOWN"]), RecoveryGrant.reply_provider_reference.is_not(None)).exists()
        reconcile = list(session.scalars(select(RecoveryAttempt.id).where(
            RecoveryAttempt.started_at.is_not(None),
            RecoveryAttempt.last_reconciled_at.is_(None) | (RecoveryAttempt.last_reconciled_at <= now - timedelta(minutes=1)),
            RecoveryAttempt.provider.in_(["TWILIO_SMS", "ELEVENLABS_RECOVERY"]),
            ((RecoveryAttempt.status.in_(["QUEUED", "UNKNOWN"]) | ((RecoveryAttempt.channel == "VOICE") & RecoveryAttempt.provider_terminal_at.is_(None) & (RecoveryAttempt.status == "SENT")))
             & RecoveryAttempt.provider_reference.is_not(None)) | pending_reply)
            .order_by(RecoveryAttempt.last_reconciled_at.nulls_first(), RecoveryAttempt.started_at).limit(batch_size)))
    jobs: list[Callable[[], None]] = []
    for event, reply, read, expiry, case in zip_longest(events, replies, reconcile, expired, identifiers):
        if event:
            jobs.append(partial(process_event, sessions, event))
        if read:
            jobs.append(partial(reconcile_attempt, sessions, read))
        if reply:
            jobs.append(partial(deliver_reply, sessions, reply))
        if expiry:
            jobs.append(partial(expire_continuation, sessions, expiry))
        if case:
            jobs.append(partial(process_case, sessions, case))
    return jobs
