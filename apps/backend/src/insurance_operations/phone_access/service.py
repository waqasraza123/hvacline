import hashlib
import hmac
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.actors import ActorContext
from insurance_operations.customer_access.service import CustomerAccessService
from insurance_operations.customer_memory.service import CustomerMemoryService
from insurance_operations.database.models.conversation import ConversationSession
from insurance_operations.database.models.customer_account import CustomerAuthLimit
from insurance_operations.database.models.customer_memory import CustomerMemoryPolicy
from insurance_operations.database.models.hvac import (
    Appointment,
    BusinessSchedule,
    HvacServiceRequest,
)
from insurance_operations.database.models.operations import AuditEvent
from insurance_operations.database.models.phone_access import CustomerPhoneAccess
from insurance_operations.database.models.telephony import AgencyInboundNumber, InboundCall
from insurance_operations.errors import ApiError
from insurance_operations.phone_access.schemas import (
    AccessApprovalInput,
    PhoneAccessContext,
)
from insurance_operations.settings import ApiSettings, RuntimeEnvironment
from insurance_operations.telephony.phone_service import (
    require_phone_call,
    require_phone_session_context,
)


def unavailable() -> ApiError:
    return ApiError(
        status_code=409,
        code="PHONE_ACCESS_UNAVAILABLE",
        message=(
            "This call approval is unavailable or expired. "
            "Start a new call to try again."
        ),
        headers={"Cache-Control": "no-store"},
    )


class PhoneAccountAccessService:
    def __init__(self, sessions: sessionmaker[Session], settings: ApiSettings) -> None:
        self.sessions = sessions
        self.settings = settings
        self.access = CustomerAccessService(sessions, settings)
        self.memory = CustomerMemoryService(sessions, settings)

    def enabled(self) -> None:
        if not (
            self.settings.phone_account_access_enabled
            and self.settings.customer_portal_enabled
            and self.settings.demo_sandbox_enabled
            and self.settings.app_environment is RuntimeEnvironment.DEVELOPMENT
        ):
            raise ApiError(
                status_code=404,
                code="PHONE_ACCESS_DISABLED",
                message="Telephone account access is not available.",
                headers={"Cache-Control": "no-store"},
            )

    def _keyed_hash(self, value: str) -> str:
        secret = self.settings.customer_portal_secret
        if secret is None:
            raise unavailable()
        return hmac.new(
            secret.get_secret_value().encode(), value.encode(), hashlib.sha256
        ).hexdigest()

    def _code(self, row: CustomerPhoneAccess) -> str:
        value = self._keyed_hash(
            f"phone-approval-code:{row.agency_id}:{row.conversation_session_id}:{row.id}"
        )[:12].upper()
        return "CALL-" + "-".join(
            value[index : index + 4] for index in range(0, 12, 4)
        )

    def _digest(self, code: str) -> str:
        return self._keyed_hash(f"phone-approval-digest:{code}")

    def _throttle(self, account_id: UUID) -> None:
        for key, maximum, seconds in (
            ("phone-approval-all", 60, 60),
            (f"phone-approval:{account_id}", 10, 900),
        ):
            now = datetime.now(UTC)
            with self.sessions() as session, session.begin():
                session.execute(
                    insert(CustomerAuthLimit)
                    .values(
                        key=key, attempts=0, window_started_at=now
                    )
                    .on_conflict_do_nothing()
                )
                limit = session.get(CustomerAuthLimit, key, with_for_update=True)
                if limit is None:
                    raise unavailable()
                if limit.window_started_at + timedelta(seconds=seconds) <= now:
                    limit.attempts, limit.window_started_at = 0, now
                if limit.attempts >= maximum:
                    raise ApiError(
                        status_code=429,
                        code="PHONE_APPROVAL_LIMITED",
                        message="Too many call approval attempts. Try again later.",
                        headers={
                            "Retry-After": str(seconds), "Cache-Control": "no-store"
                        },
                    )
                limit.attempts += 1

    @staticmethod
    def _active_call(
        session: Session, context: PhoneAccessContext, *, lock: bool = False
    ) -> tuple[ConversationSession, InboundCall]:
        conversation = require_phone_session_context(session, context, for_update=lock)
        call = require_phone_call(session, context.inbound_call_id)
        if (
            conversation.authorization_expires_at <= datetime.now(UTC)
            or conversation.authorized_at is None
            or conversation.ended_at is not None
            or call.ended_at is not None
            or call.status != "CONNECTED"
        ):
            raise unavailable()
        return conversation, call

    def _stored_call(
        self, session: Session, row: CustomerPhoneAccess, *, lock: bool = False
    ) -> tuple[ConversationSession, InboundCall]:
        conversation = session.get(ConversationSession, row.conversation_session_id)
        if conversation is None or conversation.inbound_call_id is None:
            raise unavailable()
        reference = conversation.provider_metadata.get("external_session_reference")
        if not isinstance(reference, str):
            raise unavailable()
        conversation, call = self._active_call(
            session,
            PhoneAccessContext(
                inbound_call_id=conversation.inbound_call_id, conversation_id=reference
            ),
            lock=lock,
        )
        if row.agency_id != conversation.agency_id:
            raise unavailable()
        return conversation, call

    @staticmethod
    def _audit(
        session: Session,
        row: CustomerPhoneAccess,
        actor: ActorContext,
        event: str,
        correlation_id: UUID,
    ) -> None:
        session.add(
            AuditEvent(
                agency_id=row.agency_id,
                actor_type="DEMO_USER",
                actor_user_id=actor.app_user_id,
                event_type=event,
                summary="Telephone account approval updated",
                occurred_at=datetime.now(UTC),
                correlation_id=correlation_id,
                event_version=1,
                details={
                    "access_id": str(row.id),
                    "conversation_session_id": str(row.conversation_session_id),
                    "share_memory": row.share_memory,
                },
            )
        )

    def begin(self, context: PhoneAccessContext) -> dict[str, object]:
        self.enabled()
        with self.sessions() as session, session.begin():
            conversation, _ = self._active_call(session, context, lock=True)
            business = self.access._business(session)
            if business.agency_id != conversation.agency_id:
                raise unavailable()
            row = session.scalar(
                select(CustomerPhoneAccess).where(
                    CustomerPhoneAccess.conversation_session_id == conversation.id
                )
            )
            if row is not None and (
                row.revoked_at or row.expires_at <= datetime.now(UTC)
            ):
                raise unavailable()
            if row is not None and row.approved_at:
                self._verified_actor(session, row)
                return {
                    "status": "APPROVED", "code": None,
                    "expires_at": row.expires_at.isoformat(),
                }
            if row is None:
                now = datetime.now(UTC)
                if conversation.authorization_expires_at <= now:
                    raise unavailable()
                row = CustomerPhoneAccess(
                    id=uuid4(),
                    agency_id=conversation.agency_id,
                    conversation_session_id=conversation.id,
                    created_at=now,
                    expires_at=min(
                        conversation.authorization_expires_at,
                        now + timedelta(minutes=3),
                    ),
                    share_memory=False,
                )
                row.code_digest = self._digest(self._code(row))
                session.add(row)
                session.flush()
            if row.code_digest is None or not hmac.compare_digest(
                row.code_digest, self._digest(self._code(row))
            ):
                raise unavailable()
            return {
                "status": "PENDING", "code": self._code(row),
                "expires_at": row.expires_at.isoformat(),
                "instructions": (
                    "Enter this call code in Telephone access in your signed-in "
                    "HVACLine account. Approve only the call you are on. Never "
                    "tell the agent your password, authenticator or recovery codes."
                ),
            }

    def preview(self, token: str | None, code: str) -> dict[str, object]:
        self.enabled()
        _, account = self.access.identity(token)
        self._throttle(account.id)
        with self.sessions() as session:
            actor, _, _ = self.access.session_identity(session, token)
            row = session.scalar(
                select(CustomerPhoneAccess).where(
                    CustomerPhoneAccess.agency_id == actor.agency_id,
                    CustomerPhoneAccess.code_digest == self._digest(code),
                    CustomerPhoneAccess.approved_at.is_(None),
                    CustomerPhoneAccess.revoked_at.is_(None),
                    CustomerPhoneAccess.expires_at > datetime.now(UTC),
                )
            )
            if row is None:
                raise unavailable()
            conversation, call = self._stored_call(session, row)
            return self._view(session, row, actor, call, conversation)

    def _view(
        self,
        session: Session,
        row: CustomerPhoneAccess,
        actor: ActorContext,
        call: InboundCall,
        conversation: ConversationSession,
    ) -> dict[str, object]:
        number = session.get(AgencyInboundNumber, call.inbound_number_id)
        account = self.memory.account(session, actor)
        policy = session.get(CustomerMemoryPolicy, account.id)
        return {
            "id": str(row.id),
            "business_name": actor.agency_name,
            "caller_last_four": (
                call.caller_number_e164[-4:] if call.caller_number_e164 else None
            ),
            "called_last_four": (
                number.phone_number_e164[-4:]
                if number and number.agency_id == row.agency_id else None
            ),
            "created_at": row.created_at.isoformat(),
            "expires_at": row.expires_at.isoformat(),
            "share_memory": row.share_memory,
            "memory_available": bool(
                self.settings.customer_memory_enabled
                and policy is not None and policy.enabled
                and conversation.created_at >= policy.history_after
            ),
        }

    def approve(
        self, token: str | None, data: AccessApprovalInput, correlation_id: UUID
    ) -> dict[str, object]:
        self.enabled()
        _, account = self.access.identity(token)
        self._throttle(account.id)
        with self.sessions() as session, session.begin():
            actor, current_account, source = self.access.session_identity(session, token)
            row = session.get(CustomerPhoneAccess, data.access_id)
            if row is None or row.agency_id != actor.agency_id:
                raise unavailable()
            conversation, _ = self._stored_call(session, row, lock=True)
            session.refresh(row, with_for_update=True)
            if (
                row.revoked_at or row.expires_at <= datetime.now(UTC)
                or not hmac.compare_digest(self._code(row), data.code)
            ):
                raise unavailable()
            if row.approved_at:
                if (
                    row.account_id != current_account.id
                    or row.login_session_id != source.id
                    or row.share_memory != data.share_memory
                ):
                    raise unavailable()
                return {
                    "approved": True, "id": str(row.id),
                    "expires_at": row.expires_at.isoformat(),
                }
            if row.code_digest is None or not hmac.compare_digest(
                row.code_digest, self._digest(data.code)
            ):
                raise unavailable()
            if data.share_memory:
                memory_account = self.memory.account(session, actor)
                policy = self.memory.policy(session, memory_account)
                if (
                    not self.settings.customer_memory_enabled or not policy.enabled
                    or conversation.created_at < policy.history_after
                ):
                    raise ApiError(
                        status_code=409,
                        code="PHONE_MEMORY_UNAVAILABLE",
                        message=(
                            "Saved memory is unavailable for this call. Review "
                            "your memory consent or approve appointments only."
                        ),
                    )
                row.memory_revision = policy.revision
            row.account_id, row.login_session_id = current_account.id, source.id
            row.share_memory, row.approved_at = data.share_memory, datetime.now(UTC)
            row.code_digest = None
            row.expires_at = min(row.expires_at, source.expires_at)
            self._audit(session, row, actor, "PHONE_ACCOUNT_ACCESS_APPROVED", correlation_id)
            return {
                "approved": True, "id": str(row.id),
                "expires_at": row.expires_at.isoformat(),
            }

    def _verified_actor(self, session: Session, row: CustomerPhoneAccess) -> ActorContext:
        if (
            not row.approved_at or row.revoked_at
            or row.expires_at <= datetime.now(UTC) or row.login_session_id is None
        ):
            raise unavailable()
        actor, account, _ = self.access.session_identity(
            session, login_session_id=row.login_session_id
        )
        if account.id != row.account_id or actor.agency_id != row.agency_id:
            raise unavailable()
        return actor

    def _authorized(
        self, session: Session, context: PhoneAccessContext
    ) -> tuple[CustomerPhoneAccess, ActorContext]:
        conversation, _ = self._active_call(session, context, lock=True)
        row = session.scalar(
            select(CustomerPhoneAccess).where(
                CustomerPhoneAccess.conversation_session_id == conversation.id,
                CustomerPhoneAccess.agency_id == conversation.agency_id,
            ).with_for_update()
        )
        if row is None:
            raise unavailable()
        return row, self._verified_actor(session, row)

    def status(self, context: PhoneAccessContext) -> dict[str, object]:
        self.enabled()
        with self.sessions() as session, session.begin():
            row, _ = self._authorized(session, context)
            return {
                "identity_verified": True,
                "expires_at": row.expires_at.isoformat(),
                "appointments_readable": True,
                "memory_approved": row.share_memory,
            }

    def appointments(self, context: PhoneAccessContext) -> dict[str, object]:
        self.enabled()
        with self.sessions() as session, session.begin():
            _, actor = self._authorized(session, context)
            rows = session.execute(
                select(Appointment, HvacServiceRequest).select_from(Appointment)
                .join(
                    HvacServiceRequest,
                    HvacServiceRequest.id == Appointment.service_request_id,
                )
                .join(
                    ConversationSession,
                    ConversationSession.id == HvacServiceRequest.conversation_session_id,
                )
                .where(
                    Appointment.agency_id == actor.agency_id,
                    HvacServiceRequest.agency_id == actor.agency_id,
                    ConversationSession.agency_id == actor.agency_id,
                    ConversationSession.initiated_by == actor.app_user_id,
                    Appointment.status == "CONFIRMED",
                    Appointment.ends_at > datetime.now(UTC),
                )
                .order_by(Appointment.starts_at, Appointment.id).limit(6)
            ).all()
            schedule = session.get(BusinessSchedule, actor.agency_id)
            return {
                "identity_verified": True,
                "timezone": (
                    schedule.configuration.get("timezone", "UTC") if schedule else "UTC"
                ),
                "more_available": len(rows) > 5,
                "appointments": [
                    {
                        "id": str(appointment.id), "status": appointment.status,
                        "starts_at": appointment.starts_at.isoformat(),
                        "ends_at": appointment.ends_at.isoformat(),
                        "service_kind": request.service_details.get("kind"),
                    }
                    for appointment, request in rows[:5]
                ],
            }

    def memory_context(self, context: PhoneAccessContext) -> dict[str, object]:
        self.enabled()
        with self.sessions() as session, session.begin():
            row, actor = self._authorized(session, context)
            account = self.memory.account(session, actor)
            policy = self.memory.policy(session, account)
            if (
                not row.share_memory or not self.settings.customer_memory_enabled
                or not policy.enabled or policy.revision != row.memory_revision
            ):
                raise ApiError(
                    status_code=403,
                    code="PHONE_MEMORY_NOT_APPROVED",
                    message=(
                        "Saved memory has not been approved for this call, "
                        "or consent has changed."
                    ),
                )
            view = self.memory.view(actor, context_only=True, authorized_session=session)
            return {
                "identity_verified": True,
                "summary": view["summary"], "revision": view["revision"],
            }

    def list_access(self, token: str | None) -> dict[str, object]:
        self.enabled()
        with self.sessions() as session, session.begin():
            actor, account, _ = self.access.session_identity(session, token)
            rows = session.scalars(
                select(CustomerPhoneAccess).where(
                    CustomerPhoneAccess.agency_id == actor.agency_id,
                    CustomerPhoneAccess.account_id == account.id,
                ).order_by(CustomerPhoneAccess.created_at.desc()).limit(20)
            ).all()
            items: list[dict[str, object]] = []
            for row in rows:
                conversation = session.get(
                    ConversationSession, row.conversation_session_id
                )
                call = (
                    session.get(InboundCall, conversation.inbound_call_id)
                    if conversation and conversation.inbound_call_id else None
                )
                if conversation is None or call is None:
                    continue
                status = "REVOKED" if row.revoked_at else "EXPIRED"
                if row.revoked_at is None:
                    try:
                        self._stored_call(session, row)
                        self._verified_actor(session, row)
                        status = "ACTIVE"
                    except ApiError:
                        pass
                items.append({
                    **self._view(session, row, actor, call, conversation),
                    "status": status,
                })
            return {"items": items}

    def revoke(self, token: str | None, access_id: UUID, correlation_id: UUID) -> None:
        self.enabled()
        with self.sessions() as session, session.begin():
            actor, account, _ = self.access.session_identity(session, token)
            row = session.get(CustomerPhoneAccess, access_id)
            if (
                row is None or row.agency_id != actor.agency_id
                or row.account_id != account.id
            ):
                raise ApiError(
                    status_code=404, code="PHONE_ACCESS_NOT_FOUND",
                    message="That call approval could not be found.",
                )
            session.scalar(
                select(ConversationSession.id).where(
                    ConversationSession.id == row.conversation_session_id
                ).with_for_update()
            )
            session.refresh(row, with_for_update=True)
            if row.revoked_at is None:
                row.revoked_at = datetime.now(UTC)
                self._audit(session, row, actor, "PHONE_ACCOUNT_ACCESS_REVOKED", correlation_id)
