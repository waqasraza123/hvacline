from collections.abc import Callable
import secrets
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.actors import ActorContext
from insurance_operations.database.models.staff_alert import StaffAlert
from insurance_operations.errors import ApiError
from insurance_operations.notifications.staff_alerts import StaffAlertPolicyInput, policy_view, save_policy
from insurance_operations.settings import ApiSettings


def create_staff_alert_router(settings: ApiSettings, sessions: sessionmaker[Session], actor_dependency: Callable[..., ActorContext]) -> APIRouter:
    router = APIRouter(prefix="/api/v1/development/staff-alerts")

    def owner(response: Response, actor: Annotated[ActorContext, Depends(actor_dependency)], token: Annotated[str | None, Header(alias="X-Demo-Admin-Token")] = None) -> ActorContext:
        response.headers["Cache-Control"] = "no-store"
        secret = settings.demo_admin_token
        if not secret or not token or not secrets.compare_digest(token.encode(), secret.get_secret_value().encode()):
            raise ApiError(status_code=401, code="STAFF_ALERT_ADMIN_REQUIRED", message="Connect an authorized administrator workspace.", headers={"Cache-Control": "no-store"})
        return actor

    Owner = Annotated[ActorContext, Depends(owner)]

    @router.get("")
    def view(actor: Owner) -> dict[str, object]:
        with sessions() as session:
            rows = session.scalars(select(StaffAlert).where(StaffAlert.agency_id == actor.agency_id).order_by(StaffAlert.created_at.desc(), StaffAlert.id).limit(100)).all()
            return {"policy": policy_view(session, actor.agency_id, settings), "recent": [
                {"id": str(row.id), "event_type": row.event_type, "source_id": str(row.source_id), "recipient": row.recipient,
                 "status": row.status, "delivery_status": row.delivery_status, "attempts": row.attempts,
                 "created_at": row.created_at.isoformat(), "due_at": row.due_at.isoformat(), "last_error": row.last_error}
                for row in rows
            ]}

    @router.put("")
    def save(data: StaffAlertPolicyInput, request: Request, actor: Owner) -> dict[str, object]:
        return save_policy(sessions, settings, actor, data, UUID(request.state.correlation_id))

    return router
