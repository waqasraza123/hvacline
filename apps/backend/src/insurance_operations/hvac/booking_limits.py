from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import String, case, cast, distinct, func, or_, select
from sqlalchemy.orm import Session

from insurance_operations.database.models.conversation import ConversationSession
from insurance_operations.database.models.customer_account import CustomerAccount
from insurance_operations.database.models.hvac import Appointment, HvacServiceRequest
from insurance_operations.database.models.operations import AuditEvent
from insurance_operations.errors import ApiError
from insurance_operations.settings import (
    DEFAULT_CUSTOMER_MAX_ACTIVE_APPOINTMENTS,
    DEFAULT_CUSTOMER_MAX_BOOKING_CHANGES,
    DatabaseSettings,
)


class BookingLimits(BaseModel):
    max_active_appointments: int
    max_booking_changes: int
    active_appointments: int
    appointments_remaining: int
    refresh_at: datetime | None


class BookingChangeAllowance(BaseModel):
    maximum: int
    used: int
    remaining: int


def configured_limits(session: Session) -> tuple[int, int]:
    settings = session.info.get("integration_settings")
    if isinstance(settings, DatabaseSettings):
        return (
            settings.customer_max_active_appointments,
            settings.customer_max_booking_changes,
        )
    return (
        DEFAULT_CUSTOMER_MAX_ACTIVE_APPOINTMENTS,
        DEFAULT_CUSTOMER_MAX_BOOKING_CHANGES,
    )


def customer_request_owner(
    session: Session, request: HvacServiceRequest
) -> UUID | None:
    return session.scalar(
        select(CustomerAccount.app_user_id)
        .join(
            ConversationSession,
            ConversationSession.initiated_by == CustomerAccount.app_user_id,
        )
        .where(
            ConversationSession.id == request.conversation_session_id,
            ConversationSession.channel == "BROWSER",
            ConversationSession.agency_id == request.agency_id,
            CustomerAccount.agency_id == request.agency_id,
        )
    )


def customer_booking_limits(
    session: Session,
    agency_id: UUID,
    app_user_id: UUID,
    *,
    exclude_request_id: UUID | None = None,
) -> BookingLimits:
    maximum, changes = configured_limits(session)
    now = datetime.now(UTC)
    query = (
        select(
            func.count(distinct(Appointment.service_request_id)),
            func.min(
                case(
                    (Appointment.status == "HELD", Appointment.hold_expires_at),
                    else_=Appointment.ends_at,
                )
            ),
        )
        .join(
            HvacServiceRequest, HvacServiceRequest.id == Appointment.service_request_id
        )
        .join(
            ConversationSession,
            ConversationSession.id == HvacServiceRequest.conversation_session_id,
        )
        .where(
            Appointment.agency_id == agency_id,
            HvacServiceRequest.agency_id == agency_id,
            ConversationSession.agency_id == agency_id,
            ConversationSession.initiated_by == app_user_id,
            Appointment.ends_at > now,
            or_(
                Appointment.status == "CONFIRMED",
                (Appointment.status == "HELD") & (Appointment.hold_expires_at > now),
            ),
        )
    )
    if exclude_request_id is not None:
        query = query.where(Appointment.service_request_id != exclude_request_id)
    active, refresh_at = session.execute(query).one()
    return BookingLimits(
        max_active_appointments=maximum,
        max_booking_changes=changes,
        active_appointments=active,
        appointments_remaining=max(0, maximum - active),
        refresh_at=refresh_at,
    )


def require_customer_booking_capacity(
    session: Session,
    request: HvacServiceRequest,
    *,
    confirming: bool = False,
) -> None:
    owner = customer_request_owner(session, request)
    if owner is None:
        return
    limits = customer_booking_limits(
        session,
        request.agency_id,
        owner,
        exclude_request_id=request.id if confirming else None,
    )
    if limits.appointments_remaining == 0:
        raise ApiError(
            status_code=409,
            code="CUSTOMER_APPOINTMENT_LIMIT_REACHED",
            message=(
                f"Your active appointment limit is {limits.max_active_appointments}. "
                "Unexpired holds also use a place. Open your existing booking to make a change."
            ),
            details=limits.model_dump(mode="json"),
        )


def booking_change_allowance(
    session: Session, request_id: UUID, agency_id: UUID
) -> BookingChangeAllowance:
    _, maximum = configured_limits(session)
    used = (
        session.scalar(
            select(func.count(AuditEvent.id))
            .join(
                Appointment,
                AuditEvent.details["appointment_id"].as_string()
                == cast(Appointment.id, String),
            )
            .where(
                AuditEvent.agency_id == agency_id,
                AuditEvent.event_type == "HVAC_APPOINTMENT_RESCHEDULED",
                Appointment.agency_id == agency_id,
                Appointment.service_request_id == request_id,
            )
        )
        or 0
    )
    return BookingChangeAllowance(
        maximum=maximum, used=used, remaining=max(0, maximum - used)
    )


def require_customer_booking_change(
    session: Session, request: HvacServiceRequest
) -> None:
    if customer_request_owner(session, request) is None:
        return
    allowance = booking_change_allowance(session, request.id, request.agency_id)
    if allowance.remaining == 0:
        raise ApiError(
            status_code=409,
            code="CUSTOMER_BOOKING_CHANGE_LIMIT_REACHED",
            message=f"You have used {allowance.used} of {allowance.maximum} allowed date/time changes. Contact the business for further changes.",
            details=allowance.model_dump(),
        )
