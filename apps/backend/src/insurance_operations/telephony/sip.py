from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, Request, Response
from sqlalchemy.orm import Session, sessionmaker
from starlette.concurrency import run_in_threadpool

from insurance_operations.actors import ActorResolutionError, resolve_development_actor
from insurance_operations.database.models.telephony import InboundCall
from insurance_operations.errors import ApiError
from insurance_operations.telephony.providers.telnyx_sip import (
    MAX_INITIATION_BYTES,
    TelnyxSipAdapter,
)
from insurance_operations.telephony.schemas import InboundCallReceiveInput
from insurance_operations.telephony.service import TelephonyService
from insurance_operations.telephony.sip_schemas import (
    PhoneDynamicVariables,
    PhoneInitiationResponse,
)


class SipPhoneInitializationService:
    def __init__(
        self,
        *,
        adapter: TelnyxSipAdapter,
        telephony_service: TelephonyService,
        session_factory: sessionmaker[Session],
        development_actor_user_id: UUID,
    ) -> None:
        self.adapter = adapter
        self._telephony_service = telephony_service
        self._sessions = session_factory
        self._actor_user_id = development_actor_user_id

    def initialize(
        self, *, headers: dict[str, str], body: bytes, correlation_id: UUID
    ) -> PhoneInitiationResponse:
        call, context = self.adapter.verify_initiation(headers=headers, body=body)
        with self._sessions() as session:
            try:
                actor = resolve_development_actor(session, self._actor_user_id)
            except ActorResolutionError as error:
                raise ApiError(
                    status_code=503,
                    code="PHONE_DEVELOPMENT_ACTOR_UNAVAILABLE",
                    message="The phone development context is unavailable",
                ) from error
        result = self._telephony_service.initialize_phone_call(
            actor=actor,
            request=InboundCallReceiveInput(
                adapter_name=call.adapter_name,
                adapter_version=call.adapter_version,
                source_call_reference=call.source_call_reference,
                called_number_e164=call.called_number_e164,
                caller_number_e164=call.caller_number_e164,
                occurred_at=call.occurred_at,
            ),
            initialization=context,
            correlation_id=correlation_id,
        )
        with self._sessions() as session:
            persisted = session.get(InboundCall, result.call.id)
            duration = (
                persisted.adapter_metadata.get("maximum_duration_seconds")
                if persisted is not None
                else None
            )
        if not isinstance(duration, int):
            raise RuntimeError("phone initiation duration was not persisted")
        return PhoneInitiationResponse(
            dynamic_variables=PhoneDynamicVariables(
                phone_inbound_call_id=str(result.call.id),
                phone_max_duration_seconds=duration,
            )
        )


def create_sip_initiation_router(service: SipPhoneInitializationService) -> APIRouter:
    router = APIRouter(include_in_schema=False)

    @router.post(
        "/api/v1/providers/elevenlabs/sip/initialize",
        response_model=PhoneInitiationResponse,
    )
    async def initialize(
        request: Request,
        response: Response,
        authorization: Annotated[str | None, Header()] = None,
    ) -> PhoneInitiationResponse:
        service.adapter.verify_authorization(authorization)
        if request.headers.get("content-type", "").split(";", 1)[
            0
        ].strip().casefold() != ("application/json"):
            raise ApiError(
                status_code=415,
                code="PHONE_INITIATION_CONTENT_TYPE_INVALID",
                message="Phone initiation requires application/json",
            )
        body = bytearray()
        async for chunk in request.stream():
            if len(body) + len(chunk) > MAX_INITIATION_BYTES:
                raise ApiError(
                    status_code=413,
                    code="PHONE_INITIATION_TOO_LARGE",
                    message="The phone initiation request is too large",
                )
            body.extend(chunk)
        response.headers["Cache-Control"] = "no-store"
        return await run_in_threadpool(
            service.initialize,
            headers=dict(request.headers),
            body=bytes(body),
            correlation_id=UUID(request.state.correlation_id),
        )

    return router
