import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.actors import ActorContext, resolve_development_actor
from insurance_operations.customer_access.passwords import hash_password, verify_password
from insurance_operations.customer_access.mfa import CustomerMfaService
from insurance_operations.customer_access.schemas import AccountView, LoginInput, LoginResponse, MfaChallengeResponse, SignupInput
from insurance_operations.database.models.customer_account import CustomerAccount, CustomerAuthLimit, CustomerLoginSession
from insurance_operations.database.models.customer_mfa import CustomerMfaFactor
from insurance_operations.database.models.identity import Agency, AppUser
from insurance_operations.errors import ApiError
from insurance_operations.settings import ApiSettings

SESSION_LIFETIME_SECONDS = 8 * 60 * 60


def unauthorized() -> ApiError:
    return ApiError(status_code=401, code="CUSTOMER_AUTH_REQUIRED", message="Sign in to continue to your appointments.")


class CustomerAccessService:
    def __init__(self, sessions: sessionmaker[Session], settings: ApiSettings) -> None:
        self.sessions = sessions
        self.settings = settings
        self.mfa = CustomerMfaService(sessions, settings, self._business, self._issue_session)

    def _business(self, session: Session) -> ActorContext:
        if self.settings.development_actor_user_id is None:
            raise unauthorized()
        return resolve_development_actor(session, self.settings.development_actor_user_id)

    def _throttle(self, email: str) -> None:
        for key, limit, seconds in [
            ("all", 30, 60),
            (hashlib.sha256(email.encode()).hexdigest(), 5, 15 * 60),
        ]:
            now = datetime.now(UTC)
            with self.sessions() as session, session.begin():
                session.execute(insert(CustomerAuthLimit).values(
                    key=key, attempts=0, window_started_at=now,
                ).on_conflict_do_nothing())
                row = session.get(CustomerAuthLimit, key, with_for_update=True)
                if row is None:
                    raise RuntimeError("authentication rate limit unavailable")
                if row.window_started_at + timedelta(seconds=seconds) <= now:
                    row.attempts = 0
                    row.window_started_at = now
                if row.attempts >= limit:
                    raise ApiError(status_code=429, code="AUTH_RATE_LIMITED", message="Too many attempts. Please try again later.", headers={"Retry-After": str(seconds)})
                row.attempts += 1

    def signup(self, request: SignupInput) -> MfaChallengeResponse:
        if not request.fictional_data_acknowledged:
            raise ApiError(status_code=422, code="FICTIONAL_DETAILS_REQUIRED", message="Please acknowledge the fictional-data requirement for early access.")
        email = str(request.email).casefold()
        self._throttle(email)
        password_hash = hash_password(request.password.get_secret_value())
        try:
            with self.sessions() as session, session.begin():
                business = self._business(session)
                user = AppUser(auth_subject=uuid4(), display_name=" ".join(request.full_name.split()))
                session.add(user)
                session.flush()
                account = CustomerAccount(agency_id=business.agency_id, app_user_id=user.id, email=email, password_hash=password_hash, created_at=datetime.now(UTC))
                session.add(account)
                session.flush()
                return self.mfa.start(session, account)
        except IntegrityError as error:
            raise ApiError(status_code=409, code="ACCOUNT_UNAVAILABLE", message="We could not create an account with those details. Try signing in instead.") from error

    def login(self, request: LoginInput) -> MfaChallengeResponse:
        email = str(request.email).casefold()
        self._throttle(email)
        with self.sessions() as session, session.begin():
            business = self._business(session)
            account = session.scalar(select(CustomerAccount).where(CustomerAccount.agency_id == business.agency_id, CustomerAccount.email == email))
            password_matches = verify_password(request.password.get_secret_value(), account.password_hash if account else None)
            user = session.get(AppUser, account.app_user_id) if account else None
            if not password_matches or account is None or user is None or user.status != "ACTIVE" or user.disabled_at is not None:
                raise ApiError(status_code=401, code="INVALID_CREDENTIALS", message="That email and password do not match. Please try again.")
            return self.mfa.start(session, account)

    @staticmethod
    def _issue_session(session: Session, account: CustomerAccount, user: AppUser, mfa_version: int) -> LoginResponse:
        factor = session.get(CustomerMfaFactor, account.id)
        if (
            factor is None or factor.agency_id != account.agency_id
            or factor.enabled_at is None or factor.version != mfa_version
        ):
            raise unauthorized()
        token = secrets.token_urlsafe(32)
        session.add(CustomerLoginSession(account_id=account.id, token_hash=hashlib.sha256(token.encode()).hexdigest(), expires_at=datetime.now(UTC) + timedelta(seconds=SESSION_LIFETIME_SECONDS), mfa_verified_at=datetime.now(UTC), mfa_version=mfa_version))
        return LoginResponse(user=AccountView(id=account.id, full_name=user.display_name, email=account.email), session_token=token, expires_in=SESSION_LIFETIME_SECONDS)

    def identity(self, token: str | None) -> tuple[ActorContext, AccountView]:
        if not token or len(token) > 128:
            raise unauthorized()
        with self.sessions() as session:
            result = session.execute(select(CustomerLoginSession, CustomerAccount, AppUser, Agency)
                .join(CustomerAccount, CustomerAccount.id == CustomerLoginSession.account_id)
                .join(AppUser, AppUser.id == CustomerAccount.app_user_id)
                .join(Agency, Agency.id == CustomerAccount.agency_id)
                .join(CustomerMfaFactor, CustomerMfaFactor.account_id == CustomerAccount.id)
                .where(CustomerLoginSession.token_hash == hashlib.sha256(token.encode()).hexdigest(), CustomerLoginSession.revoked_at.is_(None), CustomerLoginSession.expires_at > datetime.now(UTC), CustomerLoginSession.mfa_verified_at.is_not(None), CustomerLoginSession.mfa_version == CustomerMfaFactor.version, CustomerMfaFactor.enabled_at.is_not(None), CustomerMfaFactor.agency_id == Agency.id, AppUser.status == "ACTIVE", AppUser.disabled_at.is_(None), Agency.archived_at.is_(None), Agency.environment_kind == "DEVELOPMENT")
            ).one_or_none()
            if result is None:
                raise unauthorized()
            _, account, user, agency = result
            business = self._business(session)
            if agency.id != business.agency_id:
                raise unauthorized()
            return ActorContext(app_user_id=user.id, display_name=user.display_name, agency_id=agency.id, agency_name=agency.name, agency_environment=agency.environment_kind), AccountView(id=account.id, full_name=user.display_name, email=account.email)

    def logout(self, token: str | None) -> None:
        if not token or len(token) > 128:
            return
        with self.sessions() as session, session.begin():
            row = session.scalar(select(CustomerLoginSession).where(CustomerLoginSession.token_hash == hashlib.sha256(token.encode()).hexdigest()).with_for_update())
            if row:
                row.revoked_at = datetime.now(UTC)
