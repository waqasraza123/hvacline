from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Event
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import delete, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.database.models.conversation import ConversationSession
from insurance_operations.database.models.homepage_chat import (
    HomepageChatDailyUsage,
    HomepageChatVisitor,
)
from insurance_operations.database.models.identity import (
    Agency,
    AgencyMembership,
    AppUser,
)
from insurance_operations.errors import ApiError
from insurance_operations.homepage_chat.provider import HomepageProviderError
from insurance_operations.homepage_chat.schemas import HomepageChatInput
from insurance_operations.homepage_chat.service import HomepageChatService
from insurance_operations.settings import ApiSettings, DatabaseSettings


class ReplyProvider:
    calls = 0
    failure: bool | None = None
    started: Event | None = None
    release: Event | None = None

    def reply(self, message: str, lookup: Callable[[str], str]) -> str:
        self.calls += 1
        if self.started is not None:
            self.started.set()
        if self.release is not None and not self.release.wait(10):
            raise RuntimeError("Test reply was not released")
        if self.failure is not None:
            raise HomepageProviderError(message_sent=self.failure)
        return "I can help you with an AC repair request."


@pytest.fixture
def homepage(
    migrated_database: Engine, database_settings: DatabaseSettings
) -> Iterator[tuple[HomepageChatService, ReplyProvider]]:
    factory = sessionmaker(migrated_database, expire_on_commit=False)
    with factory() as session, session.begin():
        agency = Agency(
            name="Homepage Test Business",
            slug=f"homepage-{uuid4()}",
            environment_kind="DEVELOPMENT",
        )
        user = AppUser(auth_subject=uuid4(), display_name="Homepage Test Operator")
        session.add_all([agency, user])
        session.flush()
        session.add(AgencyMembership(agency_id=agency.id, app_user_id=user.id))
        agency_id, user_id = agency.id, user.id
    settings = ApiSettings(
        _env_file=None,
        app_environment="development",
        api_host="127.0.0.1",
        api_port=8000,
        database_url=database_settings.runtime_database_url,
        database_ssl_mode=database_settings.database_ssl_mode,
        development_actor_user_id=user_id,
        conversation_ai_enabled=True,
        demo_sandbox_enabled=True,
        demo_admin_token="test-admin-secret-32-characters-long",
        elevenlabs_api_key="test-key",
        elevenlabs_agent_id="test-agent",
        elevenlabs_privacy_confirmed=True,
        customer_portal_enabled=True,
        customer_portal_secret="test-portal-secret-32-characters-long",
        customer_mfa_encryption_key=Fernet.generate_key().decode(),
        homepage_chat_enabled=True,
    )
    provider = ReplyProvider()
    try:
        yield HomepageChatService(factory, settings, provider), provider
    finally:
        with factory() as session, session.begin():
            session.execute(
                delete(HomepageChatVisitor).where(
                    HomepageChatVisitor.agency_id == agency_id
                )
            )
            session.execute(
                delete(HomepageChatDailyUsage).where(
                    HomepageChatDailyUsage.agency_id == agency_id
                )
            )
            session.execute(
                delete(AgencyMembership).where(AgencyMembership.agency_id == agency_id)
            )
            session.execute(delete(AppUser).where(AppUser.id == user_id))
            session.execute(delete(Agency).where(Agency.id == agency_id))


def message() -> HomepageChatInput:
    return HomepageChatInput(
        message="Can you help with AC repair?",
        request_id=uuid4(),
        ai_disclosure_accepted=True,
    )


def test_one_reply_survives_refresh_without_creating_a_customer_conversation(
    homepage: tuple[HomepageChatService, ReplyProvider],
) -> None:
    service, provider = homepage
    token = "a" * 43
    request = message()
    assert service.status(token).remaining == 1
    assert service.reply(token, request).remaining == 0
    assert service.status(token).state == "used"
    for data in [request, message()]:
        with pytest.raises(ApiError) as denied:
            service.reply(token, data)
        assert denied.value.code == "HOMEPAGE_SIGN_IN_REQUIRED"
    assert provider.calls == 1
    with service.sessions() as session:
        assert (
            session.scalar(
                select(func.count())
                .select_from(ConversationSession)
                .where(
                    ConversationSession.agency_id == service._actor(session).agency_id
                )
            )
            == 0
        )
        row = session.scalar(select(HomepageChatVisitor))
        assert row is not None
        assert row.token_hash != token
        assert row.request_hash != request.message


@pytest.mark.parametrize("sent", [False, True])
def test_failed_generation_restores_only_a_known_unused_allowance(
    homepage: tuple[HomepageChatService, ReplyProvider], sent: bool
) -> None:
    service, provider = homepage
    provider.failure = sent
    with pytest.raises(ApiError):
        service.reply("b" * 43, message())
    assert service.status("b" * 43).remaining == (0 if sent else 1)


def test_parallel_tabs_and_other_visitors_cannot_start_a_second_generation(
    homepage: tuple[HomepageChatService, ReplyProvider],
) -> None:
    service, provider = homepage
    started, release = Event(), Event()
    provider.started, provider.release = started, release
    with ThreadPoolExecutor(max_workers=1) as executor:
        first = executor.submit(service.reply, "c" * 43, message())
        try:
            assert started.wait(10)
            for token, code in [
                ("c" * 43, "HOMEPAGE_CHAT_IN_PROGRESS"),
                ("d" * 43, "HOMEPAGE_CHAT_BUSY"),
            ]:
                with pytest.raises(ApiError) as denied:
                    service.reply(token, message())
                assert denied.value.code == code
        finally:
            release.set()
        assert first.result().remaining == 0
    assert provider.calls == 1


def test_daily_budget_and_expired_processing_lease_fail_closed(
    homepage: tuple[HomepageChatService, ReplyProvider],
) -> None:
    service, _provider = homepage
    service.settings.homepage_chat_daily_limit = 1
    service.reply("e" * 43, message())
    with pytest.raises(ApiError) as busy:
        service.reply("f" * 43, message())
    assert busy.value.code == "HOMEPAGE_CHAT_BUSY"
    with service.sessions() as session, session.begin():
        row = session.scalar(select(HomepageChatVisitor))
        assert row is not None
        row.state = "PROCESSING"
        row.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
    assert service.status("e" * 43).state == "used"
