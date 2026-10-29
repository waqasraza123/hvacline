from datetime import UTC, datetime, time, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.actors import (
    ActorContext,
    ActorResolutionError,
    resolve_development_actor,
)
from insurance_operations.conversations.service import ConversationService
from insurance_operations.database.models.conversation import (
    ConversationChannel,
    ConversationSession,
    ConversationSessionStatus,
)
from insurance_operations.database.models.operations import AuditEvent
from insurance_operations.database.models.whatsapp import WhatsAppConversation
from insurance_operations.errors import ApiError
from insurance_operations.settings import ApiSettings
from insurance_operations.whatsapp.provider import (
    ElevenLabsWhatsAppAdapter,
    WhatsAppInitiation,
    WhatsAppPostCall,
    rejected,
)
from insurance_operations.whatsapp.settings import WhatsAppSettings


class WhatsAppService:
    def __init__(
        self,
        sessions: sessionmaker[Session],
        settings: ApiSettings,
        whatsapp: WhatsAppSettings,
        adapter: ElevenLabsWhatsAppAdapter,
    ) -> None:
        self.sessions = sessions
        self.settings = settings
        self.whatsapp = whatsapp
        self.adapter = adapter
        self.conversations = ConversationService(
            session_factory=sessions, settings=settings, provider=adapter
        )

    def actor(self, session: Session) -> ActorContext:
        user_id = self.whatsapp.whatsapp_actor_user_id
        if user_id is None:
            raise rejected()
        try:
            actor = resolve_development_actor(session, user_id)
        except ActorResolutionError as error:
            raise rejected() from error
        if actor.agency_id != self.whatsapp.whatsapp_agency_id:
            raise rejected()
        return actor

    def initialize(
        self, data: WhatsAppInitiation, correlation_id: UUID
    ) -> dict[str, object]:
        now = datetime.now(UTC)
        with self.sessions() as session, session.begin():
            actor = self.actor(session)
            ConversationService._lock_agency(session, actor.agency_id)
            row = session.scalar(
                select(WhatsAppConversation)
                .where(WhatsAppConversation.conversation_id == data.conversation_id)
                .with_for_update()
            )
            digest = self.adapter.caller_digest(data.caller_id)
            if row is not None:
                if (
                    row.agency_id != actor.agency_id
                    or row.phone_number_id != data.called_number
                    or row.caller_digest != digest
                ):
                    raise rejected()
                self.require_active_binding(row, now)
            else:
                ConversationService._expire_stale_sessions(
                    session, actor.agency_id, now
                )
                ConversationService._enforce_concurrency_limit(session, actor, now)
                pending = session.scalar(
                    select(WhatsAppConversation.id)
                    .where(
                        WhatsAppConversation.agency_id == actor.agency_id,
                        WhatsAppConversation.expires_at > now,
                        WhatsAppConversation.finalized_at.is_(None),
                    )
                    .limit(1)
                )
                if pending is not None:
                    raise ApiError(
                        status_code=409,
                        code="CONVERSATION_ALREADY_ACTIVE",
                        message="Another conversation is active",
                    )
                day_start = datetime.combine(now.date(), time.min, tzinfo=UTC)
                whatsapp_count = (
                    session.scalar(
                        select(func.count())
                        .select_from(WhatsAppConversation)
                        .where(
                            WhatsAppConversation.agency_id == actor.agency_id,
                            WhatsAppConversation.initialized_at >= day_start,
                        )
                    )
                    or 0
                )
                other_count = (
                    session.scalar(
                        select(func.count())
                        .select_from(ConversationSession)
                        .where(
                            ConversationSession.agency_id == actor.agency_id,
                            ConversationSession.channel
                            != ConversationChannel.WHATSAPP.value,
                            ConversationSession.authorized_at >= day_start,
                        )
                    )
                    or 0
                )
                if (
                    whatsapp_count + other_count
                    >= self.settings.conversation_daily_session_limit
                ):
                    raise ApiError(
                        status_code=429,
                        code="CONVERSATION_DAILY_LIMIT_REACHED",
                        message="The daily conversation limit has been reached",
                    )
                row = WhatsAppConversation(
                    agency_id=actor.agency_id,
                    conversation_id=data.conversation_id,
                    phone_number_id=data.called_number,
                    caller_digest=digest,
                    initialized_at=now,
                    expires_at=now
                    + timedelta(
                        seconds=self.settings.conversation_max_duration_seconds
                    ),
                )
                session.add(row)
                session.flush()
                self.audit(
                    session, row, "WHATSAPP_CONVERSATION_INITIALIZED", correlation_id
                )
            return {
                "type": "conversation_initiation_client_data",
                "dynamic_variables": {
                    "whatsapp_binding_id": str(row.id),
                    "whatsapp_session_id": str(row.session_id)
                    if row.session_id
                    else "",
                    "secret__whatsapp_session_token": self.adapter.session_token(
                        str(row.id), row.conversation_id
                    ),
                },
            }

    @staticmethod
    def require_active_binding(row: WhatsAppConversation, now: datetime) -> None:
        if row.finalized_at is not None or row.expires_at <= now:
            raise ApiError(
                status_code=409,
                code="WHATSAPP_CALL_ENDED",
                message="The WhatsApp call is no longer active",
            )

    def require_binding(
        self,
        session: Session,
        binding_id: UUID,
        conversation_id: str,
        *,
        lock: bool = False,
    ) -> tuple[WhatsAppConversation, ActorContext]:
        actor = self.actor(session)
        row = session.get(WhatsAppConversation, binding_id, with_for_update=lock)
        if (
            row is None
            or row.agency_id != actor.agency_id
            or row.conversation_id != conversation_id
            or row.phone_number_id != self.adapter.number_id
        ):
            raise rejected()
        self.require_active_binding(row, datetime.now(UTC))
        return row, actor

    def consent(
        self, binding_id: UUID, conversation_id: str, correlation_id: UUID
    ) -> UUID:
        now = datetime.now(UTC)
        with self.sessions() as session, session.begin():
            actor = self.actor(session)
            ConversationService._lock_agency(session, actor.agency_id)
            row, actor = self.require_binding(
                session, binding_id, conversation_id, lock=True
            )
            if row.session_id is not None:
                self.require_session(session, row, actor, row.session_id)
                return row.session_id
            ConversationService._expire_stale_sessions(session, actor.agency_id, now)
            ConversationService._enforce_concurrency_limit(session, actor, now)
            self.conversations._enforce_daily_limit(session, actor.agency_id, now)
            conversation = ConversationSession(
                agency_id=actor.agency_id,
                initiated_by=actor.app_user_id,
                channel=ConversationChannel.WHATSAPP.value,
                input_mode="VOICE",
                status=ConversationSessionStatus.AUTHORIZED.value,
                disclosure_accepted_at=now,
                microphone_consent_at=now,
                maximum_duration_seconds=self.settings.conversation_max_duration_seconds,
                authorization_expires_at=row.expires_at,
                confirmation_expires_at=row.expires_at,
                authorized_at=now,
                provider_metadata={
                    "adapter": "elevenlabs_whatsapp",
                    "adapter_version": "1",
                    "external_session_reference": conversation_id,
                },
            )
            session.add(conversation)
            session.flush()
            row.session_id = conversation.id
            self.audit(session, row, "WHATSAPP_CONSENT_ACCEPTED", correlation_id)
            return conversation.id

    def require_session(
        self,
        session: Session,
        binding: WhatsAppConversation,
        actor: ActorContext,
        session_id: UUID,
    ) -> ConversationSession:
        row = session.get(ConversationSession, session_id)
        if (
            binding.session_id != session_id
            or row is None
            or row.agency_id != actor.agency_id
            or row.initiated_by != actor.app_user_id
            or row.channel != ConversationChannel.WHATSAPP.value
            or row.status
            not in {
                ConversationSessionStatus.AUTHORIZED.value,
                ConversationSessionStatus.CONFIRMED.value,
            }
            or row.ended_at is not None
            or row.authorization_expires_at <= datetime.now(UTC)
        ):
            raise ApiError(
                status_code=409,
                code="WHATSAPP_CONSENT_REQUIRED",
                message="An active consented WhatsApp session is required",
            )
        return row

    def finalize(self, event: WhatsAppPostCall, correlation_id: UUID) -> None:
        with self.sessions() as session, session.begin():
            actor = self.actor(session)
            row = session.scalar(
                select(WhatsAppConversation)
                .where(
                    WhatsAppConversation.agency_id == actor.agency_id,
                    WhatsAppConversation.conversation_id == event.data.conversation_id,
                )
                .with_for_update()
            )
            if row is None:
                raise rejected()
            if row.finalized_at is not None:
                return
            now = datetime.now(UTC)
            row.finalized_at = now
            if row.session_id is not None:
                conversation = session.get(
                    ConversationSession, row.session_id, with_for_update=True
                )
                if conversation is None or conversation.agency_id != actor.agency_id:
                    raise rejected()
                conversation.ended_at = conversation.ended_at or now
                if conversation.status != ConversationSessionStatus.CONFIRMED.value:
                    conversation.status = ConversationSessionStatus.FAILED.value
                    conversation.failure_code = (
                        "WHATSAPP_ENDED_WITHOUT_CONFIRMED_INTAKE"
                    )
            self.audit(session, row, "WHATSAPP_CONVERSATION_ENDED", correlation_id)

    @staticmethod
    def audit(
        session: Session, row: WhatsAppConversation, event: str, correlation_id: UUID
    ) -> None:
        session.add(
            AuditEvent(
                agency_id=row.agency_id,
                actor_type="SYSTEM",
                actor_user_id=None,
                event_type=event,
                occurred_at=datetime.now(UTC),
                summary=event.replace("_", " ").capitalize(),
                details={"whatsapp_binding_id": str(row.id)},
                correlation_id=correlation_id,
                event_version=1,
            )
        )
