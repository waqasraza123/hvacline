import secrets
from collections.abc import Callable
from functools import wraps
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.actors import ActorContext
from insurance_operations.errors import ApiError
from insurance_operations.ghl.provider import GhlError
from insurance_operations.ghl.schemas import (
    ConnectionAction,
    ConnectionInput,
    CredentialInput,
    RetryInput,
)
from insurance_operations.ghl.service import GhlBusy, GhlService
from insurance_operations.job_execution import JobDeadlineExceeded
from insurance_operations.settings import ApiSettings, RuntimeEnvironment


def provider_errors[**P, R](function: Callable[P, R]) -> Callable[P, R]:
    @wraps(function)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return function(*args, **kwargs)
        except GhlBusy:
            raise ApiError(
                status_code=409,
                code="GHL_BUSY",
                message="A GHL operation is in progress. Refresh and try again.",
                headers={"Cache-Control": "no-store"},
            ) from None
        except JobDeadlineExceeded:
            raise ApiError(
                status_code=503,
                code="GHL_TIMEOUT",
                message="GHL did not respond in time. Refresh status before retrying.",
                headers={"Cache-Control": "no-store"},
            ) from None
        except GhlError as error:
            raise ApiError(
                status_code=503 if error.retryable else 409,
                code=error.code,
                message="GHL could not complete this operation. Check the token permissions, location, mappings and recovery guidance.",
                headers={
                    "Cache-Control": "no-store",
                    **(
                        {"Retry-After": str(error.retry_after or 60)}
                        if error.retryable
                        else {}
                    ),
                },
            ) from None

    return wrapped


def create_ghl_router(
    settings: ApiSettings,
    sessions: sessionmaker[Session],
    actor_dependency: Callable[..., ActorContext],
    service: GhlService | None = None,
) -> APIRouter:
    integration = service or GhlService(sessions, settings)

    def owner(
        response: Response,
        actor: Annotated[ActorContext, Depends(actor_dependency)],
        token: Annotated[str | None, Header(alias="X-Demo-Admin-Token")] = None,
    ) -> ActorContext:
        response.headers["Cache-Control"] = "no-store"
        secret = settings.demo_admin_token
        if settings.app_environment is RuntimeEnvironment.PRODUCTION:
            raise ApiError(
                status_code=404,
                code="NOT_FOUND",
                message="This resource is unavailable.",
                headers={"Cache-Control": "no-store"},
            )
        if (
            secret is None
            or not token
            or not secrets.compare_digest(
                token.encode(), secret.get_secret_value().encode()
            )
        ):
            raise ApiError(
                status_code=401,
                code="GHL_OWNER_AUTH_REQUIRED",
                message="Connect an authorized administrator workspace.",
                headers={"Cache-Control": "no-store"},
            )
        return actor

    Owner = Annotated[ActorContext, Depends(owner)]
    router = APIRouter(prefix="/api/v1/development/integrations/ghl")

    @router.get("")
    def status(actor: Owner) -> dict[str, object]:
        return integration.status(actor)

    @router.post("/discover")
    @provider_errors
    def discover(data: CredentialInput, actor: Owner) -> dict[str, object]:
        del actor
        result = integration.discover(data)
        return {
            "pipelines": [row.model_dump() for row in result.pipelines],
            "fields": [row.model_dump() for row in result.fields],
        }

    @router.post("/connection")
    @provider_errors
    def connect(data: ConnectionInput, actor: Owner) -> dict[str, object]:
        return integration.connect(actor, data)

    @router.post("/connection/action")
    @provider_errors
    def action(data: ConnectionAction, actor: Owner) -> dict[str, object]:
        return integration.action(actor, data.action)

    @router.post("/connection/token")
    @provider_errors
    def token(data: CredentialInput, actor: Owner) -> dict[str, object]:
        return integration.rotate(actor, data)

    @router.get("/deliveries")
    def deliveries(
        actor: Owner,
        offset: int = Query(default=0, ge=0),
        limit: int = Query(default=25, ge=1, le=100),
    ) -> dict[str, object]:
        return integration.deliveries(actor, offset, limit)

    @router.post("/deliveries/{identifier}/retry")
    @provider_errors
    def retry(identifier: UUID, data: RetryInput, actor: Owner) -> dict[str, bool]:
        integration.retry(actor, identifier, data)
        return {"queued": True}

    return router
