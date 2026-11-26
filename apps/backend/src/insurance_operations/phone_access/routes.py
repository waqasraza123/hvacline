from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request, Response
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.phone_access.schemas import (
    AccessApprovalInput,
    AccessCodeInput,
    PhoneAccessContext,
    PhoneAccessStart,
)
from insurance_operations.phone_access.service import PhoneAccountAccessService
from insurance_operations.settings import ApiSettings


def no_access_cache(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


def bearer(authorization: str | None) -> str | None:
    if authorization and authorization.startswith("Bearer "):
        return authorization[7:]
    return None


def create_customer_phone_access_router(
    settings: ApiSettings, sessions: sessionmaker[Session], portal: Callable[..., None]
) -> APIRouter:
    service = PhoneAccountAccessService(sessions, settings)
    router = APIRouter(
        prefix="/phone-access",
        dependencies=[
            Depends(no_access_cache), Depends(portal), Depends(service.enabled)
        ],
    )

    @router.get("")
    def list_access(
        authorization: Annotated[str | None, Header()] = None,
    ) -> dict[str, object]:
        return service.list_access(bearer(authorization))

    @router.post("/preview")
    def preview(
        data: AccessCodeInput,
        authorization: Annotated[str | None, Header()] = None,
    ) -> dict[str, object]:
        return service.preview(bearer(authorization), data.code)

    @router.post("/approve")
    def approve(
        data: AccessApprovalInput,
        request: Request,
        authorization: Annotated[str | None, Header()] = None,
    ) -> dict[str, object]:
        return service.approve(
            bearer(authorization), data, UUID(request.state.correlation_id)
        )

    @router.post("/{access_id}/revoke", status_code=204)
    def revoke(
        access_id: UUID,
        request: Request,
        authorization: Annotated[str | None, Header()] = None,
    ) -> Response:
        service.revoke(bearer(authorization), access_id, UUID(request.state.correlation_id))
        return Response(status_code=204, headers={"Cache-Control": "no-store"})

    return router


def create_phone_access_tools_router(
    settings: ApiSettings,
    sessions: sessionmaker[Session],
    verify_tool: Callable[[str | None], None],
) -> APIRouter:
    service = PhoneAccountAccessService(sessions, settings)

    def authorized(authorization: Annotated[str | None, Header()] = None) -> None:
        verify_tool(authorization)

    router = APIRouter(
        prefix="/api/v1/providers/elevenlabs/tools/account",
        include_in_schema=False,
        dependencies=[
            Depends(no_access_cache), Depends(service.enabled), Depends(authorized)
        ],
    )

    @router.post("/begin")
    def begin(data: PhoneAccessStart) -> dict[str, object]:
        return service.begin(data)

    @router.post("/status")
    def status(data: PhoneAccessContext) -> dict[str, object]:
        return service.status(data)

    @router.post("/appointments")
    def appointments(data: PhoneAccessContext) -> dict[str, object]:
        return service.appointments(data)

    @router.post("/memory")
    def memory(data: PhoneAccessContext) -> dict[str, object]:
        return service.memory_context(data)

    return router
