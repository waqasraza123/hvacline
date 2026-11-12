from collections.abc import Iterator
from dataclasses import dataclass
from uuid import UUID, uuid4

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.actors import ActorContext
from insurance_operations.approved_faqs.service import ApprovedFaqService
from insurance_operations.conversations.contracts import (
    ConnectionGrant,
    ConversationInputMode,
    ProviderSessionMetadata,
)
from insurance_operations.conversations.schemas import (
    ConversationEndOutcome,
    ConversationIntakeConfirmationInput,
    ConversationSessionCreateInput,
)
from insurance_operations.conversations.service import ConversationService
from insurance_operations.database.models.approved_faq import AgencyApprovedFaq
from insurance_operations.database.models.conversation import ConversationSession
from insurance_operations.database.models.identity import (
    Agency,
    AgencyMembership,
    AppUser,
)
from insurance_operations.database.models.receptionist import AgencyReceptionistSettings
from insurance_operations.database.models.website import Website, WebsiteAgentBinding
from insurance_operations.errors import ApiError
from insurance_operations.settings import ApiSettings, DatabaseSettings
from insurance_operations.websites.guards import session_website
from insurance_operations.websites.schemas import (
    WebsiteDocument,
    WebsiteInquiry,
    WebsiteSave,
)
from insurance_operations.websites.service import WebsiteService


class Provider:
    def __init__(self, name: str, routed: list[tuple[str, str]]) -> None:
        self.name, self.routed = name, routed

    def authorize_session(
        self, *, input_mode: ConversationInputMode = "VOICE"
    ) -> ConnectionGrant:
        self.routed.append((self.name, input_mode))
        return ConnectionGrant(
            transport="webrtc" if input_mode == "VOICE" else "websocket",
            credential="synthetic-grant-not-a-provider-call",
            metadata=ProviderSessionMetadata(
                adapter="synthetic",
                adapter_version="1",
                external_session_reference=str(uuid4()),
            ),
        )

    def close(self) -> None:
        pass


@dataclass
class Platform:
    service: WebsiteService
    sessions: sessionmaker[Session]
    owner: ActorContext
    foreign: ActorContext
    agents: list[UUID]
    faqs: list[UUID]
    routed: list[tuple[str, str]]


@pytest.fixture
def platform(
    migrated_database: Engine, database_settings: DatabaseSettings
) -> Iterator[Platform]:
    with migrated_database.connect() as connection:
        transaction = connection.begin()
        sessions = sessionmaker(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        actors, agents, faqs = [], [], []
        with sessions() as session, session.begin():
            for index in range(2):
                agency = Agency(
                    name="Synthetic website business",
                    slug=f"websites-{uuid4()}",
                    environment_kind="DEVELOPMENT",
                )
                user = AppUser(
                    auth_subject=uuid4(), display_name="Synthetic website owner"
                )
                session.add_all([agency, user])
                session.flush()
                session.add(AgencyMembership(agency_id=agency.id, app_user_id=user.id))
                actors.append(
                    ActorContext(
                        app_user_id=user.id,
                        display_name=user.display_name,
                        agency_id=agency.id,
                        agency_name=agency.name,
                        agency_environment="DEVELOPMENT",
                    )
                )
                agent = WebsiteAgentBinding(
                    agency_id=agency.id,
                    label="Synthetic configured agent",
                    provider_agent_id=f"synthetic-agent-{uuid4()}",
                    enabled=True,
                    browser_tools_confirmed=True,
                )
                session.add(agent)
                session.add(
                    AgencyReceptionistSettings(
                        agency_id=agency.id,
                        public_name="Synthetic studio",
                        greeting="Hello",
                        office_hours="By request",
                        contact_email="studio@example.test",
                        supported_insurance_categories=["CONSULTATION"],
                        escalation_message="Ask the studio team.",
                        created_by=user.id,
                        updated_by=user.id,
                    )
                )
                faq = AgencyApprovedFaq(
                    agency_id=agency.id,
                    question="What sessions are offered?",
                    normalized_question="what sessions are offered",
                    approved_answer=f"Approved synthetic answer {index}",
                    status="ACTIVE",
                    created_by=user.id,
                    updated_by=user.id,
                )
                session.add(faq)
                session.flush()
                agents.append(agent.id)
                faqs.append(faq.id)
        routed: list[tuple[str, str]] = []
        settings = ApiSettings(
            _env_file=None,
            app_environment="test",
            database_url="postgresql://127.0.0.1/unconfigured_runtime",
            test_database_url=database_settings.runtime_database_url,
            database_ssl_mode="disable",
            api_host="127.0.0.1",
            api_port=8000,
            website_platform_enabled=True,
        )
        service = WebsiteService(
            sessions, settings, lambda reference: Provider(reference, routed)
        )
        try:
            yield Platform(
                service, sessions, actors[0], actors[1], agents, faqs, routed
            )
        finally:
            transaction.rollback()


def create(
    platform: Platform,
    configuration: WebsiteDocument,
    *,
    foreign: bool = False,
    **changes: object,
) -> dict[str, object]:
    index = int(foreign)
    data = {
        "configuration": configuration.model_dump(),
        "status": "published",
        "expected_row_version": 0,
        "agent_binding_id": str(platform.agents[index]),
        "knowledge_faq_ids": [str(platform.faqs[index])],
        "voice_enabled": True,
        "lead_capture_enabled": True,
        **changes,
    }
    return platform.service.save(
        platform.foreign if foreign else platform.owner,
        WebsiteSave.model_validate(data),
    )


def authorize(
    platform: Platform,
    slug: str,
    mode: ConversationInputMode = "TEXT",
    *,
    foreign: bool = False,
):
    return platform.service.authorize(
        platform.foreign if foreign else platform.owner,
        slug,
        ConversationSessionCreateInput(
            input_mode=mode,
            ai_disclosure_accepted=True,
            microphone_consent_granted=mode == "VOICE",
        ),
    )


def test_persistence_public_projection_and_version_conflicts(
    platform: Platform, website_document: WebsiteDocument
) -> None:
    saved = create(platform, website_document)
    assert saved["row_version"] == 1
    public = platform.service.public(website_document.slug)
    assert public["voice_available"] is True
    assert "agent_binding_id" not in public and "agency_id" not in public
    assert "provider_agent_id" not in str(platform.service.list(platform.owner))
    data = WebsiteSave(
        configuration=website_document, status="draft", expected_row_version=1
    )
    updated = platform.service.save(platform.owner, data, UUID(str(saved["id"])))
    assert updated["row_version"] == 2
    with pytest.raises(ApiError) as conflict:
        platform.service.save(platform.owner, data, UUID(str(saved["id"])))
    assert conflict.value.status_code == 409
    assert platform.service.public(website_document.slug)["voice_available"] is True
    platform.service.publication(
        platform.owner, UUID(str(saved["id"])), 2, unpublish=True
    )
    with pytest.raises(ApiError):
        platform.service.public(website_document.slug)


def test_cross_business_agents_knowledge_and_updates_are_denied(
    platform: Platform, website_document: WebsiteDocument
) -> None:
    saved = create(platform, website_document)
    with pytest.raises(ApiError):
        create(platform, website_document, agent_binding_id=str(platform.agents[1]))
    with pytest.raises(ApiError):
        create(platform, website_document, knowledge_faq_ids=[str(platform.faqs[1])])
    with pytest.raises(ApiError):
        platform.service.save(
            platform.foreign,
            WebsiteSave(
                configuration=website_document, status="draft", expected_row_version=1
            ),
            UUID(str(saved["id"])),
        )
    with pytest.raises(ApiError):
        authorize(platform, website_document.slug, foreign=True)
    assert platform.routed == []


@pytest.mark.parametrize("mode", ["VOICE", "TEXT"])
def test_correct_agent_and_immutable_conversation_binding(
    platform: Platform, website_document: WebsiteDocument, mode: ConversationInputMode
) -> None:
    saved = create(platform, website_document)
    grant = authorize(platform, website_document.slug, mode)
    assert platform.routed[0][1] == mode
    with platform.sessions() as session:
        row = session.get(ConversationSession, grant.session_id)
        assert row is not None and row.website_id == UUID(str(saved["id"]))
        assert row.website_agent_binding_id == platform.agents[0]
        assert row.website_capabilities == {
            "knowledge": True,
            "lead_capture": True,
            "booking": False,
            "memory": False,
        }
        assert (
            session.get(WebsiteAgentBinding, platform.agents[0]).provider_agent_id
            == platform.routed[0][0]
        )
        for capability in ("booking", "memory"):
            with pytest.raises(ApiError):
                session_website(session, row, capability)


def test_knowledge_is_scoped_even_through_legacy_lookup(
    platform: Platform, website_document: WebsiteDocument
) -> None:
    saved = create(platform, website_document)
    grant = authorize(platform, website_document.slug)
    lookup = ApprovedFaqService(session_factory=platform.sessions)
    result = lookup.conversation_lookup(
        actor=platform.owner,
        conversation_session_id=grant.session_id,
        query="What sessions are offered?",
        correlation_id=uuid4(),
    )
    assert result.answer == "Approved synthetic answer 0"
    data = WebsiteSave(
        configuration=website_document,
        status="published",
        expected_row_version=1,
        agent_binding_id=platform.agents[0],
        voice_enabled=True,
        knowledge_faq_ids=[],
    )
    platform.service.save(platform.owner, data, UUID(str(saved["id"])))
    with pytest.raises(ApiError):
        lookup.conversation_lookup(
            actor=platform.owner,
            conversation_session_id=grant.session_id,
            query="What sessions are offered?",
            correlation_id=uuid4(),
        )
    ConversationService(
        session_factory=platform.sessions,
        settings=platform.service.settings,
        provider=None,
    ).end_session(
        actor=platform.owner,
        conversation_session_id=grant.session_id,
        outcome=ConversationEndOutcome.COMPLETED,
    )
    next_grant = authorize(platform, website_document.slug)
    result = lookup.conversation_lookup(
        actor=platform.owner,
        conversation_session_id=next_grant.session_id,
        query="What sessions are offered?",
        correlation_id=uuid4(),
    )
    assert result.matched is False


def test_missing_disabled_and_unconfigured_sites_do_not_fallback(
    platform: Platform, website_document: WebsiteDocument
) -> None:
    for slug in ("missing", website_document.slug):
        with pytest.raises(ApiError):
            authorize(platform, slug)
    create(platform, website_document, voice_enabled=False)
    assert platform.service.public(website_document.slug)["voice_available"] is False
    with pytest.raises(ApiError):
        authorize(platform, website_document.slug)
    assert not platform.routed


def test_database_composite_foreign_key_blocks_foreign_agent(
    platform: Platform, website_document: WebsiteDocument
) -> None:
    with pytest.raises(IntegrityError), platform.sessions() as session, session.begin():
        session.add(
            Website(
                agency_id=platform.owner.agency_id,
                slug="foreign-binding",
                template_id="calm",
                configuration=website_document.model_dump(mode="json"),
                agent_binding_id=platform.agents[1],
            )
        )
        session.flush()


def test_confirmed_non_hvac_inquiry_uses_existing_lead_workflow(
    platform: Platform, website_document: WebsiteDocument
) -> None:
    create(platform, website_document)
    grant = authorize(platform, website_document.slug)
    conversations = ConversationService(
        session_factory=platform.sessions,
        settings=platform.service.settings,
        provider=None,
    )
    conversations.end_session(
        actor=platform.owner,
        conversation_session_id=grant.session_id,
        outcome=ConversationEndOutcome.COMPLETED,
    )
    request = WebsiteInquiry(
        explicit_confirmation=True,
        conversation_session_id=grant.session_id,
        customer={"full_name": "Synthetic visitor", "email": "visitor@example.com"},
        intake_intent="Please discuss a studio consultation",
        transcript=[
            {"speaker": "AGENT", "text": "What would you like the team to review?"},
            {"speaker": "USER", "text": "Please discuss a studio consultation"},
        ],
    )
    with pytest.raises(ApiError) as unconfirmed:
        conversations.confirm_intake(
            actor=platform.owner,
            request=ConversationIntakeConfirmationInput.model_validate(
                request.model_dump()
            ),
            idempotency_key="unconfirmed-legacy-inquiry",
            correlation_id=uuid4(),
        )
    assert unconfirmed.value.code == "WEBSITE_CONFIRMATION_REQUIRED"
    result, replayed = conversations.confirm_intake(
        actor=platform.owner,
        request=request,
        idempotency_key="synthetic-inquiry",
        correlation_id=uuid4(),
    )
    assert (
        result.lead_id is not None
        and result.service_request_id is None
        and not replayed
    )
    replay, replayed = conversations.confirm_intake(
        actor=platform.owner,
        request=request,
        idempotency_key="synthetic-inquiry",
        correlation_id=uuid4(),
    )
    assert replay.lead_id == result.lead_id and replayed


def test_independent_websites_route_to_distinct_agents_and_deny_wrong_site_session(
    platform: Platform, website_document: WebsiteDocument
) -> None:
    create(platform, website_document)
    first = authorize(platform, website_document.slug)
    ConversationService(
        session_factory=platform.sessions,
        settings=platform.service.settings,
        provider=None,
    ).end_session(
        actor=platform.owner,
        conversation_session_id=first.session_id,
        outcome=ConversationEndOutcome.COMPLETED,
    )
    with platform.sessions() as session, session.begin():
        agent = WebsiteAgentBinding(
            agency_id=platform.owner.agency_id,
            label="Second configured studio",
            provider_agent_id=f"second-agent-{uuid4()}",
            enabled=True,
            browser_tools_confirmed=True,
        )
        session.add(agent)
        session.flush()
        second_agent = agent.id
    second_site = website_document.model_copy(update={"slug": "second-studio"})
    create(platform, second_site, agent_binding_id=str(second_agent))
    second = authorize(platform, second_site.slug, "VOICE")
    assert platform.routed[0][0] != platform.routed[1][0]
    with pytest.raises(ApiError):
        platform.service.owned_session(
            platform.owner, website_document.slug, second.session_id
        )
    with pytest.raises(ApiError):
        platform.service.owned_session(
            platform.foreign, second_site.slug, second.session_id
        )


def test_binding_revocation_blocks_existing_session_tools(
    platform: Platform, website_document: WebsiteDocument
) -> None:
    create(platform, website_document)
    grant = authorize(platform, website_document.slug)
    with platform.sessions() as session, session.begin():
        binding = session.get(WebsiteAgentBinding, platform.agents[0])
        assert binding is not None
        binding.enabled = False
    with pytest.raises(ApiError):
        ApprovedFaqService(session_factory=platform.sessions).conversation_lookup(
            actor=platform.owner,
            conversation_session_id=grant.session_id,
            query="What sessions are offered?",
            correlation_id=uuid4(),
        )
    assert platform.service.public(website_document.slug)["voice_available"] is False


def test_website_sessions_cannot_read_existing_account_memory(
    platform: Platform, website_document: WebsiteDocument
) -> None:
    from insurance_operations.customer_memory.service import CustomerMemoryService
    from insurance_operations.database.models.customer_account import CustomerAccount

    create(platform, website_document)
    grant = authorize(platform, website_document.slug)
    account = CustomerAccount(
        agency_id=platform.owner.agency_id,
        app_user_id=platform.owner.app_user_id,
        email="synthetic@example.com",
        password_hash="not-a-real-password",
    )
    with platform.sessions() as session, pytest.raises(ApiError):
        CustomerMemoryService(
            platform.sessions, platform.service.settings
        ).active_session(session, account, grant.session_id)


def test_concurrent_owner_edits_have_one_winner(
    migrated_database: Engine,
    database_settings: DatabaseSettings,
    website_document: WebsiteDocument,
) -> None:
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from sqlalchemy import delete

    sessions = sessionmaker(bind=migrated_database, expire_on_commit=False)
    with sessions() as session, session.begin():
        agency = Agency(
            name="Concurrent synthetic owner",
            slug=f"website-concurrent-{uuid4()}",
            environment_kind="DEVELOPMENT",
        )
        user = AppUser(auth_subject=uuid4(), display_name="Synthetic owner")
        session.add_all([agency, user])
        session.flush()
        actor = ActorContext(
            app_user_id=user.id,
            display_name=user.display_name,
            agency_id=agency.id,
            agency_name=agency.name,
            agency_environment="DEVELOPMENT",
        )
    settings = ApiSettings(
        _env_file=None,
        app_environment="test",
        database_url="postgresql://127.0.0.1/unconfigured_runtime",
        test_database_url=database_settings.runtime_database_url,
        database_ssl_mode="disable",
        api_host="127.0.0.1",
        api_port=8000,
        website_platform_enabled=True,
    )
    service = WebsiteService(sessions, settings)
    configuration = website_document.model_copy(
        update={"slug": f"concurrent-{uuid4()}"}
    )
    saved = service.save(
        actor,
        WebsiteSave(
            configuration=configuration, status="draft", expected_row_version=0
        ),
    )
    site_id = UUID(str(saved["id"]))
    barrier = Barrier(2)

    def edit(_: int) -> int:
        barrier.wait(timeout=10)
        try:
            service.save(
                actor,
                WebsiteSave(
                    configuration=configuration, status="draft", expected_row_version=1
                ),
                site_id,
            )
            return 200
        except ApiError as error:
            return error.status_code

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            assert sorted(pool.map(edit, range(2))) == [200, 409]
    finally:
        with sessions() as session, session.begin():
            session.execute(delete(Website).where(Website.id == site_id))
            from insurance_operations.database.models.operations import AuditEvent

            session.execute(
                delete(AuditEvent).where(AuditEvent.agency_id == actor.agency_id)
            )
            session.execute(delete(AppUser).where(AppUser.id == actor.app_user_id))
            session.execute(delete(Agency).where(Agency.id == actor.agency_id))


def test_http_session_authorization_uses_existing_mfa_identity(
    platform: Platform, website_document: WebsiteDocument
) -> None:
    import asyncio
    import hashlib
    from datetime import UTC, datetime, timedelta

    from cryptography.fernet import Fernet
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse
    from httpx import ASGITransport, AsyncClient

    from insurance_operations.database.models.customer_account import (
        CustomerAccount,
        CustomerLoginSession,
    )
    from insurance_operations.database.models.customer_mfa import CustomerMfaFactor
    from insurance_operations.websites.routes import create_website_router

    create(platform, website_document)
    settings = ApiSettings(
        _env_file=None,
        app_environment="development",
        database_url=str(platform.sessions.kw["bind"].engine.url),
        database_ssl_mode="disable",
        api_host="127.0.0.1",
        api_port=8000,
        website_platform_enabled=True,
        customer_portal_enabled=True,
        customer_portal_secret="synthetic-portal-key-with-at-least-32-characters",
        customer_mfa_encryption_key=Fernet.generate_key().decode(),
        demo_sandbox_enabled=True,
        demo_admin_token="synthetic-admin-token-at-least-32-characters",
        development_actor_user_id=platform.owner.app_user_id,
    )
    token = "synthetic-verified-customer-session-token"
    now = datetime.now(UTC)
    with platform.sessions() as session, session.begin():
        account = CustomerAccount(
            agency_id=platform.owner.agency_id,
            app_user_id=platform.owner.app_user_id,
            email="synthetic@example.com",
            password_hash="synthetic-not-a-login-hash",
            created_at=now,
        )
        session.add(account)
        session.flush()
        session.add(
            CustomerMfaFactor(
                account_id=account.id,
                agency_id=platform.owner.agency_id,
                version=1,
                secret_ciphertext="synthetic-test-factor",
                enabled_at=now,
                last_counter=1,
                failed_attempts=0,
            )
        )
        session.add(
            CustomerLoginSession(
                account_id=account.id,
                token_hash=hashlib.sha256(token.encode()).hexdigest(),
                expires_at=now + timedelta(hours=1),
                mfa_verified_at=now,
                mfa_version=1,
            )
        )
    app = FastAPI()

    @app.exception_handler(ApiError)
    async def api_error(_: Request, error: ApiError):
        return JSONResponse(
            status_code=error.status_code, content={"error": {"code": error.code}}
        )

    app.include_router(
        create_website_router(
            settings, platform.sessions, lambda: platform.owner, platform.service
        )
    )

    async def exercise() -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            path = (
                f"/api/v1/customer/websites/{website_document.slug}"
                "/conversation-sessions"
            )
            body = {
                "input_mode": "TEXT",
                "ai_disclosure_accepted": True,
                "microphone_consent_granted": False,
            }
            assert (await client.post(path, json=body)).status_code == 404
            headers = {
                "X-Customer-Portal-Key": (
                    settings.customer_portal_secret.get_secret_value()
                ),
                "Authorization": f"Bearer {token}",
            }
            assert (
                await client.post(
                    path, headers=headers, json={**body, "agent_id": "foreign"}
                )
            ).status_code == 422
            invalid = {**body, "ai_disclosure_accepted": False}
            assert (
                await client.post(path, headers=headers, json=invalid)
            ).status_code == 422
            response = await client.post(path, headers=headers, json=body)
            assert response.status_code == 201
            assert response.json()["input_mode"] == "TEXT"
            assert "provider_agent_id" not in response.text
            assert len(platform.routed) == 1

    asyncio.run(exercise())


def test_drafts_publications_history_restore_and_unpublish(
    platform: Platform, website_document: WebsiteDocument
) -> None:
    from insurance_operations.database.models.website import WebsiteVersion

    original = create(platform, website_document)
    site_id = UUID(str(original["id"]))
    first_version = UUID(str(original["published_version_id"]))
    public_before = platform.service.public(website_document.slug)
    grant = authorize(platform, website_document.slug)
    edited = website_document.model_copy(
        update={
            "hero": website_document.hero.model_copy(
                update={"title": "A revised studio"}
            )
        }
    )
    draft = platform.service.save(
        platform.owner,
        WebsiteSave(
            expected_row_version=1,
            configuration=edited,
            status="draft",
            agent_binding_id=platform.agents[0],
            voice_enabled=True,
            knowledge_faq_ids=[],
            lead_capture_enabled=False,
        ),
        site_id,
    )
    assert draft["status"] == "published" and draft["row_version"] == 2
    assert platform.service.public(website_document.slug) == public_before
    assert len(platform.service.versions(platform.owner, site_id)) == 1
    with platform.sessions() as session:
        assert (
            session.get(ConversationSession, grant.session_id).website_version_id
            == first_version
        )
    published = platform.service.publication(platform.owner, site_id, 2)
    assert published["row_version"] == 3
    assert (
        platform.service.public(website_document.slug)["configuration"]["hero"]["title"]
        == "A revised studio"
    )
    with pytest.raises(ApiError):
        ApprovedFaqService(session_factory=platform.sessions).conversation_lookup(
            actor=platform.owner,
            conversation_session_id=grant.session_id,
            query="What sessions are offered?",
            correlation_id=uuid4(),
        )
    platform.service.owned_session(
        platform.owner, website_document.slug, grant.session_id
    )
    restored = platform.service.publication(
        platform.owner, site_id, 3, restore_version_id=first_version
    )
    assert restored["row_version"] == 4
    assert restored["configuration"]["hero"]["title"] == "A revised studio"
    assert platform.service.public(website_document.slug) == public_before
    versions = platform.service.versions(platform.owner, site_id)
    assert [version["number"] for version in versions] == [3, 2, 1]
    assert versions[0]["active"] is True
    with platform.sessions() as session:
        assert (
            session.get(WebsiteVersion, first_version).configuration["hero"]["title"]
            == website_document.hero.title
        )
    platform.service.publication(platform.owner, site_id, 4, unpublish=True)
    with pytest.raises(ApiError):
        platform.service.public(website_document.slug)
    with pytest.raises(ApiError):
        authorize(platform, website_document.slug)
    assert len(platform.service.versions(platform.owner, site_id)) == 3
    platform.service.publication(
        platform.owner, site_id, 5, restore_version_id=first_version
    )
    assert platform.service.public(website_document.slug) == public_before


def test_publication_conflicts_ownership_and_revoked_bindings(
    platform: Platform, website_document: WebsiteDocument
) -> None:
    saved = create(platform, website_document)
    site_id = UUID(str(saved["id"]))
    version_id = UUID(str(saved["published_version_id"]))
    with pytest.raises(ApiError) as duplicate:
        create(platform, website_document)
    assert duplicate.value.status_code == 409
    with pytest.raises(ApiError) as stale:
        platform.service.publication(platform.owner, site_id, 99)
    assert stale.value.code == "WEBSITE_VERSION_CONFLICT"
    for mutation in (
        lambda: platform.service.publication(platform.foreign, site_id, 1),
        lambda: platform.service.publication(
            platform.foreign, site_id, 1, unpublish=True
        ),
        lambda: platform.service.versions(platform.foreign, site_id),
        lambda: platform.service.publication(
            platform.owner, site_id, 1, restore_version_id=uuid4()
        ),
    ):
        with pytest.raises(ApiError):
            mutation()
    second = create(
        platform, website_document.model_copy(update={"slug": "another-studio"})
    )
    with pytest.raises(ApiError):
        platform.service.publication(
            platform.owner, UUID(str(second["id"])), 1, restore_version_id=version_id
        )
    with platform.sessions() as session, session.begin():
        session.get(WebsiteAgentBinding, platform.agents[0]).enabled = False
    with pytest.raises(ApiError) as revoked:
        platform.service.publication(
            platform.owner, site_id, 1, restore_version_id=version_id
        )
    assert revoked.value.code == "WEBSITE_AGENT_UNAVAILABLE"
    assert platform.service.list(platform.owner)["websites"][1]["row_version"] == 1


def test_published_versions_are_immutable_and_pointers_cannot_cross_sites(
    platform: Platform, website_document: WebsiteDocument
) -> None:
    from sqlalchemy import delete, update
    from sqlalchemy.exc import DBAPIError

    from insurance_operations.database.models.website import WebsiteVersion

    first = create(platform, website_document)
    second = create(
        platform, website_document.model_copy(update={"slug": "different-studio"})
    )
    version_id = UUID(str(first["published_version_id"]))
    for statement in (
        update(WebsiteVersion).where(WebsiteVersion.id == version_id).values(number=99),
        delete(WebsiteVersion).where(WebsiteVersion.id == version_id),
    ):
        with pytest.raises(DBAPIError), platform.sessions() as session, session.begin():
            session.execute(statement)
    with pytest.raises(IntegrityError), platform.sessions() as session, session.begin():
        site = session.get(Website, UUID(str(second["id"])))
        site.published_version_id = version_id
        session.flush()
