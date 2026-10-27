from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, FastAPI, Header, Request, Response
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.actors import ActorContext
from insurance_operations.approved_faqs.schemas import (
    ApprovedFaqLookupInput,
    ApprovedFaqLookupResponse,
)
from insurance_operations.approved_faqs.service import ApprovedFaqService
from insurance_operations.conversations.booking import (
    BrowserIntakeDraft,
    create_browser_booking_router,
)
from insurance_operations.conversations.schemas import (
    ConversationIntakeConfirmationInput,
    ConversationIntakeResponse,
)
from insurance_operations.conversations.spoken import require_spoken_confirmation
from insurance_operations.customers import CustomerInput
from insurance_operations.database.models.conversation import (
    ConversationChannel,
    ConversationIntake,
)
from insurance_operations.database.models.lead import (
    AgencyLead,
    HandoffContactMethod,
    HandoffRequestKind,
)
from insurance_operations.errors import ApiError
from insurance_operations.leads.schemas import (
    HandoffRequestCreateInput,
    HandoffRequestResponse,
)
from insurance_operations.leads.service import LeadService
from insurance_operations.settings import ApiSettings
from insurance_operations.whatsapp.provider import (
    MAX_WEBHOOK_BYTES,
    ElevenLabsWhatsAppAdapter,
    WhatsAppInitiation,
    rejected,
    spoken_history,
)
from insurance_operations.whatsapp.service import WhatsAppService
from insurance_operations.whatsapp.settings import WhatsAppSettings

CONSENT_READBACK = (
    "I am HVACLine's AI receptionist. This is a development demo: use fictional "
    "details only. ElevenLabs processes this WhatsApp voice call. May I process "
    "your voice and, after a separate readback confirmation, save the confirmed "
    "details and transcript? Reply yes to continue, or no to end the call."
)


class ConsentInput(BaseModel):
    ai_disclosure_accepted: bool
    voice_processing_accepted: bool
    synthetic_data_acknowledged: bool
    provider_history: str = Field(min_length=1, max_length=65_536)


class IntakeInput(BrowserIntakeDraft):
    provider_history: str = Field(min_length=1, max_length=65_536)


class CallbackInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    customer: CustomerInput
    reason: str = Field(min_length=1, max_length=1000)
    availability: str | None = Field(default=None, min_length=1, max_length=500)
    provider_history: str = Field(min_length=1, max_length=65_536)


class CallbackContactInput(BaseModel):
    customer: CustomerInput


def callback_readback(customer: CustomerInput) -> str:
    if customer.address is not None:
        raise ApiError(
            status_code=422,
            code="CALLBACK_CONTACT_ONLY",
            message=(
                "Callback contact must contain only name, phone and optional email"
            ),
        )
    if not customer.phone:
        raise ApiError(
            status_code=422,
            code="CALLBACK_PHONE_REQUIRED",
            message=(
                "Ask for a callback telephone number; "
                "never infer it from a WhatsApp user ID"
            ),
        )
    email = f" Email: {customer.email}." if customer.email else ""
    return (
        f"Please confirm these fictional callback details. Name: {customer.full_name}. "
        f"Callback number: {customer.phone}.{email} "
        "May I save these contact details and the conversation transcript and ask "
        "the team to call you? Reply yes to request a callback, or tell me what to correct."
    )


async def bounded_body(request: Request, maximum: int) -> bytes:
    result = bytearray()
    async for chunk in request.stream():
        result.extend(chunk)
        if len(result) > maximum:
            raise ApiError(
                status_code=413,
                code="WHATSAPP_REQUEST_TOO_LARGE",
                message="The WhatsApp request is too large",
            )
    return bytes(result)


def prevent_caching(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


def create_whatsapp_router(service: WhatsAppService) -> APIRouter:
    router = APIRouter(
        prefix="/api/v1/providers/elevenlabs/whatsapp",
        include_in_schema=False,
        dependencies=[Depends(prevent_caching)],
    )
    adapter = service.adapter
    faqs = ApprovedFaqService(session_factory=service.sessions)
    leads = LeadService(
        session_factory=service.sessions,
        idempotency_retention_hours=service.settings.idempotency_retention_hours,
    )

    def tool_context(
        request: Request,
        authorization: Annotated[str | None, Header()] = None,
        binding_id: Annotated[
            UUID | None, Header(alias="X-HVACLine-Binding-ID")
        ] = None,
        conversation_id: Annotated[
            str | None, Header(alias="X-ElevenLabs-Conversation-ID")
        ] = None,
        session_token: Annotated[
            str | None, Header(alias="X-HVACLine-Session-Token")
        ] = None,
        text_only: Annotated[str | None, Header(alias="X-ElevenLabs-Text-Only")] = None,
    ) -> UUID:
        if binding_id is None or not conversation_id or text_only != "false":
            raise rejected()
        adapter.verify_tool(
            authorization, session_token, str(binding_id), conversation_id
        )
        with service.sessions() as session:
            service.require_binding(session, binding_id, conversation_id)
        request.state.whatsapp_binding_id = binding_id
        request.state.whatsapp_conversation_id = conversation_id
        return binding_id

    def session_actor(
        session_id: UUID,
        request: Request,
        binding_id: Annotated[UUID, Depends(tool_context)],
    ) -> ActorContext:
        with service.sessions() as session:
            binding, actor = service.require_binding(
                session, binding_id, request.state.whatsapp_conversation_id
            )
            service.require_session(session, binding, actor, session_id)
            return actor

    Actor = Annotated[ActorContext, Depends(session_actor)]

    @router.post("/initialize")
    async def initialize(
        request: Request, authorization: Annotated[str | None, Header()] = None
    ) -> dict[str, object]:
        body = await bounded_body(request, 16_384)
        try:
            data = WhatsAppInitiation.model_validate_json(body)
        except ValueError as error:
            raise rejected() from error
        adapter.verify_initialization(authorization, data)
        return service.initialize(data, UUID(request.state.correlation_id))

    @router.post("/consent")
    def consent(
        request: Request,
        data: ConsentInput,
        binding_id: Annotated[UUID, Depends(tool_context)],
    ) -> dict[str, object]:
        if not all(
            (
                data.ai_disclosure_accepted,
                data.voice_processing_accepted,
                data.synthetic_data_acknowledged,
            )
        ):
            raise ApiError(
                status_code=422,
                code="WHATSAPP_CONSENT_REQUIRED",
                message="All consent acknowledgements are required",
            )
        try:
            require_spoken_confirmation(
                spoken_history(data.provider_history), CONSENT_READBACK, "continue"
            )
        except ValueError as error:
            raise ApiError(
                status_code=422,
                code="WHATSAPP_CONSENT_REQUIRED",
                message="Read the complete disclosure and wait for explicit acceptance",
            ) from error
        session_id = service.consent(
            binding_id,
            request.state.whatsapp_conversation_id,
            UUID(request.state.correlation_id),
        )
        return {"session_id": str(session_id), "accepted": True}

    @router.post("/sessions/{session_id}/faq", response_model=ApprovedFaqLookupResponse)
    def faq(
        session_id: UUID, request: Request, data: ApprovedFaqLookupInput, actor: Actor
    ) -> ApprovedFaqLookupResponse:
        return faqs.conversation_lookup(
            actor=actor,
            conversation_session_id=session_id,
            query=data.query,
            correlation_id=UUID(request.state.correlation_id),
        )

    @router.post(
        "/sessions/{session_id}/confirm-intake",
        response_model=ConversationIntakeResponse,
    )
    def intake(
        session_id: UUID, request: Request, data: IntakeInput, actor: Actor
    ) -> ConversationIntakeResponse:
        try:
            confirmed = ConversationIntakeConfirmationInput(
                conversation_session_id=session_id,
                customer=data.customer,
                intake_intent=data.service.equipment_issue,
                service=data.service,
                spoken_confirmation=True,
                transcript=spoken_history(data.provider_history),
            )
        except ValueError as error:
            raise ApiError(
                status_code=422,
                code="INTAKE_CONFIRMATION_REQUIRED",
                message="Read the complete current intake readback and wait for a clear yes",
            ) from error
        result, _ = service.conversations.confirm_intake(
            actor=actor,
            request=confirmed,
            idempotency_key=f"whatsapp-intake:{session_id}",
            correlation_id=UUID(request.state.correlation_id),
        )
        return result

    @router.post(
        "/sessions/{session_id}/callback", response_model=HandoffRequestResponse
    )
    def callback(
        session_id: UUID, request: Request, data: CallbackInput, actor: Actor
    ) -> HandoffRequestResponse:
        try:
            require_spoken_confirmation(
                spoken_history(data.provider_history),
                callback_readback(data.customer),
                "request a callback",
            )
        except ValueError as error:
            raise ApiError(
                status_code=422,
                code="CALLBACK_CONFIRMATION_REQUIRED",
                message="Read the callback question and wait for explicit acceptance",
            ) from error
        with service.sessions() as session:
            lead_id = session.scalar(
                select(AgencyLead.id)
                .join(
                    ConversationIntake,
                    ConversationIntake.id == AgencyLead.conversation_intake_id,
                )
                .where(
                    AgencyLead.agency_id == actor.agency_id,
                    ConversationIntake.conversation_session_id == session_id,
                )
            )
        if lead_id is None:
            confirmed, _ = service.conversations.confirm_intake(
                actor=actor,
                request=ConversationIntakeConfirmationInput(
                    conversation_session_id=session_id,
                    customer=data.customer,
                    intake_intent="Caller requested human assistance by callback",
                    transcript=spoken_history(data.provider_history),
                ),
                allow_live_contact_confirmation=True,
                idempotency_key=f"whatsapp-intake:{session_id}",
                correlation_id=UUID(request.state.correlation_id),
            )
            lead_id = confirmed.lead_id
            if lead_id is None:
                raise RuntimeError("Confirmed callback has no lead")
        saved = leads.get(actor=actor, lead_id=lead_id)
        if (
            saved.customer.full_name != data.customer.full_name
            or saved.customer.phone != data.customer.phone
            or saved.customer.email != data.customer.email
        ):
            raise ApiError(
                status_code=409,
                code="CONFIRMED_CONTACT_CONFLICT",
                message="Use the contact details already confirmed for this call",
            )
        result, _ = leads.create_handoff(
            actor=actor,
            lead_id=lead_id,
            request=HandoffRequestCreateInput(
                request_kind=HandoffRequestKind.CALLBACK,
                preferred_contact_method=HandoffContactMethod.PHONE,
                reason=data.reason,
                availability=data.availability,
            ),
            idempotency_key=f"whatsapp-callback:{session_id}",
            correlation_id=UUID(request.state.correlation_id),
        )
        return result

    @router.post("/sessions/{session_id}/callback-readback")
    def prepare_callback(
        session_id: UUID, data: CallbackContactInput, actor: Actor
    ) -> dict[str, object]:
        return {"readback": callback_readback(data.customer), "persisted": False}

    @router.post("/post-call")
    async def post_call(request: Request) -> Response:
        body = await bounded_body(request, MAX_WEBHOOK_BYTES)
        event = adapter.verify_post_call(request.headers, body)
        service.finalize(event, UUID(request.state.correlation_id))
        return Response(status_code=200)

    router.include_router(
        create_browser_booking_router(
            service.sessions,
            session_actor,
            prefix="/sessions/{session_id}/booking",
            channel=ConversationChannel.WHATSAPP,
            confirmation_history=lambda data: spoken_history(data.provider_history),
        )
    )
    return router


def configure_whatsapp(
    application: FastAPI,
    settings: ApiSettings,
    whatsapp: WhatsAppSettings,
    engine: Engine,
) -> None:
    if not whatsapp.whatsapp_enabled:
        return

    def secret(value: SecretStr | None) -> str:
        if value is None:
            raise RuntimeError("WhatsApp configuration is incomplete")
        return value.get_secret_value()

    if (
        whatsapp.elevenlabs_whatsapp_agent_id is None
        or whatsapp.elevenlabs_whatsapp_phone_number_id is None
    ):
        raise RuntimeError("WhatsApp configuration is incomplete")

    adapter = ElevenLabsWhatsAppAdapter(
        agent_id=whatsapp.elevenlabs_whatsapp_agent_id,
        number_id=whatsapp.elevenlabs_whatsapp_phone_number_id,
        init_secret=secret(whatsapp.elevenlabs_whatsapp_init_secret),
        tool_secret=secret(whatsapp.elevenlabs_whatsapp_tool_secret),
        session_secret=secret(whatsapp.elevenlabs_whatsapp_session_secret),
        post_call_secret=secret(whatsapp.elevenlabs_whatsapp_post_call_secret),
    )
    sessions = sessionmaker(
        bind=engine,
        class_=Session,
        expire_on_commit=False,
        info={"integration_settings": settings},
    )
    application.include_router(
        create_whatsapp_router(WhatsAppService(sessions, settings, whatsapp, adapter))
    )
