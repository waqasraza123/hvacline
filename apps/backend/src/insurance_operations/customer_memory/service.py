import hashlib
import json
import re
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import delete, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.sql.elements import ColumnElement

from insurance_operations.actors import ActorContext
from insurance_operations.conversations.schemas import ConversationTurn
from insurance_operations.conversations.spoken import normalized_speech
from insurance_operations.customer_memory.schemas import (
    FACT_OPTIONS, MemoryFactInput, MemoryFactSaveInput, MemoryMutation, fact_label,
)
from insurance_operations.database.models.conversation import (
    ConversationIntake, ConversationSession,
)
from insurance_operations.database.models.customer_account import CustomerAccount
from insurance_operations.database.models.customer_mfa import CustomerMfaFactor
from insurance_operations.database.models.customer_memory import (
    CustomerMemoryFact, CustomerMemoryPairing, CustomerMemoryPolicy,
    CustomerMemorySummary, CustomerWhatsAppIdentity,
)
from insurance_operations.database.models.hvac import Appointment, HvacServiceRequest
from insurance_operations.database.models.identity import Agency, AppUser
from insurance_operations.database.models.operations import AuditEvent
from insurance_operations.database.models.whatsapp import WhatsAppConversation
from insurance_operations.errors import ApiError
from insurance_operations.settings import ApiSettings


def memory_error(message: str, code: str = "MEMORY_NOT_AVAILABLE") -> ApiError:
    return ApiError(status_code=409, code=code, message=message)


def supported_facts(intake: ConversationIntake) -> list[MemoryFactInput]:
    user_text = " ".join(
        normalized_speech(str(turn.get("text", "")))
        for turn in intake.confirmed_transcript if turn.get("speaker") == "USER"
    )
    matches: list[MemoryFactInput] = []
    for key, choices in FACT_OPTIONS.items():
        values = [
            value for value, label in choices.items()
            if f" {normalized_speech(label)} " in f" {user_text} "
        ]
        if len(values) == 1:
            matches.append(MemoryFactInput(key=key, value=values[0]))
    return matches


def redact_pairing_codes(
    turns: list[ConversationTurn],
) -> list[ConversationTurn]:
    pattern = r"HVACMEM-[A-Za-z0-9_-]{32}"
    return [turn.model_copy(update={
        "text": re.sub(pattern, "[account linking code omitted]", turn.text)
    })
            for turn in turns]


class CustomerMemoryService:
    def __init__(self, sessions: sessionmaker[Session], settings: ApiSettings) -> None:
        self.sessions = sessions
        self.settings = settings

    def enabled(self) -> None:
        if not self.settings.customer_memory_enabled:
            raise ApiError(status_code=404, code="NOT_FOUND", message="Memory is disabled")

    @staticmethod
    def account(session: Session, actor: ActorContext) -> CustomerAccount:
        row = session.scalar(select(CustomerAccount).join(
            AppUser, AppUser.id == CustomerAccount.app_user_id
        ).join(Agency, Agency.id == CustomerAccount.agency_id).where(
            CustomerAccount.agency_id == actor.agency_id,
            CustomerAccount.app_user_id == actor.app_user_id,
            AppUser.status == "ACTIVE", AppUser.disabled_at.is_(None),
            Agency.archived_at.is_(None),
        ))
        if row is None:
            raise ApiError(status_code=404, code="NOT_FOUND", message="Memory not found")
        return row

    def policy(self, session: Session, account: CustomerAccount) -> CustomerMemoryPolicy:
        now = datetime.now(UTC)
        session.execute(insert(CustomerMemoryPolicy).values(
            account_id=account.id, agency_id=account.agency_id, enabled=False,
            revision=0, history_after=account.created_at, updated_at=now,
            retention_days=self.settings.customer_memory_retention_days,
        ).on_conflict_do_nothing(index_elements=["account_id"]))
        row = session.scalar(select(CustomerMemoryPolicy).where(
            CustomerMemoryPolicy.account_id == account.id,
            CustomerMemoryPolicy.agency_id == account.agency_id,
        ).with_for_update())
        if row is None:
            raise memory_error("Memory ownership could not be verified")
        if row.retention_days > self.settings.customer_memory_retention_days:
            row.retention_days = self.settings.customer_memory_retention_days
            row.updated_at = now
        return row

    @staticmethod
    def owned_intakes(account: CustomerAccount) -> ColumnElement[bool]:
        return or_(
            (ConversationSession.channel == "BROWSER")
            & (ConversationSession.initiated_by == account.app_user_id),
            (WhatsAppConversation.agency_id == account.agency_id)
            & (ConversationSession.channel == "WHATSAPP")
            & (WhatsAppConversation.customer_account_id == account.id),
        )

    def source(
        self, session: Session, account: CustomerAccount, intake_id: UUID,
    ) -> ConversationIntake:
        row = session.scalar(select(ConversationIntake).join(
            ConversationSession,
            ConversationSession.id == ConversationIntake.conversation_session_id,
        ).outerjoin(
            WhatsAppConversation,
            WhatsAppConversation.session_id == ConversationSession.id,
        ).where(
            ConversationIntake.id == intake_id,
            ConversationIntake.agency_id == account.agency_id,
            ConversationSession.agency_id == account.agency_id,
            self.owned_intakes(account),
        ))
        if row is None:
            raise ApiError(status_code=404, code="NOT_FOUND", message="Source not found")
        return row

    def active_session(
        self, session: Session, account: CustomerAccount, session_id: UUID,
        *, whatsapp: bool = False,
    ) -> ConversationSession:
        row = session.get(ConversationSession, session_id)
        now = datetime.now(UTC)
        if (
            row is None or row.agency_id != account.agency_id
            or row.status not in {"AUTHORIZED", "CONFIRMED"}
            or row.ended_at is not None or row.authorization_expires_at <= now
            or (not whatsapp and (
                row.channel != "BROWSER" or row.initiated_by != account.app_user_id
            ))
            or (whatsapp and row.channel != "WHATSAPP")
        ):
            raise memory_error("An active owned conversation is required")
        return row

    @staticmethod
    def begin_mutation(
        policy: CustomerMemoryPolicy, data: MemoryMutation, operation: str,
    ) -> bool:
        content = data.model_dump(mode="json", exclude={"request_id", "expected_revision"})
        digest = hashlib.sha256(json.dumps(
            [operation, content], sort_keys=True, separators=(",", ":")
        ).encode()).hexdigest()
        if policy.last_request_id == data.request_id:
            if policy.last_fingerprint != digest:
                raise memory_error("This request ID has different details")
            return False
        if policy.revision != data.expected_revision:
            raise memory_error("Memory changed. Refresh and review your choices", "MEMORY_CONFLICT")
        policy.revision += 1
        policy.updated_at = datetime.now(UTC)
        policy.last_request_id = data.request_id
        policy.last_fingerprint = digest
        return True

    @staticmethod
    def audit(
        session: Session, account: CustomerAccount, event: str, correlation_id: UUID,
        details: dict[str, object] | None = None,
    ) -> None:
        session.add(AuditEvent(
            agency_id=account.agency_id, actor_type="DEMO_USER",
            actor_user_id=account.app_user_id, event_type=event,
            occurred_at=datetime.now(UTC), summary="Customer memory preference updated",
            details=details or {}, correlation_id=correlation_id, event_version=1,
        ))

    def clear_optional(self, session: Session, account: CustomerAccount) -> None:
        for model in (CustomerMemoryFact, CustomerMemorySummary, CustomerWhatsAppIdentity):
            session.execute(delete(model).where(
                model.account_id == account.id, model.agency_id == account.agency_id
            ))

    def set_consent(
        self, actor: ActorContext, data: MemoryMutation, enabled: bool | None,
        correlation_id: UUID,
    ) -> None:
        if enabled is True:
            self.enabled()
        with self.sessions() as session, session.begin():
            account = self.account(session, actor)
            policy = self.policy(session, account)
            operation = f"consent:{enabled}" if enabled is not None else "erase"
            if not self.begin_mutation(policy, data, operation):
                return
            now = datetime.now(UTC)
            if enabled is None or enabled != policy.enabled:
                self.clear_optional(session, account)
            if enabled is None or enabled is False:
                policy.history_after = now
            if enabled is None or (enabled is True and not policy.enabled):
                policy.retention_days = self.settings.customer_memory_retention_days
            if enabled is not None:
                policy.enabled = enabled
            self.audit(session, account, "CUSTOMER_MEMORY_ERASED" if enabled is None
                       else "CUSTOMER_MEMORY_CONSENT_CHANGED", correlation_id,
                       {"enabled": policy.enabled, "revision": policy.revision,
                        "consent_scope": "CONFIRMED_HISTORY_AND_SELECTED_FACTS"})

    def save(
        self, actor: ActorContext, data: MemoryFactSaveInput, correlation_id: UUID,
        *, session_id: UUID | None = None, whatsapp: bool = False,
        whatsapp_binding_id: UUID | None = None,
    ) -> None:
        self.enabled()
        with self.sessions() as session, session.begin():
            account = self.account(session, actor)
            policy = self.policy(session, account)
            if not policy.enabled:
                raise memory_error("Enable optional memory before saving facts")
            if whatsapp:
                if whatsapp_binding_id is None:
                    raise memory_error("A verified WhatsApp link is required")
                self.require_whatsapp_link(
                    session, account, whatsapp_binding_id, session_id=session_id
                )
            if session_id is not None:
                conversation = self.active_session(
                    session, account, session_id, whatsapp=whatsapp
                )
                if policy.enabled and conversation.created_at < policy.history_after:
                    raise memory_error("Start a new conversation after changing consent")
            if not self.begin_mutation(policy, data, "save"):
                return
            if data.source_intake_id is not None:
                source = self.source(session, account, data.source_intake_id)
                allowed = {(fact.key, fact.value) for fact in supported_facts(source)}
                if session_id is not None and source.conversation_session_id != session_id:
                    raise memory_error("The source must belong to this conversation")
                if source.confirmed_at < policy.history_after:
                    raise memory_error("This source predates your current memory consent")
                if any((fact.key, fact.value) not in allowed for fact in data.facts):
                    raise memory_error("Only facts supported by the customer's words may be saved")
            elif session_id is not None:
                raise memory_error("Confirm the conversation intake before saving memory")
            now = datetime.now(UTC)
            for fact in data.facts:
                row = session.scalar(select(CustomerMemoryFact).where(
                    CustomerMemoryFact.account_id == account.id,
                    CustomerMemoryFact.agency_id == account.agency_id,
                    CustomerMemoryFact.key == fact.key,
                ).with_for_update())
                if row is None:
                    row = CustomerMemoryFact(
                        account_id=account.id, agency_id=account.agency_id,
                        key=fact.key, created_at=now,
                    )
                    session.add(row)
                row.value = fact.value
                row.source_intake_id = data.source_intake_id
                row.source_kind = "CONVERSATION" if data.source_intake_id else "CUSTOMER_CONTROL"
                row.updated_at = now
                row.expires_at = now + timedelta(days=policy.retention_days)
            self.audit(session, account, "CUSTOMER_MEMORY_SAVED", correlation_id,
                       {"fields": [fact.key for fact in data.facts],
                        "revision": policy.revision})

    def remove_fact(
        self, actor: ActorContext, key: str, data: MemoryMutation, correlation_id: UUID,
    ) -> None:
        with self.sessions() as session, session.begin():
            account = self.account(session, actor)
            policy = self.policy(session, account)
            if not self.begin_mutation(policy, data, f"remove:{key}"):
                return
            session.execute(delete(CustomerMemoryFact).where(
                CustomerMemoryFact.account_id == account.id,
                CustomerMemoryFact.agency_id == account.agency_id,
                CustomerMemoryFact.key == key,
            ))
            self.audit(session, account, "CUSTOMER_MEMORY_FACT_REMOVED", correlation_id)

    def sync_summaries(
        self, session: Session, account: CustomerAccount, policy: CustomerMemoryPolicy,
    ) -> None:
        now = datetime.now(UTC)
        cutoff = max(policy.history_after, now - timedelta(
            days=policy.retention_days
        ))
        intakes = session.scalars(select(ConversationIntake).join(
            ConversationSession,
            ConversationSession.id == ConversationIntake.conversation_session_id,
        ).outerjoin(
            WhatsAppConversation, WhatsAppConversation.session_id == ConversationSession.id,
        ).where(
            ConversationIntake.agency_id == account.agency_id,
            ConversationSession.agency_id == account.agency_id,
            ConversationIntake.confirmed_at >= cutoff, self.owned_intakes(account),
        ).order_by(ConversationIntake.confirmed_at.desc()).limit(10)).all()
        for intake in intakes:
            if session.get(CustomerMemorySummary, intake.id) is not None:
                continue
            summary = f"Authorized conversation with {len(intake.confirmed_transcript)} turns."
            request = session.scalar(select(HvacServiceRequest).where(
                HvacServiceRequest.agency_id == account.agency_id,
                HvacServiceRequest.conversation_session_id == intake.conversation_session_id,
            ))
            if request is not None:
                kind = request.service_details.get("kind")
                if kind in {"AC_REPAIR", "HEATING_REPAIR", "INSTALLATION", "MAINTENANCE"}:
                    summary += f" Confirmed {str(kind).replace('_', ' ').lower()} request."
            session.add(CustomerMemorySummary(
                intake_id=intake.id, account_id=account.id, agency_id=account.agency_id,
                summary=summary, created_at=intake.confirmed_at,
                expires_at=intake.confirmed_at + timedelta(
                    days=policy.retention_days
                ),
            ))
        session.flush()

    def view(
        self, actor: ActorContext, *, context_only: bool = False,
        whatsapp_binding_id: UUID | None = None,
        browser_session_id: UUID | None = None,
    ) -> dict[str, object]:
        if context_only:
            self.enabled()
        with self.sessions() as session, session.begin():
            account = self.account(session, actor)
            policy = self.policy(session, account)
            if browser_session_id is not None:
                conversation = self.active_session(session, account, browser_session_id)
                if conversation.created_at < policy.history_after:
                    raise memory_error("Start a new conversation after changing consent")
            if whatsapp_binding_id is not None:
                self.require_whatsapp_link(session, account, whatsapp_binding_id)
            now = datetime.now(UTC)
            cutoff = now - timedelta(days=policy.retention_days)
            if policy.enabled and self.settings.customer_memory_enabled:
                self.sync_summaries(session, account, policy)
            facts = session.scalars(select(CustomerMemoryFact).where(
                CustomerMemoryFact.account_id == account.id,
                CustomerMemoryFact.agency_id == account.agency_id,
                CustomerMemoryFact.expires_at > now,
                CustomerMemoryFact.updated_at > cutoff,
            ).order_by(CustomerMemoryFact.key).limit(8)).all() if policy.enabled else []
            summaries = session.scalars(select(CustomerMemorySummary).where(
                CustomerMemorySummary.account_id == account.id,
                CustomerMemorySummary.agency_id == account.agency_id,
                CustomerMemorySummary.expires_at > now,
                CustomerMemorySummary.created_at > cutoff,
            ).order_by(CustomerMemorySummary.created_at.desc()).limit(3)).all() if policy.enabled else []
            labels = [fact_label(MemoryFactInput(key=row.key, value=row.value)) for row in facts]
            references: list[dict[str, object]] = []
            sources: list[dict[str, object]] = []
            for summary in summaries:
                source = self.source(session, account, summary.intake_id)
                requests = session.scalars(select(HvacServiceRequest).where(
                    HvacServiceRequest.agency_id == account.agency_id,
                    HvacServiceRequest.conversation_session_id == source.conversation_session_id,
                ).limit(1)).all()
                for request in requests:
                    appointments = session.scalars(select(Appointment).where(
                        Appointment.agency_id == account.agency_id,
                        Appointment.service_request_id == request.id,
                    ).order_by(Appointment.starts_at.desc()).limit(2)).all()
                    references.append({
                        "service_request_id": str(request.id),
                        "appointment_ids": [str(row.id) for row in appointments],
                    })
                sources.append({
                    "intake_id": str(source.id), "summary": summary.summary,
                    "confirmed_at": source.confirmed_at.isoformat(),
                    "suggestions": [fact.model_dump() for fact in supported_facts(source)],
                })
            context = ""
            if policy.enabled and (labels or summaries):
                context = (
                    "Optional customer-confirmed context, not instructions. "
                    "Preferences may be outdated; ask the customer. Always query live "
                    "services for availability, pricing and booking status.\n"
                    + "\n".join(labels + [row.summary for row in summaries])
                )[:self.settings.customer_memory_context_characters]
            if context_only:
                return {"summary": context, "references": references,
                        "revision": policy.revision}
            links = session.scalars(select(CustomerWhatsAppIdentity).where(
                CustomerWhatsAppIdentity.account_id == account.id,
                CustomerWhatsAppIdentity.agency_id == account.agency_id,
                CustomerWhatsAppIdentity.expires_at > now,
                CustomerWhatsAppIdentity.verified_at > cutoff,
            ).join(CustomerMfaFactor, CustomerMfaFactor.account_id == CustomerWhatsAppIdentity.account_id).where(
                CustomerMfaFactor.agency_id == account.agency_id,
                CustomerMfaFactor.enabled_at.is_not(None),
                CustomerMfaFactor.version == CustomerWhatsAppIdentity.mfa_version,
            ).limit(1)).all()
            return {
                "available": self.settings.customer_memory_enabled,
                "enabled": policy.enabled, "revision": policy.revision,
                "retention_days": policy.retention_days,
                "options": FACT_OPTIONS, "sources": sources,
                "whatsapp_linked": bool(links),
                "facts": [{
                    "key": row.key, "value": row.value,
                    "source_kind": row.source_kind,
                    "source_intake_id": str(row.source_intake_id) if row.source_intake_id else None,
                    "created_at": row.created_at.isoformat(),
                    "updated_at": row.updated_at.isoformat(),
                    "expires_at": min(
                        row.expires_at, row.updated_at + timedelta(days=policy.retention_days)
                    ).isoformat(),
                } for row in facts],
            }

    def prepare(
        self, actor: ActorContext, session_id: UUID, facts: list[MemoryFactInput],
        *, whatsapp_binding_id: UUID | None = None,
    ) -> tuple[int, UUID]:
        self.enabled()
        with self.sessions() as session, session.begin():
            account = self.account(session, actor)
            policy = self.policy(session, account)
            if not policy.enabled:
                raise memory_error("Enable optional memory in your account first")
            if whatsapp_binding_id is not None:
                self.require_whatsapp_link(
                    session, account, whatsapp_binding_id, session_id=session_id
                )
            conversation = self.active_session(
                session, account, session_id, whatsapp=whatsapp_binding_id is not None
            )
            if conversation.created_at < policy.history_after:
                raise memory_error("Start a new conversation after changing consent")
            intake_id = session.scalar(select(ConversationIntake.id).where(
                ConversationIntake.agency_id == account.agency_id,
                ConversationIntake.conversation_session_id == session_id,
            ))
            if intake_id is None:
                raise memory_error("Confirm your intake before saving conversation memory")
            intake = self.source(session, account, intake_id)
            supported = {(fact.key, fact.value) for fact in supported_facts(intake)}
            if any((fact.key, fact.value) not in supported for fact in facts):
                raise memory_error("These details need customer evidence; use Memory settings to enter a correction")
            return policy.revision, intake.id

    def require_whatsapp_link(
        self, session: Session, account: CustomerAccount, binding_id: UUID,
        *, session_id: UUID | None = None,
    ) -> None:
        binding = session.get(WhatsAppConversation, binding_id)
        now = datetime.now(UTC)
        if (
            binding is None or binding.agency_id != account.agency_id
            or binding.customer_account_id != account.id or binding.session_id is None
            or (session_id is not None and binding.session_id != session_id)
            or binding.finalized_at is not None or binding.expires_at <= now
        ):
            raise memory_error("A verified active WhatsApp identity is required")
        policy = session.get(CustomerMemoryPolicy, account.id)
        if policy is None or not policy.enabled:
            raise memory_error("Enable optional memory before using a linked caller")
        identity = session.scalar(select(CustomerWhatsAppIdentity.id).where(
            CustomerWhatsAppIdentity.agency_id == account.agency_id,
            CustomerWhatsAppIdentity.account_id == account.id,
            CustomerWhatsAppIdentity.phone_number_id == binding.phone_number_id,
            CustomerWhatsAppIdentity.caller_digest == binding.caller_digest,
            CustomerWhatsAppIdentity.expires_at > now,
            CustomerWhatsAppIdentity.verified_at > now - timedelta(
                days=policy.retention_days
            ),
        ).join(CustomerMfaFactor, CustomerMfaFactor.account_id == CustomerWhatsAppIdentity.account_id).where(
            CustomerMfaFactor.enabled_at.is_not(None),
            CustomerMfaFactor.agency_id == account.agency_id,
            CustomerMfaFactor.version == CustomerWhatsAppIdentity.mfa_version,
        ))
        if identity is None:
            raise memory_error("The WhatsApp account link has expired or was removed")
        conversation = self.active_session(session, account, binding.session_id, whatsapp=True)
        if conversation.created_at < policy.history_after:
            raise memory_error("Start a new call after changing memory consent")

    def begin_pairing(self, binding_id: UUID) -> str:
        self.enabled()
        code = "HVACMEM-" + secrets.token_urlsafe(24)
        with self.sessions() as session, session.begin():
            binding = session.get(WhatsAppConversation, binding_id, with_for_update=True)
            now = datetime.now(UTC)
            if binding is None or binding.finalized_at or binding.expires_at <= now:
                raise memory_error("An active WhatsApp call is required")
            row = session.scalar(select(CustomerMemoryPairing).where(
                CustomerMemoryPairing.binding_id == binding_id
            ).with_for_update())
            if row is not None and row.consumed_at is not None:
                raise memory_error("This call has already completed account linking")
            if row is None:
                row = CustomerMemoryPairing(
                    agency_id=binding.agency_id, binding_id=binding_id,
                )
                session.add(row)
            row.code_digest = hashlib.sha256(code.encode()).hexdigest()
            row.expires_at = min(binding.expires_at, now + timedelta(minutes=5))
        return code

    def approve_pairing(
        self, actor: ActorContext, data: MemoryMutation, code: str, correlation_id: UUID,
    ) -> None:
        self.enabled()
        with self.sessions() as session, session.begin():
            account = self.account(session, actor)
            session.scalar(select(Agency.id).where(
                Agency.id == account.agency_id
            ).with_for_update())
            policy = self.policy(session, account)
            if not policy.enabled:
                raise memory_error("Enable memory before linking WhatsApp")
            mfa = session.get(CustomerMfaFactor, account.id)
            if mfa is None or mfa.enabled_at is None or mfa.agency_id != account.agency_id:
                raise memory_error("Complete authenticator setup before linking WhatsApp")
            if not self.begin_mutation(policy, data, "approve-whatsapp"):
                return
            pairing = session.scalar(select(CustomerMemoryPairing).where(
                CustomerMemoryPairing.agency_id == account.agency_id,
                CustomerMemoryPairing.code_digest == hashlib.sha256(code.encode()).hexdigest(),
            ))
            now = datetime.now(UTC)
            if pairing is None or pairing.consumed_at or pairing.expires_at <= now:
                raise memory_error("The linking code is invalid or expired")
            binding = session.get(WhatsAppConversation, pairing.binding_id, with_for_update=True)
            pairing = session.scalar(select(CustomerMemoryPairing).where(
                CustomerMemoryPairing.id == pairing.id,
                CustomerMemoryPairing.code_digest == hashlib.sha256(code.encode()).hexdigest(),
            ).with_for_update().execution_options(populate_existing=True))
            if pairing is None or pairing.consumed_at or pairing.expires_at <= now:
                raise memory_error("The linking code changed or expired; request a new one")
            if (
                binding is None or binding.agency_id != account.agency_id
                or binding.expires_at <= now or binding.finalized_at
                or binding.session_id is None
                or binding.customer_account_id not in {None, account.id}
            ):
                raise memory_error("The linking call is no longer available")
            existing = session.scalar(select(CustomerWhatsAppIdentity).where(
                CustomerWhatsAppIdentity.agency_id == account.agency_id,
                CustomerWhatsAppIdentity.phone_number_id == binding.phone_number_id,
                CustomerWhatsAppIdentity.caller_digest == binding.caller_digest,
            ).with_for_update())
            if existing is not None and existing.account_id != account.id:
                raise memory_error("This WhatsApp identity is already linked")
            if existing is None:
                existing = CustomerWhatsAppIdentity(
                    account_id=account.id, agency_id=account.agency_id,
                    phone_number_id=binding.phone_number_id,
                    caller_digest=binding.caller_digest,
                )
                session.add(existing)
            existing.verified_at = now
            existing.mfa_version = mfa.version
            existing.expires_at = now + timedelta(days=policy.retention_days)
            binding.customer_account_id = account.id
            self.active_session(session, account, binding.session_id, whatsapp=True)
            pairing.consumed_at = now
            self.audit(session, account, "CUSTOMER_WHATSAPP_IDENTITY_LINKED", correlation_id)

    def unlink(self, actor: ActorContext, data: MemoryMutation, correlation_id: UUID) -> None:
        with self.sessions() as session, session.begin():
            account = self.account(session, actor)
            policy = self.policy(session, account)
            if not self.begin_mutation(policy, data, "unlink-whatsapp"):
                return
            session.execute(delete(CustomerWhatsAppIdentity).where(
                CustomerWhatsAppIdentity.account_id == account.id,
                CustomerWhatsAppIdentity.agency_id == account.agency_id,
            ))
            self.audit(session, account, "CUSTOMER_WHATSAPP_IDENTITY_UNLINKED", correlation_id)

    def whatsapp_actor(self, binding_id: UUID) -> ActorContext | None:
        self.enabled()
        with self.sessions() as session, session.begin():
            binding = session.get(WhatsAppConversation, binding_id)
            now = datetime.now(UTC)
            if binding is None or binding.finalized_at or binding.expires_at <= now:
                return None
            identity = session.scalar(select(CustomerWhatsAppIdentity).where(
                CustomerWhatsAppIdentity.agency_id == binding.agency_id,
                CustomerWhatsAppIdentity.phone_number_id == binding.phone_number_id,
                CustomerWhatsAppIdentity.caller_digest == binding.caller_digest,
                CustomerWhatsAppIdentity.expires_at > now,
            ).join(CustomerMfaFactor, CustomerMfaFactor.account_id == CustomerWhatsAppIdentity.account_id).where(
                CustomerMfaFactor.agency_id == binding.agency_id,
                CustomerMfaFactor.enabled_at.is_not(None),
                CustomerMfaFactor.version == CustomerWhatsAppIdentity.mfa_version,
            ))
            if identity is None:
                return None
            account = session.get(CustomerAccount, identity.account_id)
            if account is None or account.agency_id != binding.agency_id:
                return None
            user = session.get(AppUser, account.app_user_id)
            agency = session.get(Agency, account.agency_id)
            if (
                user is None or user.status != "ACTIVE" or user.disabled_at
                or agency is None or agency.archived_at
            ):
                return None
            policy = self.policy(session, account)
            if not policy.enabled:
                return None
            identity = session.scalar(select(CustomerWhatsAppIdentity).where(
                CustomerWhatsAppIdentity.id == identity.id,
                CustomerWhatsAppIdentity.account_id == account.id,
                CustomerWhatsAppIdentity.expires_at > now,
                CustomerWhatsAppIdentity.verified_at > now - timedelta(
                    days=policy.retention_days
                ),
            ).join(CustomerMfaFactor, CustomerMfaFactor.account_id == CustomerWhatsAppIdentity.account_id).where(
                CustomerMfaFactor.enabled_at.is_not(None),
                CustomerMfaFactor.agency_id == account.agency_id,
                CustomerMfaFactor.version == CustomerWhatsAppIdentity.mfa_version,
            ).with_for_update(of=CustomerWhatsAppIdentity))
            if identity is None:
                return None
            binding = session.get(WhatsAppConversation, binding_id, with_for_update=True,
                                  populate_existing=True)
            if binding is None or binding.customer_account_id not in {None, account.id}:
                return None
            if binding.session_id is None:
                return None
            conversation = self.active_session(session, account, binding.session_id, whatsapp=True)
            if conversation.created_at < policy.history_after:
                return None
            binding.customer_account_id = account.id
            return ActorContext(
                app_user_id=account.app_user_id, agency_id=account.agency_id,
                display_name=user.display_name, agency_name=agency.name,
                agency_environment=agency.environment_kind,
            )
