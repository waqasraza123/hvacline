import re
import secrets
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy.orm import Session, sessionmaker
from starlette.concurrency import run_in_threadpool

from insurance_operations.errors import ApiError
from insurance_operations.settings import ApiSettings
from insurance_operations.telephony.contracts import TelephonyAdapterError
from insurance_operations.telephony.outbound.provider import ElevenLabsOutboundProvider
from insurance_operations.telephony.outbound.schemas import (
    DemoCallInput,
    DemoCallResponse,
)
from insurance_operations.telephony.outbound.service import (
    OutboundDemoService,
    unavailable,
)
from insurance_operations.telephony.outbound.settings import OutboundDemoSettings
from insurance_operations.telephony.providers.elevenlabs import MAX_WEBHOOK_BYTES


class CarrierEndedInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    all_carrier_legs_ended: Literal[True]

    @field_validator("all_carrier_legs_ended", mode="before")
    @classmethod
    def explicit_confirmation(cls, value: object) -> object:
        if value is not True:
            raise ValueError("Confirm that all carrier call legs have ended")
        return value


def create_outbound_demo_router(
    api: ApiSettings,
    sessions: sessionmaker[Session],
    settings: OutboundDemoSettings,
    provider: ElevenLabsOutboundProvider | None = None,
) -> APIRouter:
    if settings.outbound_demo_enabled and (
        api.development_actor_user_id is None
        or api.demo_admin_token is None
        or len(api.demo_admin_token.get_secret_value()) < 32
    ):
        raise ValueError(
            "Outbound demo requires DEVELOPMENT_ACTOR_USER_ID and a strong DEMO_ADMIN_TOKEN"
        )
    router = APIRouter(prefix="/api/v1/outbound-demo")
    service = OutboundDemoService(
        sessions, api, settings, provider or ElevenLabsOutboundProvider(settings)
    )

    def admin(
        supplied: Annotated[str | None, Header(alias="X-Demo-Admin-Token")] = None,
    ) -> None:
        # This gate is mandatory even when the general development sandbox is off.
        expected = api.demo_admin_token
        if (
            expected is None
            or len(expected.get_secret_value()) < 32
            or supplied is None
            or not secrets.compare_digest(
                supplied.encode(), expected.get_secret_value().encode()
            )
        ):
            raise ApiError(
                status_code=401,
                code="DEMO_ADMIN_AUTH_REQUIRED",
                message="Demo administrator authentication is required.",
            )

    def visitor(
        supplied: Annotated[str | None, Header(alias="X-Outbound-Demo-Key")] = None,
        token: Annotated[str | None, Header(alias="X-Outbound-Visitor")] = None,
    ) -> str:
        expected = settings.outbound_demo_secret
        if (
            expected is None
            or supplied is None
            or not secrets.compare_digest(
                supplied.encode(), expected.get_secret_value().encode()
            )
        ):
            raise ApiError(
                status_code=401,
                code="DEMO_BRIDGE_AUTH_REQUIRED",
                message="Demo website authentication is required.",
            )
        if token is None or re.fullmatch(r"[A-Za-z0-9_-]{43}", token) is None:
            raise ApiError(
                status_code=400,
                code="DEMO_VISITOR_REQUIRED",
                message="Allow cookies to request a demo call.",
            )
        return token

    Admin = Annotated[None, Depends(admin)]
    Visitor = Annotated[str, Depends(visitor)]

    @router.post("/admin/calls", response_model=DemoCallResponse)
    def create_admin_call(
        data: DemoCallInput, authenticated: Admin
    ) -> DemoCallResponse:
        return service.create(data, "admin")

    @router.get("/admin/calls/{call_id}", response_model=DemoCallResponse)
    def admin_status(call_id: UUID, authenticated: Admin) -> DemoCallResponse:
        return service.get(call_id, None)

    @router.post("/admin/calls/{call_id}/refresh", response_model=DemoCallResponse)
    def refresh(call_id: UUID, authenticated: Admin) -> DemoCallResponse:
        return service.refresh(call_id)

    @router.post(
        "/admin/calls/{call_id}/carrier-ended", response_model=DemoCallResponse
    )
    def carrier_ended(
        call_id: UUID, data: CarrierEndedInput, authenticated: Admin
    ) -> DemoCallResponse:
        return service.carrier_ended(call_id)

    @router.get("/availability")
    def availability(owner: Visitor) -> dict[str, bool]:
        return {
            "available": settings.outbound_demo_enabled
            and settings.outbound_demo_website_enabled
            and settings.outbound_demo_number_policy == "allowlist"
        }

    @router.post("/calls", response_model=DemoCallResponse)
    def create_visitor_call(data: DemoCallInput, owner: Visitor) -> DemoCallResponse:
        if (
            not settings.outbound_demo_website_enabled
            or settings.outbound_demo_number_policy != "allowlist"
        ):
            raise unavailable()
        return service.create(data, owner)

    @router.get("/calls/{call_id}", response_model=DemoCallResponse)
    def visitor_status(call_id: UUID, owner: Visitor) -> DemoCallResponse:
        return service.get(call_id, owner)

    @router.get("/requests/{request_id}", response_model=DemoCallResponse)
    def visitor_request_status(request_id: UUID, owner: Visitor) -> DemoCallResponse:
        return service.get_request(request_id, owner)

    @router.post("/webhook")
    async def webhook(request: Request) -> dict[str, str]:
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > MAX_WEBHOOK_BYTES:
                raise ApiError(
                    status_code=413,
                    code="DEMO_EVENT_TOO_LARGE",
                    message="Demo event exceeds the size limit.",
                )
        try:
            payload = service.provider.verify_webhook(request.headers, bytes(body))
        except TelephonyAdapterError as error:
            raise ApiError(
                status_code=401,
                code="DEMO_WEBHOOK_REJECTED",
                message="Demo webhook verification failed.",
            ) from error
        await run_in_threadpool(service.webhook, payload)
        return {"status": "accepted"}

    return router
