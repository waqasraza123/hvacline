from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import hmac
import re
import secrets
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.actors import ActorContext
from insurance_operations.database.models.identity import Agency, AgencyMembership, AppUser
from insurance_operations.database.models.workspace import WorkspaceBusiness, WorkspaceCredential, WorkspaceLoginLimit, WorkspaceSession
from insurance_operations.errors import ApiError
from insurance_operations.customer_access.mfa_crypto import MfaVault, valid_totp_counter
from insurance_operations.customer_access.passwords import verify_password
from insurance_operations.settings import ApiSettings
from insurance_operations.workspace.schemas import LoginInput

SESSION_SECONDS = 28800
INVITATION_HOURS = 48


def denied(message: str = "Sign in to your staff workspace.") -> ApiError:
    return ApiError(status_code=401, code="WORKSPACE_SIGN_IN_REQUIRED", message=message, headers={"Cache-Control": "no-store"})


def conflict(message: str) -> ApiError:
    return ApiError(status_code=409, code="WORKSPACE_CHANGED", message=message, headers={"Cache-Control": "no-store"})


def digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def vault(settings: ApiSettings) -> MfaVault:
    key = settings.workspace_mfa_encryption_key
    if key is None:
        raise ApiError(status_code=503, code="WORKSPACE_SECURITY_UNAVAILABLE", message="Staff account security is not configured.")
    return MfaVault(key.get_secret_value())


def decrypt_factor(settings: ApiSettings, ciphertext: str, context: str) -> str:
    try:
        return vault(settings).decrypt(ciphertext, context)
    except ValueError as error:
        raise ApiError(status_code=503, code="WORKSPACE_SECURITY_UNAVAILABLE", message="Staff verification is temporarily unavailable.") from error


@dataclass(frozen=True)
class StaffPrincipal:
    app_user_id: UUID
    email: str
    display_name: str


def principal(session: Session, token: str | None) -> StaffPrincipal:
    if not token or not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
        raise denied()
    row = session.execute(select(WorkspaceSession, AppUser, WorkspaceCredential).select_from(WorkspaceSession)
        .join(AppUser, AppUser.id == WorkspaceSession.app_user_id)
        .join(WorkspaceCredential, WorkspaceCredential.app_user_id == AppUser.id)
        .where(WorkspaceSession.token_digest == digest(token), WorkspaceSession.revoked_at.is_(None),
               WorkspaceSession.expires_at > datetime.now(UTC), AppUser.status == "ACTIVE", AppUser.disabled_at.is_(None))).one_or_none()
    if row is None:
        raise denied()
    _, user, credential = row
    return StaffPrincipal(user.id, credential.email, user.display_name)


def membership(session: Session, user: StaffPrincipal, agency_id: UUID, *, manage: bool = False) -> tuple[AgencyMembership, Agency]:
    row = session.execute(select(AgencyMembership, Agency).select_from(AgencyMembership)
        .join(Agency, Agency.id == AgencyMembership.agency_id)
        .join(WorkspaceBusiness, WorkspaceBusiness.agency_id == Agency.id)
        .join(AppUser, AppUser.id == AgencyMembership.app_user_id)
        .where(AgencyMembership.app_user_id == user.app_user_id, AgencyMembership.agency_id == agency_id,
               AgencyMembership.status == "ACTIVE", AgencyMembership.deactivated_at.is_(None), Agency.archived_at.is_(None),
               AppUser.status == "ACTIVE", AppUser.disabled_at.is_(None))).one_or_none()
    if row is None:
        raise ApiError(status_code=404, code="WORKSPACE_BUSINESS_NOT_FOUND", message="This business is not available.")
    member, agency = row
    if manage and member.role not in {"OWNER", "ADMIN"}:
        raise ApiError(status_code=403, code="WORKSPACE_MANAGER_REQUIRED", message="An owner or administrator must make this change.")
    return member, agency


def actor(session: Session, user: StaffPrincipal, agency_id: UUID, *, manage: bool = False) -> ActorContext:
    _, agency = membership(session, user, agency_id, manage=manage)
    return ActorContext(user.app_user_id, user.display_name, agency.id, agency.name, agency.environment_kind)


def user_view(session: Session, user: StaffPrincipal) -> dict[str, object]:
    rows = session.execute(select(AgencyMembership, Agency)
        .join(Agency, Agency.id == AgencyMembership.agency_id)
        .join(WorkspaceBusiness, WorkspaceBusiness.agency_id == Agency.id)
        .where(AgencyMembership.app_user_id == user.app_user_id, AgencyMembership.status == "ACTIVE",
               AgencyMembership.deactivated_at.is_(None), Agency.archived_at.is_(None)).order_by(Agency.name, Agency.id).limit(100)).all()
    return {"id": str(user.app_user_id), "email": user.email, "display_name": user.display_name,
            "businesses": [{"id": str(agency.id), "name": agency.name, "role": member.role} for member, agency in rows]}


def issue_session(session: Session, user_id: UUID) -> dict[str, object]:
    token = secrets.token_urlsafe(32)
    session.add(WorkspaceSession(token_digest=digest(token), app_user_id=user_id, expires_at=datetime.now(UTC) + timedelta(seconds=SESSION_SECONDS)))
    return {"session_token": token, "expires_in": SESSION_SECONDS, "mfa_verified": True}


def login(sessions: sessionmaker[Session], settings: ApiSettings, data: LoginInput) -> dict[str, object]:
    email = str(data.email).casefold()
    secret = settings.workspace_portal_secret
    if secret is None:
        raise denied()
    key = hmac.new(secret.get_secret_value().encode(), email.encode(), hashlib.sha256).hexdigest()
    result: dict[str, object] | None = None
    limited = False
    retry_seconds = 900
    with sessions() as session, session.begin():
        now = datetime.now(UTC)
        global_key = hmac.new(secret.get_secret_value().encode(), f"workspace-login:{int(now.timestamp() // 60)}".encode(), hashlib.sha256).hexdigest()
        session.execute(insert(WorkspaceLoginLimit).values(key=global_key, attempts=0, expires_at=now + timedelta(minutes=1)).on_conflict_do_nothing(index_elements=["key"]))
        global_limit = session.scalar(select(WorkspaceLoginLimit).where(WorkspaceLoginLimit.key == global_key).with_for_update())
        if global_limit is None or global_limit.attempts >= settings.workspace_login_per_minute:
            limited = True
            retry_seconds = 60
        else:
            global_limit.attempts += 1
            expired = select(WorkspaceLoginLimit.key).where(WorkspaceLoginLimit.expires_at < now - timedelta(days=1)).limit(100)
            session.execute(delete(WorkspaceLoginLimit).where(WorkspaceLoginLimit.key.in_(expired)))
            session.execute(insert(WorkspaceLoginLimit).values(key=key, attempts=0, expires_at=now + timedelta(minutes=15)).on_conflict_do_nothing(index_elements=["key"]))
            limit = session.scalar(select(WorkspaceLoginLimit).where(WorkspaceLoginLimit.key == key).with_for_update())
            if limit is None:
                raise denied()
            if limit.expires_at <= now:
                limit.attempts, limit.expires_at = 0, now + timedelta(minutes=15)
            if limit.attempts >= 10:
                limited = True
            else:
                limit.attempts += 1
                credential = session.scalar(select(WorkspaceCredential).where(WorkspaceCredential.email == email).with_for_update())
                valid_password = verify_password(data.password, credential.password_hash if credential else None)
                user = session.get(AppUser, credential.app_user_id) if credential else None
                if valid_password and credential is not None and user is not None and user.status == "ACTIVE" and user.disabled_at is None:
                    factor = decrypt_factor(settings, credential.secret_ciphertext, f"workspace:{user.id}")
                    counter = valid_totp_counter(factor, data.code, now.timestamp(), credential.last_totp_counter)
                    if counter is not None:
                        credential.last_totp_counter = counter
                        result = issue_session(session, user.id)
    if limited:
        raise ApiError(status_code=429, code="WORKSPACE_LOGIN_LIMITED", message="Too many sign-in attempts. Try again later.", headers={"Retry-After": str(retry_seconds), "Cache-Control": "no-store"})
    if result is None:
        raise denied("The email, password or authenticator code could not be verified. Use a fresh code before retrying.")
    return result
