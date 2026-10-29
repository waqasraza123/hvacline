import asyncio
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import cast
from unittest.mock import AsyncMock, MagicMock, Mock
from uuid import uuid4

import pytest
from fastapi import WebSocket
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.actors import ActorContext
from insurance_operations.approved_faqs import ApprovedFaqService
from insurance_operations.conversations.local_session import (
    LocalConversationError,
    LocalConversationSessionService,
    LocalDraft,
    LocalExtraction,
    LocalHandshake,
    intake_reply,
    merge_draft,
)
from insurance_operations.conversations.providers.local import credential_digest
from insurance_operations.database.models.conversation import ConversationSession
from insurance_operations.receptionist import ReceptionistSettingsService
from insurance_operations.settings import ApiSettings


@pytest.fixture
def context(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[
    tuple[
        LocalConversationSessionService,
        MagicMock,
        ConversationSession,
        ActorContext,
        LocalHandshake,
    ]
]:
    for name in ApiSettings.model_fields:
        monkeypatch.delenv(name.upper(), raising=False)
    actor = ActorContext(uuid4(), "Test operator", uuid4(), "Test HVAC", "DEVELOPMENT")
    handshake = LocalHandshake(
        session_id=uuid4(), credential="synthetic-grant-at-least-20-characters"
    )
    conversation = ConversationSession(
        id=handshake.session_id,
        agency_id=actor.agency_id,
        initiated_by=actor.app_user_id,
        status="AUTHORIZED",
        channel="BROWSER",
        input_mode="VOICE",
        ended_at=None,
        authorization_expires_at=datetime.now(UTC) + timedelta(seconds=180),
        provider_metadata={
            "adapter": "local_browser_voice",
            "external_session_reference": credential_digest(handshake.credential),
        },
    )
    database = MagicMock(spec=Session)
    database.get.return_value = conversation
    factory = MagicMock()
    factory.return_value.__enter__.return_value = database
    settings = ApiSettings(
        _env_file=None,
        app_environment="development",
        api_host="127.0.0.1",
        api_port=8000,
        database_url="postgresql://synthetic:synthetic@localhost/development",
        conversation_ai_enabled=True,
        conversation_provider="local",
        development_actor_user_id=actor.app_user_id,
    )
    service = LocalConversationSessionService(
        settings=settings,
        session_factory=cast(sessionmaker[Session], factory),
        approved_faq_service=Mock(spec=ApprovedFaqService),
        receptionist_settings_service=Mock(spec=ReceptionistSettingsService),
    )
    try:
        yield service, database, conversation, actor, handshake
    finally:
        service.close()


def test_websocket_grant_is_claimed_once_and_not_persisted_raw(
    context: tuple[
        LocalConversationSessionService,
        MagicMock,
        ConversationSession,
        ActorContext,
        LocalHandshake,
    ],
) -> None:
    service, database, conversation, actor, handshake = context
    service._validate_session(actor, handshake, claim=True)
    database.get.assert_called_once_with(
        ConversationSession, handshake.session_id, with_for_update=True
    )
    assert conversation.provider_metadata["connection_claimed"] is True
    assert handshake.credential not in conversation.provider_metadata.values()
    with pytest.raises(LocalConversationError, match="authorization failed"):
        service._validate_session(actor, handshake, claim=True)
    service._validate_session(actor, handshake)


@pytest.mark.parametrize(
    "mutation",
    ["agency", "actor", "channel", "ended", "expired", "failed", "credential"],
)
def test_socket_revalidates_ownership_and_ended_or_expired_sessions(
    context: tuple[
        LocalConversationSessionService,
        MagicMock,
        ConversationSession,
        ActorContext,
        LocalHandshake,
    ],
    mutation: str,
) -> None:
    service, _database, conversation, actor, handshake = context
    if mutation == "agency":
        conversation.agency_id = uuid4()
    elif mutation == "actor":
        conversation.initiated_by = uuid4()
    elif mutation == "channel":
        conversation.channel = "PHONE"
    elif mutation == "ended":
        conversation.ended_at = datetime.now(UTC)
    elif mutation == "expired":
        conversation.authorization_expires_at = datetime.now(UTC) - timedelta(seconds=1)
    elif mutation == "failed":
        conversation.status = "FAILED"
    elif mutation == "credential":
        handshake.credential = "different-synthetic-credential"
    with pytest.raises(LocalConversationError, match="authorization failed"):
        service._validate_session(actor, handshake)


def test_cross_origin_socket_is_rejected_before_database_work(
    context: tuple[
        LocalConversationSessionService,
        MagicMock,
        ConversationSession,
        ActorContext,
        LocalHandshake,
    ],
) -> None:
    service, database, *_rest = context
    socket = AsyncMock(spec=WebSocket)
    socket.headers = {"origin": "https://untrusted.example.test"}
    asyncio.run(service.serve(socket))
    socket.close.assert_awaited_once_with(code=1008)
    socket.accept.assert_not_awaited()
    database.get.assert_not_called()


def test_hazard_and_handoff_cannot_be_cleared_by_later_extraction() -> None:
    first = merge_draft(
        LocalDraft(), LocalExtraction(action="HANDOFF", hazardous_condition=True)
    )
    later = merge_draft(
        first, LocalExtraction(action="CONTINUE", hazardous_condition=False)
    )
    assert later.hazardous_condition is True
    assert later.handoff_requested is True
    assert "emergency services" in intake_reply(later, "CONTINUE", "Ask staff.")
    assert "confirmed" not in intake_reply(later, "CONTINUE", "Ask staff.")
