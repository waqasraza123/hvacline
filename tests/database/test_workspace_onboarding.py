from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from cryptography.fernet import Fernet
import pytest
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.database.models.identity import AgencyMembership
from insurance_operations.database.models.workspace import WorkspaceCredential, WorkspaceInvitation, WorkspaceSession
from insurance_operations.errors import ApiError
from insurance_operations.settings import ApiSettings
from insurance_operations.workspace.access import StaffPrincipal, digest, login, membership, principal
from insurance_operations.workspace.business import accept_invitation, create_business, enrollment_confirm, enrollment_start, invite_staff, revoke_invitation, update_member
from insurance_operations.workspace.schemas import BusinessInput, EnrollmentConfirmation, EnrollmentInput, InvitationInput, LoginInput, MembershipInput
from insurance_operations.customer_access.mfa_crypto import hotp


def configuration() -> ApiSettings:
    return ApiSettings(_env_file=None, app_environment="development", api_host="127.0.0.1", api_port=8000,
        database_url="postgresql://synthetic:synthetic@localhost/dev", workspace_portal_enabled=True,
        workspace_portal_secret="synthetic-staff-portal-secret-at-least-32", workspace_mfa_encryption_key=Fernet.generate_key().decode())


def enroll(sessions: sessionmaker[Session], config: ApiSettings, token: str) -> tuple[StaffPrincipal, str, str]:
    start = enrollment_start(sessions, config, EnrollmentInput(token=token, display_name="Fictional Staff", password="fictional long staff password"))
    secret = str(start["secret"])
    code = hotp(secret, int(datetime.now(UTC).timestamp() // 30))
    result = enrollment_confirm(sessions, config, EnrollmentConfirmation(token=token, code=code), uuid4())
    session_token = str(result["session_token"])
    with sessions() as session:
        user = principal(session, session_token)
    return user, session_token, secret


def business(sessions: sessionmaker[Session], config: ApiSettings, email: str) -> tuple[UUID, str]:
    result = create_business(sessions, config, BusinessInput(creation_key=uuid4(), name="Fictional HVAC Business", slug="fictional-" + uuid4().hex, owner_email=email), uuid4())
    invitation = result["invitation"]
    assert isinstance(invitation, dict)
    return UUID(str(result["id"])), str(invitation["invitation_token"])


def test_business_creation_is_idempotent_and_does_not_grant_access_before_mfa(migrated_database: Engine) -> None:
    sessions, config = sessionmaker(migrated_database), configuration()
    data = BusinessInput(creation_key=uuid4(), name="Fictional HVAC Business", slug="fictional-" + uuid4().hex, owner_email="owner-" + uuid4().hex + "@example.com")
    created = create_business(sessions, config, data, uuid4())
    replayed = create_business(sessions, config, data, uuid4())
    assert created["id"] == replayed["id"]
    assert replayed["replayed"] is True and replayed["invitation"] is None
    with sessions() as session:
        assert session.scalar(select(AgencyMembership.id).where(AgencyMembership.agency_id == UUID(str(created["id"])))) is None
    invitation = created["invitation"]
    assert isinstance(invitation, dict)
    user, token, _ = enroll(sessions, config, str(invitation["invitation_token"]))
    with sessions() as session:
        member, _ = membership(session, user, UUID(str(created["id"])))
        assert member.role == "OWNER"
        assert session.get(WorkspaceSession, digest(token)) is not None
    with pytest.raises(ApiError):
        enrollment_start(sessions, config, EnrollmentInput(token=str(invitation["invitation_token"]), display_name="Other", password="fictional different password"))


def test_staff_is_tenant_scoped_and_role_changes_invalidate_business_access(migrated_database: Engine) -> None:
    sessions, config = sessionmaker(migrated_database), configuration()
    agency, token = business(sessions, config, "owner-" + uuid4().hex + "@example.com")
    owner, _, _ = enroll(sessions, config, token)
    second, _ = business(sessions, config, "other-" + uuid4().hex + "@example.com")
    invitation = invite_staff(sessions, owner, agency, InvitationInput(email="staff-" + uuid4().hex + "@example.com", role="STAFF"), uuid4())
    staff, staff_token, _ = enroll(sessions, config, str(invitation["invitation_token"]))
    with sessions() as session:
        member, _ = membership(session, staff, agency)
        member_id, version = member.id, member.row_version
        with pytest.raises(ApiError) as other:
            membership(session, staff, second)
        assert other.value.status_code == 404
    with pytest.raises(ApiError) as forbidden:
        invite_staff(sessions, staff, agency, InvitationInput(email="unapproved@example.com", role="OWNER"), uuid4())
    assert forbidden.value.status_code == 403
    update_member(sessions, owner, agency, member_id, MembershipInput(role="STAFF", active=False, expected_row_version=version), uuid4())
    with sessions() as session:
        still_signed_in = principal(session, staff_token)
        with pytest.raises(ApiError):
            membership(session, still_signed_in, agency)


def test_concurrent_owner_changes_cannot_remove_the_last_owner(migrated_database: Engine) -> None:
    sessions, config = sessionmaker(migrated_database), configuration()
    agency, token = business(sessions, config, "first-" + uuid4().hex + "@example.com")
    first, _, _ = enroll(sessions, config, token)
    invitation = invite_staff(sessions, first, agency, InvitationInput(email="second-" + uuid4().hex + "@example.com", role="OWNER"), uuid4())
    second, _, _ = enroll(sessions, config, str(invitation["invitation_token"]))

    def demote(user: StaffPrincipal) -> str:
        with sessions() as session:
            row, _ = membership(session, user, agency)
            identifier, version = row.id, row.row_version
        try:
            update_member(sessions, user, agency, identifier, MembershipInput(role="STAFF", active=True, expected_row_version=version), uuid4())
            return "updated"
        except ApiError as error:
            return str(error.status_code)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(demote, [first, second]))
    assert sorted(results) == ["409", "updated"]


def test_revoked_invitation_and_replayed_authenticator_cannot_create_access(migrated_database: Engine) -> None:
    sessions, config = sessionmaker(migrated_database), configuration()
    agency, token = business(sessions, config, "owner-" + uuid4().hex + "@example.com")
    owner, _, factor = enroll(sessions, config, token)
    invitation = invite_staff(sessions, owner, agency, InvitationInput(email="revoked-" + uuid4().hex + "@example.com", role="STAFF"), uuid4())
    revoke_invitation(sessions, owner, agency, UUID(str(invitation["id"])), int(invitation["row_version"]), uuid4())
    with pytest.raises(ApiError):
        enrollment_start(sessions, config, EnrollmentInput(token=str(invitation["invitation_token"]), display_name="Revoked Staff", password="fictional long staff password"))
    with sessions() as session:
        credential = session.get(WorkspaceCredential, owner.app_user_id)
        assert credential is not None
        consumed_counter = credential.last_totp_counter
    reused = LoginInput(email=owner.email, password="fictional long staff password", code=hotp(factor, consumed_counter))
    with pytest.raises(ApiError) as rejected:
        login(sessions, config, reused)
    assert rejected.value.status_code == 401
    with sessions() as session, session.begin():
        row = session.scalar(select(WorkspaceCredential).where(WorkspaceCredential.app_user_id == owner.app_user_id))
        assert row is not None
        row.last_totp_counter = int(datetime.now(UTC).timestamp() // 30) - 1
    signed_in = login(sessions, config, reused.model_copy(update={"code": hotp(factor, int(datetime.now(UTC).timestamp() // 30))}))
    with sessions() as session, session.begin():
        row = session.get(WorkspaceSession, digest(str(signed_in["session_token"])))
        assert row is not None
        row.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    with sessions() as session, pytest.raises(ApiError):
        principal(session, str(signed_in["session_token"]))


def test_existing_staff_join_requires_matching_identity_and_an_authorized_inviter(migrated_database: Engine) -> None:
    sessions, config = sessionmaker(migrated_database), configuration()
    first_agency, first_token = business(sessions, config, "first-" + uuid4().hex + "@example.com")
    first, _, _ = enroll(sessions, config, first_token)
    second_agency, second_token = business(sessions, config, "second-" + uuid4().hex + "@example.com")
    second, _, _ = enroll(sessions, config, second_token)
    invited = invite_staff(sessions, second, second_agency, InvitationInput(email=first.email, role="STAFF"), uuid4())
    with pytest.raises(ApiError) as mismatch:
        accept_invitation(sessions, second, str(invited["invitation_token"]), uuid4())
    assert mismatch.value.status_code == 403
    accept_invitation(sessions, first, str(invited["invitation_token"]), uuid4())
    with sessions() as session:
        assert membership(session, first, first_agency)[0].role == "OWNER"
        assert membership(session, first, second_agency)[0].role == "STAFF"
    delegated = invite_staff(sessions, second, second_agency, InvitationInput(email="admin-" + uuid4().hex + "@example.com", role="ADMIN"), uuid4())
    admin, _, _ = enroll(sessions, config, str(delegated["invitation_token"]))
    pending = invite_staff(sessions, admin, second_agency, InvitationInput(email="pending-" + uuid4().hex + "@example.com", role="STAFF"), uuid4())
    with sessions() as session:
        member, _ = membership(session, admin, second_agency)
        member_id, version = member.id, member.row_version
    update_member(sessions, second, second_agency, member_id, MembershipInput(role="STAFF", active=True, expected_row_version=version), uuid4())
    setup = enrollment_start(sessions, config, EnrollmentInput(token=str(pending["invitation_token"]), display_name="Pending Staff", password="fictional long staff password"))
    with pytest.raises(ApiError) as changed:
        enrollment_confirm(sessions, config, EnrollmentConfirmation(token=str(pending["invitation_token"]), code=hotp(str(setup["secret"]), int(datetime.now(UTC).timestamp() // 30))), uuid4())
    assert changed.value.status_code == 409


def test_failed_enrollment_attempts_persist_and_never_create_a_staff_account(migrated_database: Engine) -> None:
    sessions, config = sessionmaker(migrated_database), configuration()
    email = "limited-" + uuid4().hex + "@example.com"
    agency, token = business(sessions, config, email)
    setup = enrollment_start(sessions, config, EnrollmentInput(token=token, display_name="Fictional Staff", password="fictional long staff password"))
    counter = int(datetime.now(UTC).timestamp() // 30)
    valid_codes = {hotp(str(setup["secret"]), value) for value in range(counter - 1, counter + 2)}
    invalid = next(f"{value:06d}" for value in range(10) if f"{value:06d}" not in valid_codes)
    for _ in range(5):
        with pytest.raises(ApiError):
            enrollment_confirm(sessions, config, EnrollmentConfirmation(token=token, code=invalid), uuid4())
    with sessions() as session:
        row = session.scalar(select(WorkspaceInvitation).where(WorkspaceInvitation.agency_id == agency))
        assert row is not None and row.failed_attempts == 5 and row.consumed_at is None
        assert session.scalar(select(WorkspaceCredential.app_user_id).where(WorkspaceCredential.email == email)) is None
