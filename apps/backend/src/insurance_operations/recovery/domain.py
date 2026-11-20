import hashlib
import hmac
import re
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from insurance_operations.database.models.conversation import ConversationIntake, ConversationSession
from insurance_operations.database.models.hvac import Appointment, BusinessSchedule, HvacServiceRequest
from insurance_operations.database.models.identity import Agency
from insurance_operations.database.models.lead import AgencyLead, LeadHandoffRequest
from insurance_operations.database.models.operations import AuditEvent
from insurance_operations.database.models.recovery import RecoveryAttempt, RecoveryCase, RecoveryPermission, RecoveryPolicy
from insurance_operations.database.models.telephony import InboundCall
from insurance_operations.errors import ApiError
from insurance_operations.hvac.availability import utc_instant
from insurance_operations.hvac.schemas import ScheduleInput
from insurance_operations.recovery.schemas import PolicyInput
from insurance_operations.settings import DatabaseSettings

TERMINAL = {"RECOVERED", "SUPPRESSED", "CLOSED"}


def audit(session: Session, agency_id: UUID, event: str, details: dict[str, object], actor_id: UUID | None = None) -> None:
    session.add(AuditEvent(agency_id=agency_id, actor_type="STAFF" if actor_id else "SYSTEM", actor_user_id=actor_id,
        event_type=event, occurred_at=datetime.now(UTC), summary="Lead recovery state updated", details=details, correlation_id=uuid4(), event_version=1))


def policy_for(session: Session, agency_id: UUID) -> PolicyInput:
    row = session.get(RecoveryPolicy, agency_id)
    if row:
        return PolicyInput.model_validate({**row.configuration, "enabled": row.enabled, "expected_row_version": row.row_version})
    schedule = session.get(BusinessSchedule, agency_id)
    return PolicyInput(expected_row_version=0, timezone=str(schedule.configuration.get("timezone", "America/New_York")) if schedule else "America/New_York")


def destination_digest(settings: DatabaseSettings, agency_id: UUID, phone: str) -> str:
    key = settings.recovery_token_encryption_key
    if key is None:
        raise ApiError(status_code=409, code="RECOVERY_ENCRYPTION_UNAVAILABLE", message="Configure the backend recovery encryption key first.")
    if re.fullmatch(r"\+[1-9][0-9]{7,14}", phone) is None:
        raise ApiError(status_code=409, code="RECOVERY_RECIPIENT_INVALID", message="A confirmed E.164 callback number is required.")
    return hmac.new(key.get_secret_value().encode(), f"{agency_id}:{phone}".encode(), hashlib.sha256).hexdigest()


def permission_rows(session: Session, settings: DatabaseSettings, request: HvacServiceRequest) -> list[RecoveryPermission]:
    if settings.recovery_token_encryption_key is None:
        return []
    phone = str(request.customer_details.get("phone") or "")
    try:
        digest = destination_digest(settings, request.agency_id, phone)
    except ApiError:
        return []
    return list(session.scalars(select(RecoveryPermission).where(RecoveryPermission.agency_id == request.agency_id, RecoveryPermission.destination_digest == digest)))


def channel_allowed(rows: list[RecoveryPermission], channel: str) -> bool:
    if any(row.revoked_at is not None and row.channel in {"ALL", channel} for row in rows):
        return False
    return any(row.channel == channel and row.granted_at is not None and row.revoked_at is None and row.scope == "LEAD_RECOVERY" for row in rows)


def request_block(session: Session, request: HvacServiceRequest) -> str | None:
    if request.status != "OPEN" or request.service_details.get("hazardous_condition") is not False:
        return "STAFF_ATTENTION_REQUIRED"
    if request.service_details.get("kind") not in {"AC_REPAIR", "HEATING_REPAIR", "INSTALLATION", "MAINTENANCE"}:
        return "UNSUPPORTED_REQUEST"
    if session.scalar(select(Appointment.id).where(Appointment.agency_id == request.agency_id, Appointment.service_request_id == request.id, Appointment.status == "CONFIRMED")):
        return "ALREADY_BOOKED"
    schedule = session.get(BusinessSchedule, request.agency_id)
    address = request.customer_details.get("address")
    try:
        configuration = ScheduleInput.model_validate(schedule.configuration) if schedule else None
    except ValueError:
        return "SCHEDULING_UNAVAILABLE"
    if not isinstance(address, dict) or configuration is None or not configuration.enabled or address.get("postal_code") not in configuration.postal_codes:
        return "SCHEDULING_UNAVAILABLE"
    if request.conversation_session_id:
        intake = session.scalar(select(ConversationIntake).where(ConversationIntake.agency_id == request.agency_id, ConversationIntake.conversation_session_id == request.conversation_session_id))
        lead = session.scalar(select(AgencyLead).where(AgencyLead.agency_id == request.agency_id, AgencyLead.conversation_intake_id == intake.id)) if intake else None
        if lead and (lead.urgency == "HIGH" or lead.status in {"CLOSED", "ARCHIVED"} or session.scalar(select(LeadHandoffRequest.id).where(LeadHandoffRequest.agency_id == request.agency_id, LeadHandoffRequest.lead_id == lead.id, LeadHandoffRequest.status.in_(["REQUESTED", "ACKNOWLEDGED", "COMPLETED"])))):
            return "STAFF_ATTENTION_REQUIRED"
    if request.inbound_call_id:
        call = session.get(InboundCall, request.inbound_call_id)
        if call and call.status in {"TRANSFERRED", "CALLBACK_REQUESTED", "TRANSFER_PENDING", "CALLBACK_PENDING"}:
            return "STAFF_ATTENTION_REQUIRED"
        if call and call.lead_id:
            lead = session.scalar(select(AgencyLead).where(AgencyLead.agency_id == request.agency_id, AgencyLead.id == call.lead_id))
            if lead and (lead.urgency == "HIGH" or lead.status in {"CLOSED", "ARCHIVED"} or session.scalar(select(LeadHandoffRequest.id).where(LeadHandoffRequest.agency_id == request.agency_id, LeadHandoffRequest.lead_id == lead.id, LeadHandoffRequest.status.in_(["REQUESTED", "ACKNOWLEDGED", "COMPLETED"])))):
                return "STAFF_ATTENTION_REQUIRED"
    return None


def detect_request(session: Session, request: HvacServiceRequest) -> None:
    """Called only by new persisted activity; never scans historical requests."""
    agency = session.get(Agency, request.agency_id)
    if agency is None:
        return
    defaults = policy_for(session, request.agency_id)
    session.execute(insert(RecoveryPolicy).values(agency_id=request.agency_id, enabled=False, capture_from=agency.created_at,
        configuration=defaults.model_dump(mode="json", exclude={"enabled", "expected_row_version"}))
        .on_conflict_do_nothing(index_elements=[RecoveryPolicy.agency_id]))
    capture = session.get(RecoveryPolicy, request.agency_id)
    if capture is None or request.confirmed_at < capture.capture_from:
        return
    block = request_block(session, request)
    if block:
        existing = session.scalar(select(RecoveryCase).where(RecoveryCase.agency_id == request.agency_id, RecoveryCase.service_request_id == request.id).with_for_update())
        if existing and existing.status not in TERMINAL:
            existing.status, existing.reason = "NEEDS_REVIEW", block
            cancel_scheduled(session, existing)
        return
    if not request.customer_details.get("full_name") or not request.customer_details.get("phone"):
        return
    source, reference, activity = "UNCONFIRMED_BOOKING", request.id, request.confirmed_at
    policy = policy_for(session, request.agency_id)
    delay = policy.booking_delay_minutes
    lead_id = None
    if request.inbound_call_id:
        call = session.get(InboundCall, request.inbound_call_id)
        if call and call.agency_id == request.agency_id:
            lead_id = call.lead_id
        if call and call.status in {"COMPLETED", "FAILED"}:
            source, reference = "MISSED_CALL", call.id
            activity = max(activity, call.ended_at or call.updated_at)
            delay = policy.abandoned_delay_minutes
    if request.conversation_session_id:
        conversation = session.get(ConversationSession, request.conversation_session_id)
        if conversation and conversation.ended_at:
            source, reference, activity = "ABANDONED_CONVERSATION", conversation.id, max(activity, conversation.ended_at)
            delay = policy.abandoned_delay_minutes
        intake = session.scalar(select(ConversationIntake).where(ConversationIntake.agency_id == request.agency_id, ConversationIntake.conversation_session_id == request.conversation_session_id))
        if intake:
            lead_id = session.scalar(select(AgencyLead.id).where(AgencyLead.agency_id == request.agency_id, AgencyLead.conversation_intake_id == intake.id))
    created = session.execute(insert(RecoveryCase).values(agency_id=request.agency_id, service_request_id=request.id, lead_id=lead_id, source_type=source,
        source_reference=reference, status="PENDING", eligible_at=activity + timedelta(minutes=delay), last_activity_at=activity, paused=False)
        .on_conflict_do_nothing(constraint="uq_recovery_cases_request").returning(RecoveryCase.id)).scalar_one_or_none()
    if created:
        audit(session, request.agency_id, "LEAD_RECOVERY_CANDIDATE_CREATED", {"case_id": str(created), "service_request_id": str(request.id), "source_type": source, "source_reference": str(reference)})
    case = session.scalar(select(RecoveryCase).where(RecoveryCase.agency_id == request.agency_id, RecoveryCase.service_request_id == request.id).with_for_update())
    if case and case.status not in TERMINAL and case.lead_id is None and lead_id:
        case.lead_id = lead_id
    if case and case.status == "PENDING" and activity > case.last_activity_at:
        case.source_type, case.source_reference = source, reference
        case.last_activity_at, case.eligible_at = activity, activity + timedelta(minutes=delay)


def detect_terminal(session: Session, agency_id: UUID, *, call_id: UUID | None = None, conversation_id: UUID | None = None) -> None:
    filters = [HvacServiceRequest.agency_id == agency_id]
    if call_id:
        filters.append(HvacServiceRequest.inbound_call_id == call_id)
    elif conversation_id:
        filters.append(HvacServiceRequest.conversation_session_id == conversation_id)
    else:
        return
    request = session.scalar(select(HvacServiceRequest).where(*filters))
    if request:
        detect_request(session, request)


def cancel_scheduled(session: Session, case: RecoveryCase) -> None:
    for attempt in session.scalars(select(RecoveryAttempt).where(RecoveryAttempt.agency_id == case.agency_id, RecoveryAttempt.recovery_case_id == case.id, RecoveryAttempt.status == "SCHEDULED").with_for_update()):
        attempt.status, attempt.completed_at = "CANCELLED", datetime.now(UTC)


def record_booking_activity(session: Session, appointment: Appointment, now: datetime) -> None:
    case = session.scalar(select(RecoveryCase).where(RecoveryCase.agency_id == appointment.agency_id, RecoveryCase.service_request_id == appointment.service_request_id).with_for_update())
    if case is None or case.status in TERMINAL:
        return
    case.last_activity_at = max(now, case.last_activity_at)
    policy = policy_for(session, case.agency_id)
    case.eligible_at = case.last_activity_at + timedelta(minutes=policy.booking_delay_minutes)
    for attempt in session.scalars(select(RecoveryAttempt).where(RecoveryAttempt.agency_id == case.agency_id, RecoveryAttempt.recovery_case_id == case.id, RecoveryAttempt.status == "SCHEDULED").with_for_update()):
        attempt.scheduled_at = max(attempt.scheduled_at, case.eligible_at)


def stop_for_booking(session: Session, appointment: Appointment, *, attributable_attempt_id: UUID | None = None) -> None:
    if appointment.status != "CONFIRMED":
        return
    case = session.scalar(select(RecoveryCase).where(RecoveryCase.agency_id == appointment.agency_id, RecoveryCase.service_request_id == appointment.service_request_id).with_for_update())
    if case is None or case.status in TERMINAL:
        return
    attempt = session.get(RecoveryAttempt, attributable_attempt_id) if attributable_attempt_id else None
    attributed = bool(attempt and attempt.agency_id == case.agency_id and attempt.recovery_case_id == case.id and attempt.provider_reference and attempt.status in {"SENT", "DELIVERED"})
    case.status, case.reason = ("RECOVERED", "ATTRIBUTED_BOOKING") if attributed else ("CLOSED", "BOOKED_INDEPENDENTLY")
    if attributed:
        case.recovered_appointment_id = appointment.id
    cancel_scheduled(session, case)
    audit(session, case.agency_id, "LEAD_RECOVERY_BOOKING_STOPPED", {"case_id": str(case.id), "appointment_id": str(appointment.id), "status": case.status})


def contact_time(earliest: datetime, policy: PolicyInput) -> datetime:
    zone = ZoneInfo(policy.timezone)
    local = earliest.astimezone(zone)
    for offset in range(8):
        day = local.date() + timedelta(days=offset)
        start, end = utc_instant(day, policy.contact_start, zone), utc_instant(day, policy.contact_end, zone)
        if start and end:
            candidate = max(earliest, start)
            if candidate < end:
                return candidate
    raise ValueError("No safe contact window")
