import hashlib
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.customer_access.mfa_crypto import hotp
from insurance_operations.customer_access.schemas import LoginInput, LoginResponse, MfaChallengeResponse, SignupInput
from insurance_operations.customer_access.service import CustomerAccessService
from insurance_operations.database.models.customer_account import CustomerAccount, CustomerLoginSession
from insurance_operations.database.models.customer_memory import CustomerWhatsAppIdentity
from insurance_operations.database.models.customer_mfa import (
    CustomerMfaChallenge, CustomerMfaFactor, CustomerMfaRecoveryCode,
)
from insurance_operations.database.models.identity import Agency, AgencyMembership, AppUser
from insurance_operations.errors import ApiError
from insurance_operations.settings import ApiSettings, DatabaseSettings

EMAIL = "fictional-mfa@example.test"
PASSWORD = "fictional account security passphrase"


@dataclass
class MfaHarness:
    access: CustomerAccessService
    now: datetime

    def login(self) -> MfaChallengeResponse:
        return self.access.login(LoginInput(email=EMAIL, password=PASSWORD))

    def enroll(self) -> tuple[LoginResponse, str]:
        challenge = self.access.signup(SignupInput(
            email=EMAIL, password=PASSWORD, full_name="Fictional MFA Customer",
        ))
        setup = self.access.mfa.setup(challenge.challenge_token)
        verified = self.access.mfa.verify(
            challenge.challenge_token, hotp(setup.secret, int(self.now.timestamp() // 30) - 1),
        )
        return verified, setup.secret


@pytest.fixture
def harness(migrated_database: Engine, database_settings: DatabaseSettings) -> Iterator[MfaHarness]:
    with migrated_database.connect() as connection:
        transaction = connection.begin()
        sessions = sessionmaker(
            bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint",
        )
        with sessions() as session, session.begin():
            business = Agency(name="Fictional MFA HVAC", slug=f"mfa-{uuid4()}", environment_kind="DEVELOPMENT")
            operator = AppUser(auth_subject=uuid4(), display_name="Fictional configured operator")
            session.add_all([business, operator])
            session.flush()
            session.add(AgencyMembership(agency_id=business.id, app_user_id=operator.id))
        settings = ApiSettings(
            _env_file=None, app_environment="development", api_host="127.0.0.1", api_port=8000,
            database_url=database_settings.runtime_database_url,
            database_ssl_mode=database_settings.database_ssl_mode,
            development_actor_user_id=operator.id,
            customer_mfa_encryption_key=Fernet.generate_key().decode(),
        )
        now = datetime.now(UTC)
        try:
            with patch("insurance_operations.customer_access.mfa.datetime", wraps=datetime) as clock:
                clock.now.return_value = now
                yield MfaHarness(CustomerAccessService(sessions, settings), now)
        finally:
            transaction.rollback()


def test_new_and_legacy_accounts_have_no_access_until_authenticator_proof(harness: MfaHarness) -> None:
    access = harness.access
    challenge = access.signup(SignupInput(
        email=EMAIL, password=PASSWORD, full_name="Fictional MFA Customer",
    ))
    assert challenge.next_action == "enroll"
    with access.sessions() as session, session.begin():
        account = session.scalar(select(CustomerAccount).where(CustomerAccount.email == EMAIL))
        assert account is not None
        assert session.scalar(select(func.count()).select_from(CustomerLoginSession)) == 0
        legacy = "fictional-legacy-session-for-mfa-test"
        session.add(CustomerLoginSession(
            account_id=account.id, token_hash=hashlib.sha256(legacy.encode()).hexdigest(),
            expires_at=harness.now + timedelta(hours=1),
        ))
    for token in (challenge.challenge_token, legacy, None):
        with pytest.raises(ApiError) as rejected:
            access.identity(token)
        assert rejected.value.status_code == 401
    replacement = harness.login()
    assert replacement.next_action == "enroll"
    with pytest.raises(ApiError):
        access.mfa.setup(challenge.challenge_token)
    setup = access.mfa.setup(replacement.challenge_token)
    verified = access.mfa.verify(replacement.challenge_token, hotp(setup.secret, int(harness.now.timestamp() // 30)))
    assert access.identity(verified.session_token)[1].email == EMAIL
    assert verified.recovery_codes is not None and len(verified.recovery_codes) == 10
    with pytest.raises(ApiError):
        access.mfa.verify(replacement.challenge_token, hotp(setup.secret, int(harness.now.timestamp() // 30)))
    with pytest.raises(ApiError):
        access.identity(legacy)
    with access.sessions() as session:
        factor = session.scalar(select(CustomerMfaFactor))
        assert factor is not None and factor.secret_ciphertext is not None
        assert setup.secret not in factor.secret_ciphertext
        assert session.scalar(select(func.count()).select_from(CustomerMfaRecoveryCode)) == 10


def test_password_login_still_requires_new_non_replayed_totp(harness: MfaHarness) -> None:
    verified, secret = harness.enroll()
    challenge = harness.login()
    assert challenge.next_action == "verify"
    with pytest.raises(ApiError):
        harness.access.identity(challenge.challenge_token)
    with pytest.raises(ApiError):
        harness.access.mfa.setup(challenge.challenge_token)
    with pytest.raises(ApiError):
        harness.access.mfa.verify(challenge.challenge_token, hotp(secret, int(harness.now.timestamp() // 30) - 1))
    logged_in = harness.access.mfa.verify(challenge.challenge_token, hotp(secret, int(harness.now.timestamp() // 30)))
    assert harness.access.identity(logged_in.session_token)[1].id == verified.user.id
    second = harness.login()
    with pytest.raises(ApiError):
        harness.access.mfa.verify(second.challenge_token, hotp(secret, int(harness.now.timestamp() // 30)))


def test_wrong_attempts_commit_and_password_challenges_cannot_reset_lockout(harness: MfaHarness) -> None:
    _, secret = harness.enroll()
    counter = int(harness.now.timestamp() // 30)
    valid = {hotp(secret, counter + offset) for offset in (-1, 0, 1)}
    wrong = next(f"{value:06}" for value in range(1_000_000) if f"{value:06}" not in valid)
    challenge = harness.login()
    for attempt in range(5):
        if attempt == 2:
            challenge = harness.login()
        with pytest.raises(ApiError) as rejected:
            harness.access.mfa.verify(challenge.challenge_token, wrong)
        assert rejected.value.code == "MFA_CODE_INVALID"
    with harness.access.sessions() as session:
        factor = session.scalar(select(CustomerMfaFactor))
        assert factor is not None and factor.failed_attempts == 5
        assert factor.locked_until == harness.now + timedelta(minutes=15)
    with pytest.raises(ApiError) as locked:
        harness.login()
    assert locked.value.status_code == 429


def test_expired_and_foreign_tenant_challenges_fail_closed(harness: MfaHarness) -> None:
    _, secret = harness.enroll()
    challenge = harness.login()
    code = hotp(secret, int(harness.now.timestamp() // 30))
    with harness.access.sessions() as session, session.begin():
        pending = session.scalar(select(CustomerMfaChallenge).where(CustomerMfaChallenge.consumed_at.is_(None)))
        assert pending is not None
        pending.expires_at = harness.now - timedelta(seconds=1)
    with pytest.raises(ApiError):
        harness.access.mfa.verify(challenge.challenge_token, code)
    challenge = harness.login()
    with harness.access.sessions() as session, session.begin():
        foreign = Agency(name="Other MFA HVAC", slug=f"other-mfa-{uuid4()}", environment_kind="DEVELOPMENT")
        operator = AppUser(auth_subject=uuid4(), display_name="Other operator")
        session.add_all([foreign, operator])
        session.flush()
        session.add(AgencyMembership(agency_id=foreign.id, app_user_id=operator.id))
    foreign_settings = harness.access.settings.model_copy(update={"development_actor_user_id": operator.id})
    foreign_access = CustomerAccessService(harness.access.sessions, foreign_settings)
    with pytest.raises(ApiError):
        foreign_access.mfa.verify(challenge.challenge_token, code)


def test_recovery_is_one_use_and_forces_verified_replacement_before_access(harness: MfaHarness) -> None:
    verified, _ = harness.enroll()
    assert verified.recovery_codes is not None
    with harness.access.sessions() as session, session.begin():
        account = session.get(CustomerAccount, verified.user.id)
        factor = session.get(CustomerMfaFactor, verified.user.id)
        assert account is not None and factor is not None
        original_version = factor.version
        session.add(CustomerWhatsAppIdentity(
            account_id=account.id, agency_id=account.agency_id, phone_number_id="fictional-meta-number",
            caller_digest="a" * 64, verified_at=harness.now,
            expires_at=harness.now + timedelta(days=1), mfa_version=factor.version,
        ))
    challenge = harness.login()
    replacement = harness.access.mfa.recover(challenge.challenge_token, verified.recovery_codes[0])
    assert replacement.next_action == "enroll"
    for token in (verified.session_token, replacement.challenge_token):
        with pytest.raises(ApiError):
            harness.access.identity(token)
    with pytest.raises(ApiError):
        harness.access.mfa.recover(challenge.challenge_token, verified.recovery_codes[0])
    with harness.access.sessions() as session:
        factor = session.get(CustomerMfaFactor, verified.user.id)
        link = session.scalar(select(CustomerWhatsAppIdentity))
        assert factor is not None and factor.version > original_version
        assert link is not None and link.mfa_version != factor.version
    setup = harness.access.mfa.setup(replacement.challenge_token)
    renewed = harness.access.mfa.verify(replacement.challenge_token, hotp(setup.secret, int(harness.now.timestamp() // 30)))
    assert harness.access.identity(renewed.session_token)[1].id == verified.user.id
    challenge = harness.login()
    with pytest.raises(ApiError):
        harness.access.mfa.recover(challenge.challenge_token, verified.recovery_codes[0])
