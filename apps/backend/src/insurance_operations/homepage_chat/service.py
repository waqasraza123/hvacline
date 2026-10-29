import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.actors import ActorContext, resolve_development_actor
from insurance_operations.approved_faqs import ApprovedFaqService
from insurance_operations.database.models.homepage_chat import (
    HomepageChatDailyUsage,
    HomepageChatVisitor,
)
from insurance_operations.database.models.identity import Agency
from insurance_operations.errors import ApiError
from insurance_operations.homepage_chat.provider import (
    HomepageProviderError,
    HomepageReplyProvider,
)
from insurance_operations.homepage_chat.schemas import (
    HomepageChatInput,
    HomepageChatReply,
    HomepageChatStatus,
)
from insurance_operations.settings import ApiSettings


class HomepageChatService:
    def __init__(
        self,
        sessions: sessionmaker[Session],
        settings: ApiSettings,
        provider: HomepageReplyProvider,
    ) -> None:
        self.sessions = sessions
        self.settings = settings
        self.provider = provider

    def _actor(self, session: Session) -> ActorContext:
        user_id = self.settings.development_actor_user_id
        if user_id is None:
            raise ApiError(
                status_code=503,
                code="HOMEPAGE_CHAT_UNAVAILABLE",
                message="Please sign in to speak with Line.",
            )
        return resolve_development_actor(session, user_id)

    def _hash(self, value: str) -> str:
        secret = self.settings.customer_portal_secret
        if secret is None:
            raise RuntimeError("Homepage chat secret is unavailable")
        return hmac.new(
            secret.get_secret_value().encode(),
            ("homepage-chat/v1:" + value).encode(),
            hashlib.sha256,
        ).hexdigest()

    def status(self, token: str) -> HomepageChatStatus:
        now = datetime.now(UTC)
        with self.sessions() as session:
            actor = self._actor(session)
            row = session.get(
                HomepageChatVisitor, (actor.agency_id, self._hash("visitor:" + token))
            )
            if row and row.expires_at > now:
                if row.state == "USED" or (
                    row.state == "PROCESSING"
                    and row.lease_expires_at is not None
                    and row.lease_expires_at <= now
                ):
                    return HomepageChatStatus(state="used", remaining=0)
                if row.state == "PROCESSING":
                    return HomepageChatStatus(state="busy", remaining=0)
            usage = session.get(HomepageChatDailyUsage, (actor.agency_id, now.date()))
            if usage and usage.generations >= self.settings.homepage_chat_daily_limit:
                return HomepageChatStatus(state="busy", remaining=0)
            return HomepageChatStatus(state="ready", remaining=1)

    def reply(self, token: str, data: HomepageChatInput) -> HomepageChatReply:
        actor, token_hash = self._reserve(token, data)

        def lookup(query: str) -> str:
            result = ApprovedFaqService(session_factory=self.sessions).preview_lookup(
                actor=actor, query=query
            )
            return json.dumps(
                {
                    "matched": result.matched,
                    "approved_answer": result.answer,
                    "fallback_message": result.fallback_message,
                }
            )

        try:
            reply = self.provider.reply(data.message, lookup)
            response = HomepageChatReply(reply=reply)
        except HomepageProviderError as error:
            self._finish(
                actor.agency_id, token_hash, data.request_id, used=error.message_sent
            )
            raise ApiError(
                status_code=503,
                code="HOMEPAGE_CHAT_OUTCOME_UNKNOWN"
                if error.message_sent
                else "HOMEPAGE_CHAT_UNAVAILABLE",
                message="Line’s reply was interrupted. Sign in to continue."
                if error.message_sent
                else "Line couldn’t connect. Your message is kept; please retry.",
                details={"remaining": 0 if error.message_sent else 1},
            ) from error
        except Exception:
            self._finish(actor.agency_id, token_hash, data.request_id, used=True)
            raise
        self._finish(actor.agency_id, token_hash, data.request_id, used=True)
        return response

    def _reserve(self, token: str, data: HomepageChatInput) -> tuple[ActorContext, str]:
        now = datetime.now(UTC)
        token_hash = self._hash("visitor:" + token)
        fingerprint = self._hash("message:" + data.message)
        with self.sessions() as session, session.begin():
            actor = self._actor(session)
            session.execute(
                select(Agency.id).where(Agency.id == actor.agency_id).with_for_update()
            ).scalar_one()
            expired = (
                select(HomepageChatVisitor.token_hash)
                .where(
                    HomepageChatVisitor.agency_id == actor.agency_id,
                    HomepageChatVisitor.expires_at <= now,
                )
                .limit(100)
            )
            session.execute(
                delete(HomepageChatVisitor)
                .where(
                    HomepageChatVisitor.agency_id == actor.agency_id,
                    HomepageChatVisitor.token_hash.in_(expired),
                )
                .execution_options(synchronize_session=False)
            )
            session.execute(
                delete(HomepageChatDailyUsage).where(
                    HomepageChatDailyUsage.agency_id == actor.agency_id,
                    HomepageChatDailyUsage.day < now.date() - timedelta(days=31),
                )
            )
            row = session.get(HomepageChatVisitor, (actor.agency_id, token_hash))
            if row is not None and row.expires_at <= now:
                session.delete(row)
                session.flush()
                row = None
            if row and row.state != "READY":
                used = (
                    row.state == "USED"
                    or row.lease_expires_at is None
                    or row.lease_expires_at <= now
                )
                raise ApiError(
                    status_code=403 if used else 409,
                    code="HOMEPAGE_SIGN_IN_REQUIRED"
                    if used
                    else "HOMEPAGE_CHAT_IN_PROGRESS",
                    message="Sign in to continue with Line."
                    if used
                    else "Your first message is still being answered.",
                )
            if (
                row
                and row.request_id == data.request_id
                and row.request_hash != fingerprint
            ):
                raise ApiError(
                    status_code=409,
                    code="HOMEPAGE_REQUEST_CHANGED",
                    message="Please send your updated message again.",
                )
            usage = session.get(HomepageChatDailyUsage, (actor.agency_id, now.date()))
            active = (
                session.scalar(
                    select(func.count())
                    .select_from(HomepageChatVisitor)
                    .where(
                        HomepageChatVisitor.agency_id == actor.agency_id,
                        HomepageChatVisitor.state == "PROCESSING",
                        HomepageChatVisitor.lease_expires_at > now,
                    )
                )
                or 0
            )
            if (
                usage and usage.generations >= self.settings.homepage_chat_daily_limit
            ) or active >= self.settings.homepage_chat_concurrent_limit:
                raise ApiError(
                    status_code=429,
                    code="HOMEPAGE_CHAT_BUSY",
                    message="Line is busy right now. Please retry shortly or sign in to continue.",
                    headers={"Retry-After": "30"},
                )
            if usage is None:
                usage = HomepageChatDailyUsage(
                    agency_id=actor.agency_id, day=now.date(), generations=0
                )
                session.add(usage)
            usage.generations += 1
            if row is None:
                row = HomepageChatVisitor(
                    agency_id=actor.agency_id,
                    token_hash=token_hash,
                    state="READY",
                    created_at=now,
                    expires_at=now + timedelta(days=30),
                )
                session.add(row)
            row.state = "PROCESSING"
            row.request_id = data.request_id
            row.request_hash = fingerprint
            row.lease_expires_at = now + timedelta(seconds=45)
            return actor, token_hash

    def _finish(
        self, agency_id: UUID, token_hash: str, request_id: UUID, *, used: bool
    ) -> None:
        with self.sessions() as session, session.begin():
            row = session.get(
                HomepageChatVisitor, (agency_id, token_hash), with_for_update=True
            )
            if (
                row is not None
                and row.request_id == request_id
                and row.state == "PROCESSING"
            ):
                row.state = "USED" if used else "READY"
                row.lease_expires_at = None
