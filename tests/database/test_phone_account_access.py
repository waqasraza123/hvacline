from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.customer_access.mfa_crypto import hotp
from insurance_operations.customer_access.schemas import SignupInput
from insurance_operations.database.models.conversation import ConversationSession
from insurance_operations.database.models.customer_account import (
    CustomerAccount,
    CustomerLoginSession,
)
from insurance_operations.database.models.customer_memory import CustomerMemoryPolicy
from insurance_operations.database.models.customer_mfa import CustomerMfaFactor
from insurance_operations.database.models.hvac import Appointment, HvacServiceRequest
from insurance_operations.database.models.identity import Agency, AgencyMembership, AppUser
from insurance_operations.database.models.phone_access import CustomerPhoneAccess
from insurance_operations.database.models.telephony import AgencyInboundNumber, InboundCall
from insurance_operations.errors import ApiError
from insurance_operations.phone_access.schemas import AccessApprovalInput, PhoneAccessContext
from insurance_operations.phone_access.service import PhoneAccountAccessService
from insurance_operations.settings import ApiSettings


@dataclass
class Harness:
    service: PhoneAccountAccessService
    agency_id: UUID
    operator_id: UUID
    token: str
    context: PhoneAccessContext

    @property
    def sessions(self) -> sessionmaker[Session]:
        return self.service.sessions

    def account(self) -> tuple[str, UUID]:
        access = self.service.access
        challenge = access.signup(SignupInput(
            email=f"fictional-{uuid4().hex}@example.com",
            password="fictional long customer security passphrase",
            full_name="Fictional Caller",
        ))
        setup = access.mfa.setup(challenge.challenge_token)
        login = access.mfa.verify(
            challenge.challenge_token,
            hotp(setup.secret, int(datetime.now(UTC).timestamp() // 30)),
        )
        return login.session_token, login.user.id

    def begin(self) -> tuple[str, AccessApprovalInput]:
        code = str(self.service.begin(self.context)["code"])
        preview = self.service.preview(self.token, code)
        return code, AccessApprovalInput(
            access_id=UUID(str(preview["id"])), code=code,
            explicit_confirmation=True,
        )


def make_harness(sessions: sessionmaker[Session]) -> Harness:
    with sessions() as session, session.begin():
        agency = Agency(name="Fictional Caller Business", slug=uuid4().hex, environment_kind="DEVELOPMENT")
        operator = AppUser(auth_subject=uuid4(), display_name="Fictional Operator")
        session.add_all([agency, operator])
        session.flush()
        session.add(AgencyMembership(agency_id=agency.id, app_user_id=operator.id))
        agency_id, operator_id = agency.id, operator.id
    settings = ApiSettings(_env_file=None,
        app_environment="development", api_host="127.0.0.1", api_port=8000,
        database_url="postgresql://synthetic:synthetic@localhost/development",
        development_actor_user_id=operator_id, demo_sandbox_enabled=True,
        demo_admin_token="synthetic-demo-secret-at-least-32-characters",
        website_platform_enabled=True, customer_portal_enabled=True,
        customer_portal_secret="synthetic-customer-secret-at-least-32-characters",
        customer_mfa_encryption_key=Fernet.generate_key().decode(),
        phone_account_access_enabled=True, customer_memory_enabled=True,
    )
    service = PhoneAccountAccessService(sessions, settings)
    harness = Harness(service, agency_id, operator_id, "", PhoneAccessContext(inbound_call_id=uuid4(), conversation_id="pending"))
    harness.token, _ = harness.account()
    now = datetime.now(UTC)
    reference = "synthetic-" + uuid4().hex
    with sessions() as session, session.begin():
        number = AgencyInboundNumber(
            agency_id=agency_id, phone_number_e164="+1555" + str(uuid4().int % 10_000_000).zfill(7),
            label="Fictional line", status="ACTIVE", created_by=operator_id, updated_by=operator_id,
        )
        session.add(number)
        session.flush()
        call = InboundCall(
            agency_id=agency_id, inbound_number_id=number.id, status="CONNECTED",
            caller_number_e164="+15559991002", adapter_name="twilio",
            source_call_reference=reference, received_at=now - timedelta(seconds=5),
            answered_at=now, policy_snapshot={}, adapter_metadata={},
        )
        session.add(call)
        session.flush()
        session.add(ConversationSession(
            agency_id=agency_id, initiated_by=operator_id, channel="PHONE", inbound_call_id=call.id,
            created_at=now,
            status="AUTHORIZED", provider_metadata={"external_session_reference": reference},
            disclosure_accepted_at=now, microphone_consent_at=now, maximum_duration_seconds=180,
            authorization_expires_at=now + timedelta(minutes=3),
            confirmation_expires_at=now + timedelta(minutes=10), authorized_at=now,
        ))
        harness.context = PhoneAccessContext(inbound_call_id=call.id, conversation_id=reference)
    return harness


@pytest.fixture
def harness(migrated_database: Engine, monkeypatch: pytest.MonkeyPatch) -> Iterator[Harness]:
    for name in ApiSettings.model_fields:
        monkeypatch.delenv(name.upper(), raising=False)
    with migrated_database.connect() as connection:
        transaction = connection.begin()
        sessions = sessionmaker(bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint")
        try:
            yield make_harness(sessions)
        finally:
            transaction.rollback()


def test_call_id_alone_never_grants_account_access(harness: Harness) -> None:
    with pytest.raises(ApiError):
        harness.service.appointments(harness.context)
    code, approval = harness.begin()
    assert harness.service.begin(harness.context)["code"] == code
    with pytest.raises(ApiError):
        harness.service.status(harness.context)
    with pytest.raises(ApiError):
        harness.service.preview(None, code)
    first = harness.service.approve(harness.token, approval, uuid4())
    assert harness.service.approve(harness.token, approval, uuid4()) == first
    assert harness.service.status(harness.context)["identity_verified"] is True
    with harness.sessions() as session:
        row = session.get(CustomerPhoneAccess, approval.access_id)
        assert row is not None and row.code_digest is None
        assert row.login_session_id is not None and row.account_id is not None
    with pytest.raises(ApiError):
        harness.service.preview(harness.token, code)
    other_token, _ = harness.account()
    with pytest.raises(ApiError):
        harness.service.approve(other_token, approval, uuid4())
    wrong_context = harness.context.model_copy(update={"conversation_id": "other"})
    with pytest.raises(ApiError):
        harness.service.appointments(wrong_context)


def add_appointment(harness: Harness, token: str, status: str = "CONFIRMED") -> UUID:
    actor, _ = harness.service.access.identity(token)
    now = datetime.now(UTC)
    with harness.sessions() as session, session.begin():
        conversation = ConversationSession(
            agency_id=actor.agency_id, initiated_by=actor.app_user_id,
            channel="BROWSER", input_mode="TEXT", status="AUTHORIZED",
            provider_metadata={}, disclosure_accepted_at=now, microphone_consent_at=None,
            maximum_duration_seconds=180, authorization_expires_at=now + timedelta(minutes=3),
            confirmation_expires_at=now + timedelta(minutes=10), authorized_at=now,
        )
        session.add(conversation)
        session.flush()
        request = HvacServiceRequest(
            agency_id=actor.agency_id, conversation_session_id=conversation.id,
            customer_details={}, service_details={"kind": "MAINTENANCE"},
            fingerprint=uuid4().hex, confirmed_at=now,
        )
        session.add(request)
        session.flush()
        appointment = Appointment(
            agency_id=actor.agency_id, service_request_id=request.id, team_key="fictional",
            starts_at=now + timedelta(days=1), ends_at=now + timedelta(days=1, hours=1),
            status=status, hold_expires_at=now + timedelta(minutes=5),
            idempotency_key=uuid4().hex, fingerprint=uuid4().hex,
        )
        session.add(appointment)
        session.flush()
        return appointment.id


def test_account_reads_only_return_owned_confirmed_appointments(harness: Harness) -> None:
    owned = add_appointment(harness, harness.token)
    add_appointment(harness, harness.token, "HELD")
    other_token, _ = harness.account()
    add_appointment(harness, other_token)
    _, approval = harness.begin()
    harness.service.approve(harness.token, approval, uuid4())
    result = harness.service.appointments(harness.context)
    rows = result["appointments"]
    assert isinstance(rows, list) and len(rows) == 1
    assert rows[0]["id"] == str(owned)
    assert "customer" not in rows[0] and "address" not in rows[0]


@pytest.mark.parametrize("invalidate", ["logout", "session_expiry", "factor", "user", "call", "conversation", "transfer"])
def test_account_proof_is_rechecked_on_every_phone_read(harness: Harness, invalidate: str) -> None:
    _, approval = harness.begin()
    harness.service.approve(harness.token, approval, uuid4())
    actor, account = harness.service.access.identity(harness.token)
    if invalidate == "logout":
        harness.service.access.logout(harness.token)
    else:
        with harness.sessions() as session, session.begin():
            row = session.get(CustomerPhoneAccess, approval.access_id)
            assert row is not None
            if invalidate == "session_expiry":
                source = session.get(CustomerLoginSession, row.login_session_id)
                assert source is not None
                source.expires_at = datetime.now(UTC) - timedelta(seconds=1)
            elif invalidate == "factor":
                factor = session.get(CustomerMfaFactor, account.id)
                assert factor is not None
                factor.version += 1
            elif invalidate == "user":
                user = session.get(AppUser, actor.app_user_id)
                assert user is not None
                user.disabled_at = datetime.now(UTC)
            elif invalidate == "conversation":
                conversation = session.get(ConversationSession, row.conversation_session_id)
                assert conversation is not None
                conversation.authorization_expires_at = datetime.now(UTC) - timedelta(seconds=1)
            else:
                call = session.get(InboundCall, harness.context.inbound_call_id)
                assert call is not None
                call.status = "TRANSFER_PENDING" if invalidate == "transfer" else "COMPLETED"
                if invalidate == "call":
                    call.ended_at = datetime.now(UTC)
    with pytest.raises(ApiError):
        harness.service.appointments(harness.context)


def test_memory_requires_explicit_approval_and_unchanged_consent(harness: Harness) -> None:
    actor, account = harness.service.access.identity(harness.token)
    with harness.sessions() as session, session.begin():
        customer = session.get(CustomerAccount, account.id)
        assert customer is not None
        session.add(CustomerMemoryPolicy(
            account_id=account.id, agency_id=actor.agency_id, enabled=True, revision=1,
            history_after=customer.created_at, updated_at=datetime.now(UTC), retention_days=30,
        ))
    _, approval = harness.begin()
    approval.share_memory = True
    harness.service.approve(harness.token, approval, uuid4())
    assert harness.service.memory_context(harness.context)["identity_verified"] is True
    with harness.sessions() as session, session.begin():
        policy = session.get(CustomerMemoryPolicy, account.id)
        assert policy is not None
        policy.revision += 1
    with pytest.raises(ApiError) as changed:
        harness.service.memory_context(harness.context)
    assert changed.value.status_code == 403
    assert harness.service.appointments(harness.context)["identity_verified"] is True


def test_memory_is_not_included_by_default_and_revocation_is_final(harness: Harness) -> None:
    _, approval = harness.begin()
    harness.service.approve(harness.token, approval, uuid4())
    with pytest.raises(ApiError) as memory:
        harness.service.memory_context(harness.context)
    assert memory.value.status_code == 403
    other_token, _ = harness.account()
    with pytest.raises(ApiError) as other:
        harness.service.revoke(other_token, approval.access_id, uuid4())
    assert other.value.status_code == 404
    harness.service.revoke(harness.token, approval.access_id, uuid4())
    harness.service.revoke(harness.token, approval.access_id, uuid4())
    with pytest.raises(ApiError):
        harness.service.approve(harness.token, approval, uuid4())
    with pytest.raises(ApiError):
        harness.service.begin(harness.context)
    assert harness.service.list_access(harness.token)["items"][0]["status"] == "REVOKED"


def test_bad_call_codes_count_toward_persistent_approval_limits(harness: Harness) -> None:
    for _ in range(10):
        with pytest.raises(ApiError) as invalid:
            harness.service.preview(harness.token, "CALL-0000-0000-0000")
        assert invalid.value.status_code == 409
    with pytest.raises(ApiError) as limited:
        harness.service.preview(harness.token, "CALL-0000-0000-0000")
    assert limited.value.status_code == 429


def test_expired_pending_codes_and_other_business_context_cannot_approve(harness: Harness) -> None:
    code, approval = harness.begin()
    other = make_harness(harness.sessions)
    with pytest.raises(ApiError):
        other.service.preview(other.token, code)
    with pytest.raises(ApiError):
        other.service.begin(harness.context)
    with harness.sessions() as session, session.begin():
        row = session.get(CustomerPhoneAccess, approval.access_id)
        assert row is not None
        row.created_at = datetime.now(UTC) - timedelta(minutes=4)
        row.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    with pytest.raises(ApiError):
        harness.service.preview(harness.token, code)
    with pytest.raises(ApiError):
        harness.service.approve(harness.token, approval, uuid4())


def test_database_rejects_cross_business_and_cross_account_approval(harness: Harness) -> None:
    _, approval = harness.begin()
    harness.service.approve(harness.token, approval, uuid4())
    _, second_account = harness.account()
    with pytest.raises(IntegrityError), harness.sessions() as session, session.begin():
        row = session.get(CustomerPhoneAccess, approval.access_id)
        assert row is not None
        row.account_id = second_account
    with harness.sessions() as session, session.begin():
        other = Agency(name="Other Fictional Business", slug=uuid4().hex, environment_kind="DEVELOPMENT")
        session.add(other)
        session.flush()
        other_id = other.id
    with pytest.raises(IntegrityError), harness.sessions() as session, session.begin():
        row = session.get(CustomerPhoneAccess, approval.access_id)
        assert row is not None
        row.agency_id = other_id


def test_concurrent_accounts_cannot_both_approve_the_same_call(migrated_database: Engine, monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ApiSettings.model_fields:
        monkeypatch.delenv(name.upper(), raising=False)
    harness = make_harness(sessionmaker(migrated_database, expire_on_commit=False))
    second_token, _ = harness.account()
    _, approval = harness.begin()

    def approve(token: str) -> str:
        try:
            harness.service.approve(token, approval, uuid4())
            return "approved"
        except ApiError as error:
            return str(error.status_code)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(approve, [harness.token, second_token]))
    assert sorted(results) == ["409", "approved"]
    with harness.sessions() as session:
        rows = session.scalars(select(CustomerPhoneAccess).where(CustomerPhoneAccess.id == approval.access_id)).all()
        assert len(rows) == 1 and rows[0].approved_at is not None
