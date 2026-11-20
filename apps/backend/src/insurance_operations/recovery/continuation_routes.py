import secrets
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.errors import ApiError
from insurance_operations.hvac.schemas import AppointmentView, AvailabilityResponse
from insurance_operations.recovery.continuation import Confirmation, RecoveryContinuation, SlotSelection
from insurance_operations.recovery.grants import unavailable
from insurance_operations.recovery.transports import TransportFailure
from insurance_operations.recovery.voice import FinishInput, RecoveryVoice
from insurance_operations.settings import DatabaseSettings


class DayInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    day: date


def create_recovery_continuation_routes(settings: DatabaseSettings, sessions: sessionmaker[Session]) -> APIRouter:
    router = APIRouter(prefix="/api/v1/recovery/continuation", include_in_schema=False)
    service = RecoveryContinuation(sessions, settings)

    def token(response: Response, authorization: Annotated[str | None, Header()] = None) -> str:
        response.headers["Cache-Control"] = "no-store"
        if not authorization or not authorization.startswith("Bearer ") or len(authorization) > 256:
            raise unavailable()
        value = authorization[7:]
        # Authenticate as SMS before returning any request or availability data.
        from insurance_operations.recovery.grants import authenticate

        with sessions() as session:
            if authenticate(session, settings, value).channel != "SMS":
                raise unavailable()
        return value

    Token = Annotated[str, Depends(token)]

    @router.get("")
    def context(value: Token) -> dict[str, object]:
        return service.context(value)

    @router.post("/availability", response_model=AvailabilityResponse)
    def availability(data: DayInput, value: Token) -> AvailabilityResponse:
        return service.availability(value, data.day)

    @router.post("/reserve")
    def reserve(data: SlotSelection, value: Token) -> dict[str, object]:
        return service.reserve(value, data)

    @router.post("/readback")
    def readback(value: Token) -> dict[str, object]:
        return service.readback(value)

    @router.post("/confirm", response_model=AppointmentView)
    def confirm(data: Confirmation, value: Token) -> AppointmentView:
        return service.confirm(value, data)

    @router.post("/release")
    def release(value: Token) -> dict[str, object]:
        return service.release(value)

    return router


def create_recovery_voice_tools(settings: DatabaseSettings, sessions: sessionmaker[Session]) -> APIRouter:
    router = APIRouter(prefix="/api/v1/providers/recovery/voice/tools", include_in_schema=False)
    service = RecoveryContinuation(sessions, settings)
    voice = RecoveryVoice(sessions, settings)

    def authenticated(response: Response,
        authorization: Annotated[str | None, Header()] = None,
        context: Annotated[str | None, Header(alias="X-Recovery-Context")] = None,
        conversation: Annotated[str | None, Header(alias="X-Recovery-Conversation")] = None,
    ) -> tuple[str, str]:
        response.headers["Cache-Control"] = "no-store"
        secret = settings.recovery_voice_tool_secret
        if not secret or not authorization or not secrets.compare_digest(authorization.encode(), f"Bearer {secret.get_secret_value()}".encode()) or not context or len(context) > 256 or not conversation or not 1 <= len(conversation) <= 200:
            raise unavailable()
        try:
            voice.bind(context, conversation)
        except TransportFailure:
            raise ApiError(status_code=503, code="RECOVERY_VOICE_UNAVAILABLE", message="The recovery call could not be verified. Do not claim a booking; request staff help.") from None
        return context, conversation

    Access = Annotated[tuple[str, str], Depends(authenticated)]

    @router.post("/continue")
    def continue_scheduling(access: Access) -> dict[str, object]:
        try:
            return voice.continue_scheduling(*access)
        except TransportFailure:
            raise ApiError(status_code=503, code="RECOVERY_VOICE_UNAVAILABLE", message="Customer continuation could not be verified. Ask the customer to repeat or request staff assistance.") from None

    @router.post("/context")
    def context(access: Access) -> dict[str, object]:
        result = service.context(access[0])
        if result["status"] == "WAITING":
            raise unavailable()
        return result

    @router.post("/availability", response_model=AvailabilityResponse)
    def availability(data: DayInput, access: Access) -> AvailabilityResponse:
        return service.availability(access[0], data.day)

    @router.post("/reserve")
    def reserve(data: SlotSelection, access: Access) -> dict[str, object]:
        return service.reserve(access[0], data)

    @router.post("/readback")
    def readback(access: Access) -> dict[str, object]:
        return service.readback(access[0])

    @router.post("/confirm", response_model=AppointmentView)
    def confirm(data: Confirmation, access: Access) -> AppointmentView:
        try:
            voice.verify_confirmation(access[0], access[1], data.nonce)
        except TransportFailure:
            raise ApiError(status_code=503, code="RECOVERY_VOICE_UNAVAILABLE", message="The current customer confirmation is not yet available. Keep the reservation and check again; do not claim a confirmed booking.") from None
        return service.confirm(access[0], data)

    @router.post("/release")
    def release(access: Access) -> dict[str, object]:
        return service.release(access[0])

    @router.post("/finish")
    def finish(data: FinishInput, access: Access) -> dict[str, bool]:
        return voice.finish(access[0], access[1], data)

    return router
