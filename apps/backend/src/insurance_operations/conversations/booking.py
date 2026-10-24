from collections.abc import Callable
from datetime import UTC, date, datetime
from typing import Annotated
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.actors import ActorContext
from insurance_operations.conversations.schemas import ConversationTurn
from insurance_operations.conversations.service import CONFIRM_INTAKE_ROUTE_KEY
from insurance_operations.conversations.spoken import (
    intake_readback,
    require_spoken_confirmation,
)
from insurance_operations.customers import CustomerInput
from insurance_operations.database.models.conversation import (
    ConversationChannel,
    ConversationIntake,
    ConversationSession,
    ConversationSessionStatus,
)
from insurance_operations.database.models.hvac import HvacServiceRequest
from insurance_operations.database.models.operations import (
    IdempotencyRecord,
    IdempotencyStatus,
)
from insurance_operations.errors import ApiError
from insurance_operations.hvac.schemas import (
    AppointmentView,
    AvailabilityInput,
    AvailabilityResponse,
    ReservationInput,
    ServiceDetails,
    ServiceRequestInput,
)
from insurance_operations.hvac.service import SchedulingService, unavailable


class BrowserIntakeDraft(BaseModel):
    customer: CustomerInput
    service: ServiceDetails


class BrowserAvailabilityInput(BaseModel):
    day: date


class BrowserReservationInput(BaseModel):
    team_key: str = Field(min_length=1, max_length=40)
    starts_at: datetime
    idempotency_key: str = Field(
        min_length=8, max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$"
    )


class BrowserAppointmentConfirmation(BaseModel):
    explicit_confirmation: bool
    transcript: list[ConversationTurn] = Field(min_length=2, max_length=60)


class BrowserReservationResponse(BaseModel):
    appointment: AppointmentView
    timezone: str
    readback: str


def appointment_readback(appointment: AppointmentView, timezone: str) -> str:
    local = appointment.starts_at.astimezone(ZoneInfo(timezone))
    spoken_time = local.strftime("%A, %B %d, %Y at %I:%M %p")
    return (
        f"Your appointment is temporarily held for {spoken_time}, "
        f"in the {timezone} timezone. "
        "It is not booked yet. May I confirm this appointment? "
        "Say yes to confirm my appointment, or say no."
    )


def create_browser_booking_router(
    sessions: sessionmaker[Session], actor_dependency: Callable[..., ActorContext]
) -> APIRouter:
    router = APIRouter(
        prefix="/api/v1/development/conversation-sessions/{session_id}/booking"
    )
    scheduling = SchedulingService(sessions)
    Actor = Annotated[ActorContext, Depends(actor_dependency)]

    def require_live_session(
        session: Session, actor: ActorContext, session_id: UUID
    ) -> ConversationSession:
        row = session.get(ConversationSession, session_id)
        if (
            row is None
            or row.agency_id != actor.agency_id
            or row.initiated_by != actor.app_user_id
            or row.channel != ConversationChannel.BROWSER.value
            or row.status
            not in {
                ConversationSessionStatus.AUTHORIZED.value,
                ConversationSessionStatus.CONFIRMED.value,
            }
            or row.ended_at is not None
            or row.authorization_expires_at <= datetime.now(UTC)
        ):
            raise unavailable(
                "The browser conversation is not active.",
                "CONVERSATION_SESSION_NOT_ACTIVE",
            )
        return row

    def confirmed_request(
        actor: ActorContext, session_id: UUID, *, allow_hazardous: bool = False
    ) -> HvacServiceRequest:
        with sessions() as session:
            require_live_session(session, actor, session_id)
            record = session.scalar(
                select(IdempotencyRecord)
                .join(
                    ConversationIntake,
                    ConversationIntake.id == IdempotencyRecord.resource_id,
                )
                .where(
                    ConversationIntake.conversation_session_id == session_id,
                    ConversationIntake.agency_id == actor.agency_id,
                    ConversationIntake.created_by == actor.app_user_id,
                    IdempotencyRecord.agency_id == actor.agency_id,
                    IdempotencyRecord.actor_scope_type == "APP_USER",
                    IdempotencyRecord.actor_scope_id == actor.app_user_id,
                    IdempotencyRecord.route_key == CONFIRM_INTAKE_ROUTE_KEY,
                    IdempotencyRecord.resource_type == "CONVERSATION_INTAKE",
                    IdempotencyRecord.status == IdempotencyStatus.COMPLETED.value,
                )
            )
            body = record.response_body if record else None
            request_id = body.get("service_request_id") if body else None
            if not isinstance(request_id, str):
                raise unavailable("Read back and save the service request first.")
            row = scheduling._request(session, actor.agency_id, UUID(request_id))
            if row.service_details.get("hazardous_condition") and not allow_hazardous:
                raise unavailable(
                    "This request needs human attention. No appointment can be booked. "
                    "Leave immediate danger and contact emergency services.",
                    "HUMAN_ATTENTION_REQUIRED",
                )
            session.expunge(row)
            return row

    def reservation_response(
        actor: ActorContext, appointment: AppointmentView
    ) -> BrowserReservationResponse:
        configuration = scheduling.configuration(actor.agency_id)["configuration"]
        if not isinstance(configuration, dict):
            raise unavailable("Scheduling is not configured.")
        timezone = configuration.get("timezone")
        if not isinstance(timezone, str):
            raise unavailable("The business timezone is not configured.")
        return BrowserReservationResponse(
            appointment=appointment,
            timezone=timezone,
            readback=appointment_readback(appointment, timezone),
        )

    @router.post("/intake-readback")
    def prepare_intake(
        session_id: UUID, data: BrowserIntakeDraft, actor: Actor
    ) -> dict[str, object]:
        with sessions() as session:
            require_live_session(session, actor, session_id)
        try:
            validated = ServiceRequestInput(
                customer=data.customer, service=data.service, explicit_confirmation=True
            )
            readback = intake_readback(validated)
        except ValueError as error:
            raise ApiError(
                status_code=422,
                code="INTAKE_INCOMPLETE",
                message="Complete the callback number, U.S. address and service details.",
            ) from error
        configuration = scheduling.configuration(actor.agency_id)["configuration"]
        timezone = (
            configuration.get("timezone")
            if isinstance(configuration, dict)
            else None
        )
        business_date = (
            datetime.now(ZoneInfo(timezone)).date().isoformat()
            if isinstance(timezone, str)
            else None
        )
        return {
            "readback": readback,
            "persisted": False,
            "timezone": timezone,
            "business_date": business_date,
        }

    @router.post("/hazard")
    def flag_hazard(session_id: UUID, request: Request, actor: Actor) -> dict[str, bool]:
        row = confirmed_request(actor, session_id, allow_hazardous=True)
        scheduling.flag_hazard(
            actor.agency_id, row.id, UUID(request.state.correlation_id)
        )
        return {"human_attention_required": True, "bookable": False}

    @router.post("/availability", response_model=AvailabilityResponse)
    def availability(
        session_id: UUID, data: BrowserAvailabilityInput, actor: Actor
    ) -> AvailabilityResponse:
        row = confirmed_request(actor, session_id)
        customer = CustomerInput.model_validate(row.customer_details)
        postal_code = customer.address.postal_code if customer.address else None
        if postal_code is None:
            raise unavailable("A confirmed service ZIP code is required.")
        return scheduling.availability(
            actor.agency_id, AvailabilityInput(postal_code=postal_code, day=data.day)
        )

    @router.post("/reservations", response_model=BrowserReservationResponse)
    def reserve(
        session_id: UUID, data: BrowserReservationInput, request: Request, actor: Actor
    ) -> BrowserReservationResponse:
        row = confirmed_request(actor, session_id)
        appointment = scheduling.reserve(
            actor.agency_id,
            ReservationInput(service_request_id=row.id, **data.model_dump()),
            UUID(request.state.correlation_id),
        )
        return reservation_response(actor, appointment)

    @router.post(
        "/appointments/{appointment_id}/release", response_model=AppointmentView
    )
    def release(
        session_id: UUID, appointment_id: UUID, request: Request, actor: Actor
    ) -> AppointmentView:
        row = confirmed_request(actor, session_id)
        with sessions() as session:
            appointment = scheduling._appointment(
                session, actor.agency_id, appointment_id
            )
            if appointment.service_request_id != row.id:
                raise unavailable(
                    "This appointment does not belong to this conversation."
                )
        return scheduling.release_hold(
            actor.agency_id, appointment_id, UUID(request.state.correlation_id)
        )

    @router.post(
        "/appointments/{appointment_id}/confirm", response_model=BrowserReservationResponse
    )
    def confirm(
        session_id: UUID,
        appointment_id: UUID,
        data: BrowserAppointmentConfirmation,
        request: Request,
        actor: Actor,
    ) -> BrowserReservationResponse:
        row = confirmed_request(actor, session_id)
        with sessions() as session:
            appointment = scheduling._appointment(
                session, actor.agency_id, appointment_id
            )
            if appointment.service_request_id != row.id:
                raise unavailable(
                    "This appointment does not belong to this conversation."
                )
            result = reservation_response(
                actor, AppointmentView.model_validate(appointment)
            )
            if appointment.status == "CONFIRMED":
                return result
        try:
            require_spoken_confirmation(
                data.transcript, result.readback, "confirm my appointment"
            )
        except ValueError as error:
            raise unavailable(str(error), "SPOKEN_CONFIRMATION_REQUIRED") from error
        confirmed = scheduling.confirm(
            actor.agency_id,
            appointment_id,
            data.explicit_confirmation,
            UUID(request.state.correlation_id),
        )
        return result.model_copy(update={"appointment": confirmed})

    return router
