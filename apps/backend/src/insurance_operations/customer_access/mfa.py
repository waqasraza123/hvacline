import hashlib
import secrets
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from math import ceil
from uuid import uuid4

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.actors import ActorContext
from insurance_operations.customer_access.mfa_crypto import (
    MfaVault, new_recovery_codes, new_totp_secret, provisioning_uri, valid_totp_counter,
)
from insurance_operations.customer_access.schemas import (
    LoginResponse, MfaChallengeResponse, MfaSetupResponse, MfaStatusResponse,
)
from insurance_operations.database.models.customer_account import CustomerAccount, CustomerLoginSession
from insurance_operations.database.models.customer_mfa import (
    CustomerMfaChallenge, CustomerMfaFactor, CustomerMfaRecoveryCode,
)
from insurance_operations.database.models.identity import AppUser
from insurance_operations.database.models.operations import AuditEvent
from insurance_operations.errors import ApiError
from insurance_operations.settings import ApiSettings

MFA_CHALLENGE_SECONDS = 600
MFA_LOCK_SECONDS = 900


def challenge_rejected() -> ApiError:
    return ApiError(status_code=401, code="MFA_CHALLENGE_REQUIRED",
                    message="Sign in again to continue authenticator verification.")


class CustomerMfaService:
    def __init__(
        self, sessions: sessionmaker[Session], settings: ApiSettings,
        business: Callable[[Session], ActorContext],
        issue_session: Callable[[Session, CustomerAccount, AppUser, int], LoginResponse],
    ) -> None:
        self.sessions, self.settings = sessions, settings
        self.business, self.issue_session = business, issue_session

    def vault(self) -> MfaVault:
        key = self.settings.customer_mfa_encryption_key
        if key is None:
            raise ApiError(status_code=503, code="MFA_UNAVAILABLE",
                           message="Account security is not configured. Try again later.")
        return MfaVault(key.get_secret_value())

    def decrypt(self, ciphertext: str, context: str) -> str:
        try:
            return self.vault().decrypt(ciphertext, context)
        except ValueError as error:
            raise ApiError(status_code=503, code="MFA_UNAVAILABLE",
                           message="Authenticator verification is unavailable. Try again later.") from error

    @staticmethod
    def factor(session: Session, account: CustomerAccount) -> CustomerMfaFactor:
        session.execute(insert(CustomerMfaFactor).values(
            account_id=account.id, agency_id=account.agency_id, version=1, failed_attempts=0,
        ).on_conflict_do_nothing(index_elements=["account_id"]))
        row = session.scalar(select(CustomerMfaFactor).where(
            CustomerMfaFactor.account_id == account.id,
            CustomerMfaFactor.agency_id == account.agency_id,
        ).with_for_update())
        if row is None:
            raise challenge_rejected()
        now = datetime.now(UTC)
        if row.locked_until is not None:
            if row.locked_until > now:
                raise ApiError(status_code=429, code="MFA_LOCKED",
                               message="Too many authenticator attempts. Try again later.",
                               headers={"Retry-After": str(max(1, ceil((row.locked_until - now).total_seconds())))})
            row.failed_attempts, row.locked_until = 0, None
        return row

    @staticmethod
    def factor_context(account: CustomerAccount, factor: CustomerMfaFactor) -> str:
        return f"{account.agency_id}:{account.id}:factor:{factor.version}"

    @staticmethod
    def pending_context(account: CustomerAccount, challenge: CustomerMfaChallenge) -> str:
        return f"{account.agency_id}:{account.id}:pending:{challenge.id}"

    def start(
        self, session: Session, account: CustomerAccount, *, replace: bool = False,
    ) -> MfaChallengeResponse:
        vault = self.vault()
        factor = self.factor(session, account)
        now = datetime.now(UTC)
        session.execute(update(CustomerMfaChallenge).where(
            CustomerMfaChallenge.account_id == account.id,
            CustomerMfaChallenge.consumed_at.is_(None),
        ).values(consumed_at=now, secret_ciphertext=None))
        token = secrets.token_urlsafe(32)
        purpose = "REPLACE" if replace else "ENROLL" if factor.enabled_at is None else "VERIFY"
        challenge = CustomerMfaChallenge(
            id=uuid4(), account_id=account.id, agency_id=account.agency_id,
            token_hash=hashlib.sha256(token.encode()).hexdigest(), purpose=purpose,
            factor_version=factor.version, attempts=0, created_at=now,
            expires_at=now + timedelta(seconds=MFA_CHALLENGE_SECONDS),
        )
        if purpose != "VERIFY":
            challenge.secret_ciphertext = vault.encrypt(
                new_totp_secret(), self.pending_context(account, challenge)
            )
        session.add(challenge)
        return MfaChallengeResponse(
            next_action="verify" if purpose == "VERIFY" else "enroll",
            challenge_token=token, expires_in=MFA_CHALLENGE_SECONDS,
        )

    def context(
        self, session: Session, token: str | None,
    ) -> tuple[CustomerAccount, AppUser, CustomerMfaFactor, CustomerMfaChallenge]:
        if not token or len(token) > 128:
            raise challenge_rejected()
        business = self.business(session)
        initial = session.scalar(select(CustomerMfaChallenge).where(
            CustomerMfaChallenge.token_hash == hashlib.sha256(token.encode()).hexdigest(),
            CustomerMfaChallenge.agency_id == business.agency_id,
        ))
        if initial is None:
            raise challenge_rejected()
        account = session.get(CustomerAccount, initial.account_id)
        if account is None or account.agency_id != business.agency_id:
            raise challenge_rejected()
        user = session.get(AppUser, account.app_user_id)
        if user is None or user.status != "ACTIVE" or user.disabled_at is not None:
            raise challenge_rejected()
        factor = self.factor(session, account)
        challenge = session.get(CustomerMfaChallenge, initial.id,
                                with_for_update=True, populate_existing=True)
        if (
            challenge is None or challenge.consumed_at is not None
            or challenge.expires_at <= datetime.now(UTC) or challenge.attempts >= 5
            or challenge.factor_version != factor.version
        ):
            raise challenge_rejected()
        if challenge.purpose == "ENROLL" and factor.enabled_at is not None:
            raise challenge_rejected()
        return account, user, factor, challenge

    def status(self, token: str | None) -> MfaStatusResponse:
        with self.sessions() as session, session.begin():
            _, _, _, challenge = self.context(session, token)
            return MfaStatusResponse(
                next_action="verify" if challenge.purpose == "VERIFY" else "enroll",
                expires_at=challenge.expires_at,
            )

    def setup(self, token: str | None) -> MfaSetupResponse:
        with self.sessions() as session, session.begin():
            account, _, _, challenge = self.context(session, token)
            if challenge.purpose == "VERIFY" or challenge.secret_ciphertext is None:
                raise challenge_rejected()
            secret = self.decrypt(
                challenge.secret_ciphertext, self.pending_context(account, challenge)
            )
            return MfaSetupResponse(secret=secret, otpauth_uri=provisioning_uri(account.email, secret))

    @staticmethod
    def failure(factor: CustomerMfaFactor, challenge: CustomerMfaChallenge) -> ApiError:
        now = datetime.now(UTC)
        factor.failed_attempts = min(5, factor.failed_attempts + 1)
        challenge.attempts = min(5, challenge.attempts + 1)
        if factor.failed_attempts == 5:
            factor.locked_until = now + timedelta(seconds=MFA_LOCK_SECONDS)
        if challenge.attempts == 5:
            challenge.consumed_at, challenge.secret_ciphertext = now, None
        return ApiError(status_code=401, code="MFA_CODE_INVALID",
                        message="The code is invalid or already used. Wait for a new code, then retry.")

    @staticmethod
    def audit(session: Session, account: CustomerAccount, event: str) -> None:
        session.add(AuditEvent(
            agency_id=account.agency_id, actor_type="DEMO_USER",
            actor_user_id=account.app_user_id, event_type=event,
            occurred_at=datetime.now(UTC), summary="Customer authenticator security updated",
            details={}, correlation_id=uuid4(), event_version=1,
        ))

    @staticmethod
    def revoke_sessions(session: Session, account: CustomerAccount) -> None:
        session.execute(update(CustomerLoginSession).where(
            CustomerLoginSession.account_id == account.id,
            CustomerLoginSession.revoked_at.is_(None),
        ).values(revoked_at=datetime.now(UTC)))

    def verify(self, token: str | None, code: str) -> LoginResponse:
        error: ApiError | None = None
        result: LoginResponse | None = None
        with self.sessions() as session, session.begin():
            account, user, factor, challenge = self.context(session, token)
            vault = self.vault()
            enrolling = challenge.purpose != "VERIFY"
            ciphertext = challenge.secret_ciphertext if enrolling else factor.secret_ciphertext
            if ciphertext is None:
                raise challenge_rejected()
            secret = self.decrypt(ciphertext, self.pending_context(account, challenge)
                                   if enrolling else self.factor_context(account, factor))
            counter = valid_totp_counter(secret, code, datetime.now(UTC).timestamp(),
                                         None if enrolling else factor.last_counter)
            if counter is None:
                error = self.failure(factor, challenge)
                self.audit(session, account, "CUSTOMER_MFA_FAILED")
            else:
                recovery_codes: list[str] | None = None
                now = datetime.now(UTC)
                if enrolling:
                    factor.version += 1
                    factor.secret_ciphertext = vault.encrypt(secret, self.factor_context(account, factor))
                    factor.enabled_at = now
                    factor.last_counter = counter
                    self.revoke_sessions(session, account)
                    session.execute(delete(CustomerMfaRecoveryCode).where(
                        CustomerMfaRecoveryCode.account_id == account.id
                    ))
                    recovery_codes = new_recovery_codes()
                    session.add_all([CustomerMfaRecoveryCode(
                        account_id=account.id, agency_id=account.agency_id,
                        code_hash=vault.recovery_hash(account.id, item), created_at=now,
                    ) for item in recovery_codes])
                factor.last_counter, factor.failed_attempts, factor.locked_until = counter, 0, None
                challenge.consumed_at, challenge.secret_ciphertext = now, None
                session.flush()
                result = self.issue_session(session, account, user, factor.version)
                result.recovery_codes = recovery_codes
                self.audit(session, account, "CUSTOMER_MFA_ENROLLED" if enrolling else "CUSTOMER_MFA_VERIFIED")
        if error is not None:
            raise error
        if result is None:
            raise RuntimeError("MFA verification produced no result")
        return result

    def recover(self, token: str | None, code: str) -> MfaChallengeResponse:
        error: ApiError | None = None
        result: MfaChallengeResponse | None = None
        with self.sessions() as session, session.begin():
            account, _, factor, challenge = self.context(session, token)
            vault = self.vault()
            if challenge.purpose != "VERIFY" or factor.secret_ciphertext is None:
                raise challenge_rejected()
            recovery = session.scalar(select(CustomerMfaRecoveryCode).where(
                CustomerMfaRecoveryCode.account_id == account.id,
                CustomerMfaRecoveryCode.agency_id == account.agency_id,
                CustomerMfaRecoveryCode.code_hash == vault.recovery_hash(account.id, code),
                CustomerMfaRecoveryCode.used_at.is_(None),
            ).with_for_update())
            if recovery is None:
                error = self.failure(factor, challenge)
                self.audit(session, account, "CUSTOMER_MFA_RECOVERY_FAILED")
            else:
                active_secret = self.decrypt(factor.secret_ciphertext, self.factor_context(account, factor))
                recovery.used_at = datetime.now(UTC)
                factor.version += 1
                factor.secret_ciphertext = vault.encrypt(active_secret, self.factor_context(account, factor))
                factor.failed_attempts, factor.locked_until = 0, None
                self.revoke_sessions(session, account)
                session.flush()
                result = self.start(session, account, replace=True)
                self.audit(session, account, "CUSTOMER_MFA_RECOVERY_STARTED")
        if error is not None:
            raise error
        if result is None:
            raise RuntimeError("MFA recovery produced no result")
        return result

    def cancel(self, token: str | None) -> None:
        try:
            with self.sessions() as session, session.begin():
                _, _, _, challenge = self.context(session, token)
                challenge.consumed_at = datetime.now(UTC)
                challenge.secret_ciphertext = None
        except ApiError:
            return
