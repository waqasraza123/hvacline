import secrets
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.actors import ActorContext
from insurance_operations.approved_faqs import ApprovedFaqLookupInput, ApprovedFaqLookupResponse, ApprovedFaqService
from insurance_operations.conversations.booking import create_browser_booking_router
from insurance_operations.conversations.schemas import ConversationEndInput, ConversationEndResponse, ConversationIntakeConfirmationInput, ConversationIntakeResponse, ConversationSessionCreateInput, ConversationSessionResponse
from insurance_operations.conversations.service import ConversationService
from insurance_operations.customer_access.bookings import create_customer_booking_router
from insurance_operations.customer_access.schemas import AccountView, LoginInput, LoginResponse, SignupInput
from insurance_operations.customer_access.service import CustomerAccessService, unauthorized
from insurance_operations.database.models.conversation import ConversationSession
from insurance_operations.database.models.hvac import Appointment, HvacServiceRequest
from insurance_operations.errors import ApiError
from insurance_operations.hvac.schemas import AppointmentAction, AppointmentView, AvailabilityInput, AvailabilityResponse, ReservationInput
from insurance_operations.hvac.service import SchedulingService
from insurance_operations.receptionist import ReceptionistSettingsResponse, ReceptionistSettingsService
from insurance_operations.settings import ApiSettings, RuntimeEnvironment


def create_customer_router(
    settings: ApiSettings,
    sessions: sessionmaker[Session],
    conversations: ConversationService | None,
) -> APIRouter:
    router = APIRouter(prefix="/api/v1/customer")
    access = CustomerAccessService(sessions, settings)
    scheduling = SchedulingService(sessions)

    def portal(
        key: Annotated[str | None, Header(alias="X-Customer-Portal-Key")] = None,
    ) -> None:
        secret = settings.customer_portal_secret
        if (
            not settings.customer_portal_enabled
            or settings.app_environment is not RuntimeEnvironment.DEVELOPMENT
            or not settings.demo_sandbox_enabled
            or conversations is None
            or secret is None
            or not key
            or not secrets.compare_digest(key.encode(), secret.get_secret_value().encode())
        ):
            raise ApiError(status_code=404, code="NOT_FOUND", message="Customer booking is not available right now.")

    def session_token(authorization: str | None) -> str | None:
        if authorization and authorization.startswith("Bearer "):
            return authorization[7:]
        return None

    def actor(
        _: Annotated[None, Depends(portal)],
        authorization: Annotated[str | None, Header()] = None,
    ) -> ActorContext:
        return access.identity(session_token(authorization))[0]

    Actor = Annotated[ActorContext, Depends(actor)]
    Portal = Annotated[None, Depends(portal)]

    def voice() -> ConversationService:
        if conversations is None:
            raise unauthorized()
        return conversations

    @router.post("/auth/signup", response_model=LoginResponse, status_code=201)
    def signup(data: SignupInput, _: Portal) -> LoginResponse:
        return access.signup(data)

    @router.post("/auth/login", response_model=LoginResponse)
    def login(data: LoginInput, _: Portal) -> LoginResponse:
        return access.login(data)

    @router.get("/auth/me", response_model=AccountView)
    def me(_: Portal, authorization: Annotated[str | None, Header()] = None) -> AccountView:
        return access.identity(session_token(authorization))[1]

    @router.post("/auth/logout", status_code=204)
    def logout(_: Portal, authorization: Annotated[str | None, Header()] = None) -> Response:
        access.logout(session_token(authorization))
        return Response(status_code=204)

    @router.get("/receptionist-settings", response_model=ReceptionistSettingsResponse)
    def profile(customer: Actor) -> ReceptionistSettingsResponse:
        return ReceptionistSettingsService(session_factory=sessions).get(actor=customer)

    @router.post("/conversation-sessions", response_model=ConversationSessionResponse, status_code=201)
    def authorize(data: ConversationSessionCreateInput, customer: Actor) -> ConversationSessionResponse:
        return voice().authorize_session(actor=customer, request=data)

    @router.post("/conversation-sessions/{session_id}/end", response_model=ConversationEndResponse)
    def end(session_id: UUID, data: ConversationEndInput, customer: Actor) -> ConversationEndResponse:
        return voice().end_session(actor=customer, conversation_session_id=session_id, outcome=data.outcome)

    @router.post("/conversation-sessions/{session_id}/approved-faq-lookup", response_model=ApprovedFaqLookupResponse)
    def faq(session_id: UUID, data: ApprovedFaqLookupInput, request: Request, customer: Actor) -> ApprovedFaqLookupResponse:
        return ApprovedFaqService(session_factory=sessions).conversation_lookup(actor=customer, conversation_session_id=session_id, query=data.query, correlation_id=UUID(request.state.correlation_id))

    @router.post("/conversation-intakes", response_model=ConversationIntakeResponse, status_code=201)
    def confirm_intake(
        data: ConversationIntakeConfirmationInput, request: Request, response: Response,
        customer: Actor, key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
    ) -> ConversationIntakeResponse:
        if not all(character.isascii() and (character.isalnum() or character in "_.:-") for character in key):
            raise ApiError(status_code=422, code="INVALID_IDEMPOTENCY_KEY", message="The confirmation could not be processed. Please retry.")
        result, replayed = voice().confirm_intake(actor=customer, request=data, idempotency_key=key, correlation_id=UUID(request.state.correlation_id))
        if replayed:
            response.headers["Idempotent-Replayed"] = "true"
        return result

    def owned_request(session: Session, customer: Actor, request_id: UUID) -> HvacServiceRequest:
        row = session.scalar(select(HvacServiceRequest)
            .join(ConversationSession, ConversationSession.id == HvacServiceRequest.conversation_session_id)
            .where(HvacServiceRequest.id == request_id, HvacServiceRequest.agency_id == customer.agency_id, ConversationSession.agency_id == customer.agency_id, ConversationSession.initiated_by == customer.app_user_id))
        if row is None:
            raise ApiError(status_code=404, code="REQUEST_NOT_FOUND", message="That appointment request could not be found.")
        return row

    def owned_appointment(customer: Actor, appointment_id: UUID) -> None:
        with sessions() as session:
            row = scheduling._appointment(session, customer.agency_id, appointment_id)
            owned_request(session, customer, row.service_request_id)

    @router.get("/appointments")
    def appointments(customer: Actor, response: Response) -> dict[str, object]:
        response.headers["Cache-Control"] = "no-store"
        with sessions() as session:
            rows = session.scalars(select(Appointment)
                .join(HvacServiceRequest, HvacServiceRequest.id == Appointment.service_request_id)
                .join(ConversationSession, ConversationSession.id == HvacServiceRequest.conversation_session_id)
                .where(Appointment.agency_id == customer.agency_id, HvacServiceRequest.agency_id == customer.agency_id, ConversationSession.agency_id == customer.agency_id, ConversationSession.initiated_by == customer.app_user_id)
                .order_by(Appointment.starts_at.desc()).limit(50)).all()
            config = scheduling.configuration(customer.agency_id)["configuration"]
            timezone = config.get("timezone") if isinstance(config, dict) else None
            return {"appointments": [AppointmentView.model_validate(row).model_dump(mode="json") for row in rows], "timezone": timezone}

    @router.post("/hvac/availability", response_model=AvailabilityResponse)
    def availability(data: AvailabilityInput, customer: Actor) -> AvailabilityResponse:
        return scheduling.availability(customer.agency_id, data)

    @router.post("/hvac/reservations", response_model=AppointmentView)
    def reserve(data: ReservationInput, request: Request, customer: Actor) -> AppointmentView:
        with sessions() as session:
            owned_request(session, customer, data.service_request_id)
        return scheduling.reserve(customer.agency_id, data, UUID(request.state.correlation_id))

    @router.post("/hvac/appointments/{appointment_id}/confirm", response_model=AppointmentView)
    def confirm(appointment_id: UUID, data: AppointmentAction, request: Request, customer: Actor) -> AppointmentView:
        owned_appointment(customer, appointment_id)
        return scheduling.confirm(customer.agency_id, appointment_id, data.explicit_confirmation, UUID(request.state.correlation_id))

    @router.post("/hvac/appointments/{appointment_id}/release", response_model=AppointmentView)
    def release(appointment_id: UUID, request: Request, customer: Actor) -> AppointmentView:
        owned_appointment(customer, appointment_id)
        return scheduling.release_hold(customer.agency_id, appointment_id, UUID(request.state.correlation_id))

    router.include_router(create_browser_booking_router(sessions, actor, prefix="/conversation-sessions/{session_id}/booking"))
    router.include_router(create_customer_booking_router(sessions, actor))
    return router
