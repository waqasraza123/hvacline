from datetime import UTC, datetime
import secrets
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.actors import ActorContext
from insurance_operations.database.models.hvac import BusinessSchedule
from insurance_operations.database.models.receptionist import AgencyReceptionistSettings
from insurance_operations.database.models.workspace import WorkspaceSession
from insurance_operations.errors import ApiError
from insurance_operations.hvac.routes import create_hvac_router
from insurance_operations.leads.schemas import HandoffRequestResponse, HandoffStatusInput
from insurance_operations.leads.service import LeadService
from insurance_operations.receptionist.schemas import ReceptionistSettingsInput, ReceptionistSettingsResponse
from insurance_operations.receptionist.service import ReceptionistSettingsService
from insurance_operations.settings import ApiSettings
from insurance_operations.workspace import business
from insurance_operations.workspace.access import StaffPrincipal, actor, denied, digest, login, membership, principal, user_view
from insurance_operations.workspace.schemas import AcceptInput, BusinessInput, EnrollmentConfirmation, EnrollmentInput, InvitationInput, LoginInput, MembershipInput, VersionInput


def correlation(request: Request) -> UUID:
    return UUID(str(getattr(request.state, "correlation_id", uuid4())))


def create_workspace_router(settings: ApiSettings, sessions: sessionmaker[Session]) -> APIRouter:
    def portal(response: Response, key: Annotated[str | None, Header(alias="X-Workspace-Portal-Key")] = None) -> None:
        response.headers["Cache-Control"] = "no-store"
        secret = settings.workspace_portal_secret
        if not settings.workspace_portal_enabled:
            raise ApiError(status_code=404, code="WORKSPACE_DISABLED", message="Staff workspace is not enabled.", headers={"Cache-Control": "no-store"})
        if secret is None or not key or not secrets.compare_digest(key.encode(), secret.get_secret_value().encode()):
            raise denied()

    router = APIRouter(prefix="/api/v1/workspace", dependencies=[Depends(portal)])

    def staff(authorization: Annotated[str | None, Header()] = None) -> StaffPrincipal:
        token = authorization[7:] if authorization and authorization.startswith("Bearer ") else None
        with sessions() as session:
            return principal(session, token)

    User = Annotated[StaffPrincipal, Depends(staff)]

    def bootstrap(key: Annotated[str | None, Header(alias="X-Workspace-Bootstrap-Key")] = None) -> None:
        secret = settings.workspace_bootstrap_token
        if secret is None or not key or not secrets.compare_digest(key.encode(), secret.get_secret_value().encode()):
            raise ApiError(status_code=403, code="WORKSPACE_BOOTSTRAP_REQUIRED", message="Platform-owner access is required.", headers={"Cache-Control": "no-store"})

    def business_actor(agency_id: UUID, request: Request, user: User) -> ActorContext:
        with sessions() as session:
            return actor(session, user, agency_id, manage=request.method == "PUT")

    @router.post("/auth/login")
    def sign_in(data: LoginInput) -> dict[str, object]:
        return login(sessions, settings, data)

    @router.post("/auth/invitation/start")
    def enroll(data: EnrollmentInput) -> dict[str, object]:
        return business.enrollment_start(sessions, settings, data)

    @router.post("/auth/invitation/confirm")
    def confirm_enrollment(data: EnrollmentConfirmation, request: Request) -> dict[str, object]:
        return business.enrollment_confirm(sessions, settings, data, correlation(request))

    @router.post("/auth/invitation/accept")
    def accept(data: AcceptInput, request: Request, user: User) -> dict[str, object]:
        return business.accept_invitation(sessions, user, data.token, correlation(request))

    @router.get("/auth/me")
    def me(user: User) -> dict[str, object]:
        with sessions() as session:
            return user_view(session, user)

    @router.post("/auth/logout", status_code=204)
    def logout(authorization: Annotated[str | None, Header()] = None) -> Response:
        token = authorization[7:] if authorization and authorization.startswith("Bearer ") else ""
        if token:
            with sessions() as session, session.begin():
                row = session.get(WorkspaceSession, digest(token))
                if row is not None and row.revoked_at is None:
                    row.revoked_at = datetime.now(UTC)
        return Response(status_code=204, headers={"Cache-Control": "no-store"})

    @router.get("/bootstrap/businesses", dependencies=[Depends(bootstrap)])
    def businesses() -> dict[str, object]:
        return {"items": business.bootstrap_businesses(sessions)}

    @router.post("/bootstrap/businesses", dependencies=[Depends(bootstrap)])
    def provision(data: BusinessInput, request: Request) -> dict[str, object]:
        return business.create_business(sessions, settings, data, correlation(request))

    @router.post("/bootstrap/businesses/{agency_id}/owner-invitation", dependencies=[Depends(bootstrap)])
    def replace_owner_invitation(agency_id: UUID, request: Request) -> dict[str, object]:
        return business.replace_initial_invitation(sessions, agency_id, correlation(request))

    @router.get("/businesses/{agency_id}/setup")
    def setup(agency_id: UUID, user: User) -> dict[str, object]:
        with sessions() as session:
            member, agency = membership(session, user, agency_id)
            profile = session.scalar(select(AgencyReceptionistSettings.id).where(AgencyReceptionistSettings.agency_id == agency_id))
            schedule = session.get(BusinessSchedule, agency_id)
            return {"id": str(agency.id), "name": agency.name, "role": member.role,
                    "profile_configured": profile is not None, "schedule_configured": schedule is not None,
                    "phone_setup": "Requires separate provider provisioning and acceptance"}

    @router.get("/businesses/{agency_id}/team")
    def team(agency_id: UUID, user: User) -> dict[str, object]:
        return business.team_view(sessions, user, agency_id)

    @router.post("/businesses/{agency_id}/invitations")
    def invite(agency_id: UUID, data: InvitationInput, request: Request, user: User) -> dict[str, object]:
        return business.invite_staff(sessions, user, agency_id, data, correlation(request))

    @router.post("/businesses/{agency_id}/invitations/{invitation_id}/revoke", status_code=204)
    def revoke(agency_id: UUID, invitation_id: UUID, data: VersionInput, request: Request, user: User) -> Response:
        business.revoke_invitation(sessions, user, agency_id, invitation_id, data.expected_row_version, correlation(request))
        return Response(status_code=204, headers={"Cache-Control": "no-store"})

    @router.put("/businesses/{agency_id}/members/{member_id}", status_code=204)
    def update_member(agency_id: UUID, member_id: UUID, data: MembershipInput, request: Request, user: User) -> Response:
        business.update_member(sessions, user, agency_id, member_id, data, correlation(request))
        return Response(status_code=204, headers={"Cache-Control": "no-store"})

    @router.get("/businesses/{agency_id}/profile")
    def profile(agency_id: UUID, user: User) -> ReceptionistSettingsResponse:
        with sessions() as session:
            context = actor(session, user, agency_id, manage=True)
        return ReceptionistSettingsService(session_factory=sessions).get(actor=context)

    @router.put("/businesses/{agency_id}/profile")
    def save_profile(agency_id: UUID, data: ReceptionistSettingsInput, request: Request, user: User) -> ReceptionistSettingsResponse:
        with sessions() as session:
            context = actor(session, user, agency_id, manage=True)
        return ReceptionistSettingsService(session_factory=sessions).replace(actor=context, request=data, correlation_id=correlation(request))

    @router.post("/businesses/{agency_id}/handoff-requests/{handoff_id}/status")
    def update_handoff(agency_id: UUID, handoff_id: UUID, data: HandoffStatusInput, request: Request, user: User) -> HandoffRequestResponse:
        with sessions() as session:
            context = actor(session, user, agency_id)
        return LeadService(session_factory=sessions, idempotency_retention_hours=settings.idempotency_retention_hours).set_handoff_status(actor=context, handoff_id=handoff_id, request=data, correlation_id=correlation(request))

    router.include_router(create_hvac_router(sessions, business_actor, prefix="/businesses/{agency_id}/hvac"))
    return router
