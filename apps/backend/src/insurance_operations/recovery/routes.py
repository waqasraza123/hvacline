from collections.abc import Callable
import secrets
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.actors import ActorContext
from insurance_operations.errors import ApiError
from insurance_operations.database.models.identity import AgencyMembership
from insurance_operations.recovery.ai import RecoveryAiService
from insurance_operations.recovery.schemas import AiInput, CaseAction, CaseView, PermissionInput, PolicyInput, RecoveryStatus, VersionInput, OutcomeInput
from insurance_operations.recovery.service import RecoveryService
from insurance_operations.settings import ApiSettings, RuntimeEnvironment


def create_recovery_router(settings: ApiSettings, sessions: sessionmaker[Session], actor_dependency: Callable[..., ActorContext]) -> APIRouter:
    router = APIRouter(prefix="/api/v1/development/lead-recovery", tags=["lead-recovery"])
    service, ai = RecoveryService(sessions, settings), RecoveryAiService(sessions, settings)

    def owner(response: Response, actor: Annotated[ActorContext, Depends(actor_dependency)], token: Annotated[str | None, Header(alias="X-Demo-Admin-Token")] = None) -> ActorContext:
        response.headers["Cache-Control"] = "no-store"
        secret = settings.demo_admin_token
        if settings.app_environment is RuntimeEnvironment.PRODUCTION:
            raise ApiError(status_code=404, code="NOT_FOUND", message="This resource is unavailable.", headers={"Cache-Control": "no-store"})
        if secret is None or not token or not secrets.compare_digest(token.encode(), secret.get_secret_value().encode()):
            raise ApiError(status_code=401, code="RECOVERY_ADMIN_REQUIRED", message="Connect an authorized administrator workspace.", headers={"Cache-Control": "no-store"})
        return actor

    Owner = Annotated[ActorContext, Depends(owner)]

    @router.get("/cases")
    def cases(actor: Owner, status: RecoveryStatus | None = None, limit: int = Query(default=25, ge=1, le=100), offset: int = Query(default=0, ge=0)) -> dict[str, object]:
        return service.cases(actor, status, limit, offset)

    @router.get("/summary")
    def summary(actor: Owner) -> dict[str, object]:
        return service.summary(actor)

    @router.get("/settings")
    def settings_view(actor: Owner) -> dict[str, object]:
        return service.settings_view(actor)

    @router.put("/settings")
    def settings_save(data: PolicyInput, actor: Owner) -> dict[str, object]:
        return service.save_policy(actor, data)

    @router.get("/staff")
    def staff(actor: Owner) -> dict[str, object]:
        with sessions() as session:
            identifiers = list(session.scalars(select(AgencyMembership.app_user_id).where(AgencyMembership.agency_id == actor.agency_id, AgencyMembership.status == "ACTIVE", AgencyMembership.deactivated_at.is_(None)).limit(100)))
        return {"items": [str(identifier) for identifier in identifiers]}

    @router.get("/ai")
    def ai_status(actor: Owner) -> dict[str, object]:
        return ai.status(actor)

    @router.put("/ai")
    def ai_save(data: AiInput, actor: Owner) -> dict[str, object]:
        return ai.save(actor, data)

    @router.post("/ai/test")
    def ai_test(data: VersionInput, actor: Owner) -> dict[str, object]:
        return ai.generate(actor, data.expected_row_version, "Reply with OK only. This is an administrator connection test without customer data.", test=True)

    @router.post("/ai/revoke")
    def ai_revoke(data: VersionInput, actor: Owner) -> dict[str, object]:
        return ai.revoke(actor, data.expected_row_version)

    @router.get("/cases/{identifier}", response_model=CaseView)
    def detail(identifier: UUID, actor: Owner) -> CaseView:
        return service.detail(actor, identifier)

    @router.post("/cases/{identifier}/action", response_model=CaseView)
    def action(identifier: UUID, data: CaseAction, actor: Owner, idempotency_key: Annotated[str, Header(alias="Idempotency-Key", pattern=r"^[A-Za-z0-9_.:-]{8,128}$")]) -> CaseView:
        return service.action(actor, identifier, data, idempotency_key)

    @router.put("/cases/{identifier}/permission", response_model=CaseView)
    def permission(identifier: UUID, data: PermissionInput, actor: Owner) -> CaseView:
        return service.permission(actor, identifier, data)

    @router.post("/cases/{identifier}/attempts/{attempt_id}/reconcile", response_model=CaseView)
    def reconcile(identifier: UUID, attempt_id: UUID, data: OutcomeInput, actor: Owner) -> CaseView:
        return service.resolve_outcome(actor, identifier, attempt_id, data)

    @router.post("/cases/{identifier}/draft")
    def draft(identifier: UUID, data: VersionInput, actor: Owner) -> dict[str, object]:
        # The model receives a service category and fixed task, not customer PII or raw transcripts.
        service.detail(actor, identifier)
        return ai.generate(actor, data.expected_row_version, "Draft a short service-related HVAC booking follow-up for staff review. Ask if the customer would like scheduling help. Include a STOP opt-out instruction. Do not include names, prices or appointment times.", test=False)

    return router
