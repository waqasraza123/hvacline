from datetime import UTC, datetime, timedelta
import hashlib
import secrets
from uuid import UUID, uuid4

from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.customer_access.mfa_crypto import new_totp_secret, provisioning_uri, valid_totp_counter
from insurance_operations.customer_access.passwords import hash_password, verify_password
from insurance_operations.database.models.identity import Agency, AgencyMembership, AppUser
from insurance_operations.database.models.operations import AuditActorType, AuditEvent
from insurance_operations.database.models.workspace import WorkspaceBusiness, WorkspaceCredential, WorkspaceInvitation
from insurance_operations.errors import ApiError
from insurance_operations.settings import ApiSettings, RuntimeEnvironment
from insurance_operations.workspace.access import INVITATION_HOURS, StaffPrincipal, conflict, denied, decrypt_factor, digest, issue_session, membership, vault
from insurance_operations.workspace.schemas import BusinessInput, EnrollmentConfirmation, EnrollmentInput, InvitationInput, MembershipInput


def audit(session: Session, agency_id: UUID, event_type: str, correlation_id: UUID, user: StaffPrincipal | None = None, **details: object) -> None:
    session.add(AuditEvent(agency_id=agency_id, actor_type=AuditActorType.STAFF.value if user else AuditActorType.SYSTEM.value,
        actor_user_id=user.app_user_id if user else None, event_type=event_type, summary="Business workspace access updated",
        occurred_at=datetime.now(UTC), details=details, correlation_id=correlation_id, event_version=1))


def lock_business(session: Session, agency_id: UUID) -> None:
    identifier = session.scalar(select(Agency.id).join(WorkspaceBusiness, WorkspaceBusiness.agency_id == Agency.id)
        .where(Agency.id == agency_id, Agency.archived_at.is_(None)).with_for_update(of=Agency))
    if identifier is None:
        raise ApiError(status_code=404, code="WORKSPACE_BUSINESS_NOT_FOUND", message="This business is not available.")


def invite_view(row: WorkspaceInvitation) -> dict[str, object]:
    return {"id": str(row.id), "email": row.email, "role": row.role, "row_version": row.row_version,
            "expires_at": row.expires_at.isoformat(), "consumed": row.consumed_at is not None, "revoked": row.revoked_at is not None}


def new_invitation(session: Session, agency_id: UUID, email: str, role: str, created_by: UUID | None) -> dict[str, object]:
    now = datetime.now(UTC)
    pending = session.scalar(select(WorkspaceInvitation.id).where(WorkspaceInvitation.agency_id == agency_id,
        WorkspaceInvitation.email == email, WorkspaceInvitation.consumed_at.is_(None), WorkspaceInvitation.revoked_at.is_(None), WorkspaceInvitation.expires_at > now))
    if pending:
        raise conflict("An invitation is already pending. Revoke it before creating another link.")
    token = secrets.token_urlsafe(32)
    invitation = WorkspaceInvitation(agency_id=agency_id, email=email, role=role, created_by=created_by,
        token_digest=digest(token), expires_at=now + timedelta(hours=INVITATION_HOURS))
    session.add(invitation)
    session.flush()
    return {**invite_view(invitation), "invitation_token": token}


def create_business(sessions: sessionmaker[Session], settings: ApiSettings, data: BusinessInput, correlation_id: UUID) -> dict[str, object]:
    fingerprint = hashlib.sha256(data.model_dump_json(exclude={"creation_key"}).encode()).hexdigest()
    try:
        with sessions() as session, session.begin():
            session.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"), {"key": f"workspace-create:{data.creation_key}"})
            prior = session.scalar(select(WorkspaceBusiness).where(WorkspaceBusiness.creation_key == data.creation_key))
            if prior:
                if prior.fingerprint != fingerprint:
                    raise conflict("This creation reference was used for different details. Review the saved business.")
                return {"id": str(prior.agency_id), "replayed": True, "invitation": None}
            agency = Agency(name=data.name, slug=data.slug, environment_kind="PRODUCTION" if settings.app_environment is RuntimeEnvironment.PRODUCTION else "DEVELOPMENT")
            session.add(agency)
            session.flush()
            email = str(data.owner_email).casefold()
            session.add(WorkspaceBusiness(agency_id=agency.id, creation_key=data.creation_key, fingerprint=fingerprint, owner_email=email))
            result = new_invitation(session, agency.id, email, "OWNER", None)
            audit(session, agency.id, "WORKSPACE_BUSINESS_CREATED", correlation_id, invitation_id=result["id"])
            return {"id": str(agency.id), "replayed": False, "invitation": result}
    except IntegrityError as error:
        raise conflict("The business identifier is already in use. Refresh the business list before retrying.") from error


def bootstrap_businesses(sessions: sessionmaker[Session]) -> list[dict[str, object]]:
    with sessions() as session:
        rows = session.execute(select(WorkspaceBusiness, Agency).join(Agency, Agency.id == WorkspaceBusiness.agency_id)
            .where(Agency.archived_at.is_(None)).order_by(WorkspaceBusiness.created_at.desc()).limit(100)).all()
        return [{"id": str(agency.id), "name": agency.name, "slug": agency.slug, "owner_email": record.owner_email,
                 "has_owner": bool(session.scalar(select(AgencyMembership.id).where(AgencyMembership.agency_id == agency.id, AgencyMembership.role == "OWNER", AgencyMembership.status == "ACTIVE", AgencyMembership.deactivated_at.is_(None)).limit(1)))} for record, agency in rows]


def replace_initial_invitation(sessions: sessionmaker[Session], agency_id: UUID, correlation_id: UUID) -> dict[str, object]:
    with sessions() as session, session.begin():
        lock_business(session, agency_id)
        active_owner = session.scalar(select(AgencyMembership.id).where(AgencyMembership.agency_id == agency_id,
            AgencyMembership.role == "OWNER", AgencyMembership.status == "ACTIVE", AgencyMembership.deactivated_at.is_(None)).limit(1))
        record = session.get(WorkspaceBusiness, agency_id)
        if active_owner or record is None:
            raise conflict("An owner already has access. Use the signed-in team controls for further invitations.")
        for row in session.scalars(select(WorkspaceInvitation).where(WorkspaceInvitation.agency_id == agency_id,
                WorkspaceInvitation.created_by.is_(None), WorkspaceInvitation.consumed_at.is_(None), WorkspaceInvitation.revoked_at.is_(None))):
            row.revoked_at = datetime.now(UTC)
            row.pending_secret_ciphertext, row.pending_password_hash, row.pending_name = None, None, None
        session.flush()
        result = new_invitation(session, agency_id, record.owner_email, "OWNER", None)
        audit(session, agency_id, "WORKSPACE_INITIAL_INVITATION_REPLACED", correlation_id, invitation_id=result["id"])
        return result


def invitation(session: Session, token: str, *, lock: bool = True) -> WorkspaceInvitation:
    query = select(WorkspaceInvitation).where(WorkspaceInvitation.token_digest == digest(token)).execution_options(populate_existing=True)
    row = session.scalar(query.with_for_update() if lock else query)
    if row is None or row.revoked_at or row.consumed_at or row.expires_at <= datetime.now(UTC) or row.failed_attempts >= 5:
        raise denied("This invitation is invalid, expired or unavailable. Ask your business owner for a new invitation.")
    return row


def validate_inviter(session: Session, row: WorkspaceInvitation) -> None:
    if row.created_by is None:
        owner = session.scalar(select(AgencyMembership.id).where(AgencyMembership.agency_id == row.agency_id,
            AgencyMembership.role == "OWNER", AgencyMembership.status == "ACTIVE", AgencyMembership.deactivated_at.is_(None)).limit(1))
        if row.role != "OWNER" or owner:
            raise conflict("An owner is already established. Ask them for a new invitation.")
        return
    creator = session.execute(select(AgencyMembership, AppUser).join(AppUser, AppUser.id == AgencyMembership.app_user_id)
        .where(AgencyMembership.agency_id == row.agency_id, AgencyMembership.app_user_id == row.created_by,
               AgencyMembership.status == "ACTIVE", AgencyMembership.deactivated_at.is_(None), AppUser.status == "ACTIVE", AppUser.disabled_at.is_(None))).one_or_none()
    if creator is None or creator[0].role not in ({"OWNER"} if row.role in {"OWNER", "ADMIN"} else {"OWNER", "ADMIN"}):
        raise conflict("The inviter no longer has permission to grant this role. Ask an owner for a new invitation.")


def enrollment_start(sessions: sessionmaker[Session], settings: ApiSettings, data: EnrollmentInput) -> dict[str, object]:
    with sessions() as session, session.begin():
        row = invitation(session, data.token)
        existing = session.scalar(select(WorkspaceCredential.app_user_id).where(WorkspaceCredential.email == row.email))
        if existing:
            raise conflict("A staff account already exists for this invitation. Sign in, then accept it.")
        context = f"workspace-invitation:{row.id}"
        if row.pending_secret_ciphertext:
            if not verify_password(data.password, row.pending_password_hash):
                raise conflict("Enrollment already started with another password. Use that password or request a replacement invitation.")
            secret = decrypt_factor(settings, row.pending_secret_ciphertext, context)
        else:
            secret = new_totp_secret()
            row.pending_secret_ciphertext = vault(settings).encrypt(secret, context)
            row.pending_password_hash, row.pending_name = hash_password(data.password), data.display_name
        return {"secret": secret, "otpauth_uri": provisioning_uri(row.email, secret), "email": row.email}


def grant_membership(session: Session, row: WorkspaceInvitation, user_id: UUID) -> None:
    member = session.scalar(select(AgencyMembership).where(AgencyMembership.agency_id == row.agency_id, AgencyMembership.app_user_id == user_id))
    if member and member.status == "ACTIVE" and member.deactivated_at is None:
        raise conflict("This account already has access. Review its current role in the workspace.")
    if member is None:
        member = AgencyMembership(agency_id=row.agency_id, app_user_id=user_id)
        session.add(member)
    member.role, member.status, member.deactivated_at = row.role, "ACTIVE", None
    row.consumed_at = datetime.now(UTC)
    row.pending_secret_ciphertext, row.pending_password_hash, row.pending_name = None, None, None


def enrollment_confirm(sessions: sessionmaker[Session], settings: ApiSettings, data: EnrollmentConfirmation, correlation_id: UUID) -> dict[str, object]:
    result: dict[str, object] | None = None
    with sessions() as session, session.begin():
        reference = invitation(session, data.token, lock=False)
        lock_business(session, reference.agency_id)
        row = invitation(session, data.token)
        validate_inviter(session, row)
        session.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"), {"key": "workspace-email:" + digest(row.email)})
        if session.scalar(select(WorkspaceCredential.app_user_id).where(WorkspaceCredential.email == row.email)):
            raise conflict("Your staff account already exists. Sign in to accept this invitation.")
        if not row.pending_secret_ciphertext or not row.pending_password_hash or not row.pending_name:
            raise conflict("Start authenticator enrollment before confirming this invitation.")
        secret = decrypt_factor(settings, row.pending_secret_ciphertext, f"workspace-invitation:{row.id}")
        counter = valid_totp_counter(secret, data.code, datetime.now(UTC).timestamp(), None)
        if counter is None:
            row.failed_attempts += 1
        else:
            identifier = uuid4()
            user = AppUser(id=identifier, auth_subject=identifier, display_name=row.pending_name, email_snapshot=row.email)
            session.add(user)
            session.flush()
            session.add(WorkspaceCredential(app_user_id=user.id, email=row.email, password_hash=row.pending_password_hash,
                secret_ciphertext=vault(settings).encrypt(secret, f"workspace:{user.id}"), last_totp_counter=counter))
            grant_membership(session, row, user.id)
            audit(session, row.agency_id, "WORKSPACE_INVITATION_ACCEPTED", correlation_id, StaffPrincipal(user.id, row.email, user.display_name), invitation_id=str(row.id), role=row.role)
            result = issue_session(session, user.id)
    if result is None:
        raise denied("The authenticator code could not be verified. Use a fresh code; five failed attempts require a replacement invitation.")
    return result


def accept_invitation(sessions: sessionmaker[Session], user: StaffPrincipal, token: str, correlation_id: UUID) -> dict[str, object]:
    with sessions() as session, session.begin():
        reference = invitation(session, token, lock=False)
        lock_business(session, reference.agency_id)
        row = invitation(session, token)
        validate_inviter(session, row)
        if row.email != user.email:
            raise ApiError(status_code=403, code="WORKSPACE_INVITATION_EMAIL_MISMATCH", message="Sign in with the staff account this invitation was sent to.")
        grant_membership(session, row, user.app_user_id)
        audit(session, row.agency_id, "WORKSPACE_INVITATION_ACCEPTED", correlation_id, user, invitation_id=str(row.id), role=row.role)
        return {"agency_id": str(row.agency_id)}


def team_view(sessions: sessionmaker[Session], user: StaffPrincipal, agency_id: UUID) -> dict[str, object]:
    with sessions() as session:
        member, _ = membership(session, user, agency_id, manage=True)
        rows = session.execute(select(AgencyMembership, AppUser).join(AppUser, AppUser.id == AgencyMembership.app_user_id)
            .where(AgencyMembership.agency_id == agency_id).order_by(AgencyMembership.created_at, AgencyMembership.id).limit(100)).all()
        invites = session.scalars(select(WorkspaceInvitation).where(WorkspaceInvitation.agency_id == agency_id)
            .order_by(WorkspaceInvitation.created_at.desc()).limit(100)).all()
        return {"role": member.role, "members": [
            {"id": str(row.id), "user_id": str(person.id), "display_name": person.display_name, "email": person.email_snapshot,
             "role": row.role, "active": row.status == "ACTIVE" and row.deactivated_at is None,
             "row_version": row.row_version} for row, person in rows
        ], "invitations": [invite_view(row) for row in invites]}


def invite_staff(sessions: sessionmaker[Session], user: StaffPrincipal, agency_id: UUID, data: InvitationInput, correlation_id: UUID) -> dict[str, object]:
    with sessions() as session, session.begin():
        lock_business(session, agency_id)
        manager, _ = membership(session, user, agency_id, manage=True)
        if manager.role != "OWNER" and data.role != "STAFF":
            raise ApiError(status_code=403, code="WORKSPACE_OWNER_REQUIRED", message="Only an owner may invite owners or administrators.")
        email = str(data.email).casefold()
        existing = session.scalar(select(AgencyMembership.id).join(WorkspaceCredential, WorkspaceCredential.app_user_id == AgencyMembership.app_user_id)
            .where(AgencyMembership.agency_id == agency_id, WorkspaceCredential.email == email,
                   AgencyMembership.status == "ACTIVE", AgencyMembership.deactivated_at.is_(None)).limit(1))
        if existing:
            raise conflict("This staff account already has access. Update its membership instead.")
        result = new_invitation(session, agency_id, email, data.role, user.app_user_id)
        audit(session, agency_id, "WORKSPACE_STAFF_INVITED", correlation_id, user, invitation_id=result["id"], role=data.role)
        return result


def revoke_invitation(sessions: sessionmaker[Session], user: StaffPrincipal, agency_id: UUID, invitation_id: UUID, version: int, correlation_id: UUID) -> None:
    with sessions() as session, session.begin():
        lock_business(session, agency_id)
        manager, _ = membership(session, user, agency_id, manage=True)
        row = session.scalar(select(WorkspaceInvitation).where(WorkspaceInvitation.id == invitation_id, WorkspaceInvitation.agency_id == agency_id).with_for_update())
        if row is None:
            raise ApiError(status_code=404, code="WORKSPACE_INVITATION_NOT_FOUND", message="This invitation is not available.")
        if manager.role != "OWNER" and row.role != "STAFF":
            raise ApiError(status_code=403, code="WORKSPACE_OWNER_REQUIRED", message="Only an owner can revoke this invitation.")
        if row.row_version != version or row.consumed_at or row.revoked_at:
            raise conflict("This invitation changed. Reload its saved status.")
        row.revoked_at = datetime.now(UTC)
        row.pending_name, row.pending_secret_ciphertext, row.pending_password_hash = None, None, None
        audit(session, agency_id, "WORKSPACE_INVITATION_REVOKED", correlation_id, user, invitation_id=str(row.id))


def update_member(sessions: sessionmaker[Session], user: StaffPrincipal, agency_id: UUID, member_id: UUID, data: MembershipInput, correlation_id: UUID) -> None:
    with sessions() as session, session.begin():
        lock_business(session, agency_id)
        manager, _ = membership(session, user, agency_id, manage=True)
        target = session.scalar(select(AgencyMembership).where(AgencyMembership.id == member_id, AgencyMembership.agency_id == agency_id).with_for_update())
        if target is None:
            raise ApiError(status_code=404, code="WORKSPACE_MEMBER_NOT_FOUND", message="This membership is not available.")
        if manager.role != "OWNER" and (target.role != "STAFF" or data.role != "STAFF"):
            raise ApiError(status_code=403, code="WORKSPACE_OWNER_REQUIRED", message="Only an owner can change owner or administrator access.")
        if target.row_version != data.expected_row_version:
            raise conflict("This membership changed. Reload before updating it.")
        target_user = session.get(AppUser, target.app_user_id)
        if target.role == "OWNER" and target.status == "ACTIVE" and target.deactivated_at is None and target_user is not None and target_user.status == "ACTIVE" and target_user.disabled_at is None and (not data.active or data.role != "OWNER"):
            count = session.scalar(select(func.count()).select_from(AgencyMembership).join(AppUser, AppUser.id == AgencyMembership.app_user_id).where(AgencyMembership.agency_id == agency_id,
                AgencyMembership.role == "OWNER", AgencyMembership.status == "ACTIVE", AgencyMembership.deactivated_at.is_(None), AppUser.status == "ACTIVE", AppUser.disabled_at.is_(None)))
            if (count or 0) <= 1:
                raise conflict("Keep at least one active owner. Invite another owner and wait for acceptance first.")
        target.role, target.status = data.role, "ACTIVE" if data.active else "INACTIVE"
        target.deactivated_at = None if data.active else datetime.now(UTC)
        audit(session, agency_id, "WORKSPACE_MEMBERSHIP_UPDATED", correlation_id, user, membership_id=str(target.id), role=target.role, active=data.active)
