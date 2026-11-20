from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from functools import partial
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.database.models.hvac import Appointment, BusinessSchedule, HvacServiceRequest
from insurance_operations.database.models.identity import Agency
from insurance_operations.database.models.recovery import RecoveryAiConnection, RecoveryAttempt, RecoveryCase, RecoveryPolicy
from insurance_operations.hvac.locking import lock_business_schedule
from insurance_operations.job_execution import check_job_deadline
from insurance_operations.recovery.domain import TERMINAL, audit, cancel_scheduled, channel_allowed, contact_time, permission_rows, policy_for, request_block, stop_for_booking
from insurance_operations.recovery.providers import DeliveryOutcome, RecoveryContact, RecoveryDeliveryProvider, UnavailableRecoveryProvider
from insurance_operations.settings import DatabaseSettings


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
    if any(a.status in {"UNKNOWN", "STARTED", "QUEUED"} for a in attempts):
        return None, None, "PROVIDER_OUTCOME_UNRESOLVED"
    if now >= case.created_at + timedelta(days=policy.expiry_days) or len(attempts) >= policy.max_attempts:
        return None, None, "ATTEMPT_LIMIT_REACHED"
    permissions = permission_rows(session, settings, request)
    channels = [channel for channel in policy.channels if channel_allowed(permissions, channel)]
    if executing:
        channels = [channel for channel in channels if channel == executing.channel]
    if not channels:
        revoked = any(row.revoked_at is not None for row in permissions)
        return None, None, "OPTED_OUT" if revoked else "EXPLICIT_PERMISSION_REQUIRED"
    ai = session.get(RecoveryAiConnection, case.agency_id)
    if ai is None or ai.status != "CONNECTED":
        return None, None, "AI_MODEL_NOT_CONNECTED"
    channels = [channel for channel in channels if provider.available(case.agency_id, channel)]
    if not channels:
        return None, None, "RECOVERY_PROVIDER_UNAVAILABLE"
    earliest = max(now, case.eligible_at)
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
    adapter = provider or UnavailableRecoveryProvider()
    with sessions() as session, session.begin():
        seed = session.get(RecoveryCase, case_id)
        if seed is None or lock_business_schedule(session, seed.agency_id, skip_locked=True) is None:
            return
        case = session.scalar(select(RecoveryCase).where(RecoveryCase.id == case_id, RecoveryCase.agency_id == seed.agency_id).with_for_update(skip_locked=True))
        settings = session.info.get("integration_settings")
        if case is None or case.status in TERMINAL or not isinstance(settings, DatabaseSettings):
            return
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
        contact = RecoveryContact(case.agency_id, case.id, case.service_request_id, agency.name, str(request.customer_details["phone"]), attempt.idempotency_key)
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
        attempt.completed_at = datetime.now(UTC)
        case.status = "AWAITING_RESPONSE" if outcome.status in {"QUEUED", "SENT", "DELIVERED"} else "NEEDS_REVIEW"
        case.reason = outcome.failure_code
        audit(session, case.agency_id, "LEAD_RECOVERY_ATTEMPT_RECORDED", {"case_id": str(case.id), "attempt_id": str(attempt.id), "status": outcome.status})


def collect_recovery_jobs(sessions: sessionmaker[Session], batch_size: int) -> list[Callable[[], None]]:
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
    return [partial(process_case, sessions, identifier) for identifier in identifiers]
