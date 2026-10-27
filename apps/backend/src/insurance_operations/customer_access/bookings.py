from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.actors import ActorContext
from insurance_operations.customers import CustomerInput
from insurance_operations.database.models.conversation import ConversationSession
from insurance_operations.database.models.hvac import (
    Appointment,
    BusinessSchedule,
    HvacServiceRequest,
)
from insurance_operations.errors import ApiError
from insurance_operations.hvac.booking_limits import (
    BookingChangeAllowance,
    BookingLimits,
    booking_change_allowance,
    customer_booking_limits,
)
from insurance_operations.hvac.schemas import (
    AppointmentView,
    AvailabilityInput,
    AvailabilityResponse,
    RescheduleInput,
    ScheduleInput,
    ServiceDetails,
)
from insurance_operations.hvac.service import SchedulingService, unavailable


class BookingDetails(BaseModel):
    appointment: AppointmentView
    customer: CustomerInput
    service: ServiceDetails
    timezone: str
    can_reschedule: bool
    change_message: str | None
    change_allowance: BookingChangeAllowance


class BookingAvailabilityInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    day: date


class BookingRescheduleInput(RescheduleInput):
    model_config = ConfigDict(extra="forbid")


def owned_booking(
    session: Session, actor: ActorContext, appointment_id: UUID
) -> tuple[Appointment, HvacServiceRequest]:
    result = session.execute(
        select(Appointment, HvacServiceRequest)
        .join(
            HvacServiceRequest,
            HvacServiceRequest.id == Appointment.service_request_id,
        )
        .join(
            ConversationSession,
            ConversationSession.id == HvacServiceRequest.conversation_session_id,
        )
        .where(
            Appointment.id == appointment_id,
            Appointment.agency_id == actor.agency_id,
            HvacServiceRequest.agency_id == actor.agency_id,
            ConversationSession.agency_id == actor.agency_id,
            ConversationSession.initiated_by == actor.app_user_id,
        )
    ).one_or_none()
    if result is None:
        raise ApiError(
            status_code=404,
            code="APPOINTMENT_NOT_FOUND",
            message="That appointment could not be found.",
        )
    return result[0], result[1]


def booking_details(
    session: Session, actor: ActorContext, appointment_id: UUID
) -> BookingDetails:
    appointment, request = owned_booking(session, actor, appointment_id)
    schedule = session.get(BusinessSchedule, actor.agency_id)
    configuration = (
        ScheduleInput.model_validate(schedule.configuration) if schedule else None
    )
    allowance = booking_change_allowance(session, request.id, actor.agency_id)
    can_reschedule = bool(
        configuration
        and configuration.enabled
        and appointment.status == "CONFIRMED"
        and appointment.starts_at
        >= datetime.now(UTC)
        + timedelta(minutes=configuration.cancellation_notice_minutes)
        and not request.service_details.get("hazardous_condition")
        and request.status != "CLOSED"
        and allowance.remaining > 0
    )
    return BookingDetails(
        appointment=AppointmentView.model_validate(appointment),
        customer=CustomerInput.model_validate(request.customer_details),
        service=ServiceDetails.model_validate(request.service_details),
        timezone=configuration.timezone if configuration else "UTC",
        can_reschedule=can_reschedule,
        change_allowance=allowance,
        change_message=None
        if can_reschedule
        else f"You have used {allowance.used} of {allowance.maximum} allowed date/time changes. Contact the business for further changes."
        if allowance.remaining == 0
        else "Please contact the business to change this appointment.",
    )


def create_customer_booking_router(
    sessions: sessionmaker[Session], actor_dependency: Callable[..., ActorContext]
) -> APIRouter:
    router = APIRouter()
    scheduling = SchedulingService(sessions)
    Actor = Annotated[ActorContext, Depends(actor_dependency)]

    @router.get("/booking-limits", response_model=BookingLimits)
    def limits(customer: Actor, response: Response) -> BookingLimits:
        response.headers["Cache-Control"] = "no-store"
        with sessions() as session:
            return customer_booking_limits(
                session, customer.agency_id, customer.app_user_id
            )

    @router.get("/appointments/{appointment_id}", response_model=BookingDetails)
    def detail(
        appointment_id: UUID, customer: Actor, response: Response
    ) -> BookingDetails:
        response.headers["Cache-Control"] = "no-store"
        with sessions() as session:
            return booking_details(session, customer, appointment_id)

    @router.post(
        "/appointments/{appointment_id}/availability",
        response_model=AvailabilityResponse,
    )
    def availability(
        appointment_id: UUID, data: BookingAvailabilityInput, customer: Actor
    ) -> AvailabilityResponse:
        with sessions() as session:
            details = booking_details(session, customer, appointment_id)
        if not details.can_reschedule:
            raise unavailable(
                details.change_message or "This booking cannot be changed."
            )
        address = details.customer.address
        if address is None or address.postal_code is None:
            raise unavailable("The service address needs staff review.")
        return scheduling.availability(
            customer.agency_id,
            AvailabilityInput(postal_code=address.postal_code, day=data.day),
            replace_id=appointment_id,
        )

    @router.post(
        "/appointments/{appointment_id}/reschedule", response_model=AppointmentView
    )
    def reschedule(
        appointment_id: UUID,
        data: BookingRescheduleInput,
        request: Request,
        customer: Actor,
    ) -> AppointmentView:
        with sessions() as session:
            appointment, _ = owned_booking(session, customer, appointment_id)
            if appointment.status not in {"CONFIRMED", "CANCELLED"}:
                raise unavailable("Only a confirmed appointment can be rescheduled.")
        if not data.explicit_confirmation:
            raise unavailable("Confirm the new appointment time before continuing.")
        return scheduling.reschedule(
            customer.agency_id, appointment_id, data, UUID(request.state.correlation_id)
        )

    return router
