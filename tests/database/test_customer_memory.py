import asyncio
import subprocess
import sys
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from insurance_operations.actors import ActorContext
from insurance_operations.conversations.schemas import ConversationTurn
from insurance_operations.customer_memory.purge import purge_expired
from insurance_operations.customer_memory.routes import create_customer_memory_router
from insurance_operations.customer_memory.schemas import (
    MemoryConsentInput,
    MemoryFactInput,
    MemoryFactSaveInput,
    MemoryMutation,
    MemoryPairInput,
)
from insurance_operations.customer_memory.service import (
    CustomerMemoryService,
    redact_pairing_codes,
)
from insurance_operations.customers import CustomerInput, customer_from_input
from insurance_operations.database.connection import create_database_engine
from insurance_operations.database.models.conversation import (
    ConversationIntake,
    ConversationSession,
)
from insurance_operations.database.models.customer_account import CustomerAccount
from insurance_operations.database.models.customer_memory import (
    CustomerMemoryFact,
    CustomerMemoryPolicy,
    CustomerMemorySummary,
)
from insurance_operations.database.models.customer_mfa import CustomerMfaFactor
from insurance_operations.database.models.identity import Agency, AppUser
from insurance_operations.database.models.operations import AuditEvent
from insurance_operations.database.models.whatsapp import WhatsAppConversation
from insurance_operations.errors import ApiError
from insurance_operations.settings import ApiSettings, DatabaseSettings


@dataclass
class MemoryHarness:
    memory: CustomerMemoryService
    owner: ActorContext
    other: ActorContext
    foreign: ActorContext


@pytest.fixture
def harness(
    migrated_database: Engine, database_settings: DatabaseSettings
) -> Iterator[MemoryHarness]:
    with migrated_database.connect() as connection:
        transaction = connection.begin()
        sessions = sessionmaker(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        actors: list[ActorContext] = []
        with sessions() as session, session.begin():
            agency = Agency(
                name="Synthetic Memory HVAC",
                slug=f"memory-{uuid4()}",
                environment_kind="DEVELOPMENT",
            )
            foreign = Agency(
                name="Separate HVAC",
                slug=f"memory-{uuid4()}",
                environment_kind="DEVELOPMENT",
            )
            session.add_all([agency, foreign])
            session.flush()
            for business in (agency, agency, foreign):
                user = AppUser(
                    auth_subject=uuid4(), display_name="Fictional memory customer"
                )
                session.add(user)
                session.flush()
                account = CustomerAccount(
                    agency_id=business.id,
                    app_user_id=user.id,
                    email=f"memory-{uuid4()}@example.test",
                    password_hash="synthetic-not-a-login-hash",
                    created_at=datetime.now(UTC),
                )
                session.add(account)
                session.flush()
                session.add(
                    CustomerMfaFactor(
                        account_id=account.id,
                        agency_id=business.id,
                        version=1,
                        secret_ciphertext="synthetic-service-fixture-not-an-encrypted-secret",
                        enabled_at=datetime.now(UTC),
                        last_counter=1,
                        failed_attempts=0,
                    )
                )
                actors.append(
                    ActorContext(
                        app_user_id=user.id,
                        display_name=user.display_name,
                        agency_id=business.id,
                        agency_name=business.name,
                        agency_environment="DEVELOPMENT",
                    )
                )
        settings = ApiSettings(
            _env_file=None,
            app_environment="development",
            api_host="127.0.0.1",
            api_port=8000,
            database_url=database_settings.runtime_database_url,
            database_ssl_mode=database_settings.database_ssl_mode,
            customer_memory_enabled=True,
        )
        try:
            yield MemoryHarness(
                CustomerMemoryService(sessions, settings),
                actors[0],
                actors[1],
                actors[2],
            )
        finally:
            transaction.rollback()


def revision(memory: CustomerMemoryService, actor: ActorContext) -> int:
    value = memory.view(actor)["revision"]
    assert isinstance(value, int)
    return value


def enable(memory: CustomerMemoryService, actor: ActorContext) -> None:
    memory.set_consent(
        actor,
        MemoryConsentInput(
            expected_revision=revision(memory, actor),
            request_id=uuid4(),
            enabled=True,
            explicit_confirmation=True,
        ),
        True,
        uuid4(),
    )


def conversation(
    memory: CustomerMemoryService,
    actor: ActorContext,
    channel: str = "BROWSER",
    input_mode: str = "VOICE",
) -> UUID:
    now = datetime.now(UTC)
    with memory.sessions() as session, session.begin():
        row = ConversationSession(
            agency_id=actor.agency_id,
            initiated_by=actor.app_user_id,
            channel=channel,
            input_mode=input_mode,
            status="AUTHORIZED",
            provider_metadata={},
            disclosure_accepted_at=now,
            microphone_consent_at=now if input_mode == "VOICE" else None,
            synthetic_data_acknowledged_at=now,
            maximum_duration_seconds=180,
            authorization_expires_at=now + timedelta(seconds=180),
            confirmation_expires_at=now + timedelta(minutes=30),
            authorized_at=now,
            created_at=now,
            updated_at=now,
        )
        session.add(row)
        session.flush()
        return row.id


def authorized_intake(
    memory: CustomerMemoryService,
    actor: ActorContext,
    session_id: UUID,
    statement: str = "My furnace needs service.",
    confirmed_at: datetime | None = None,
) -> UUID:
    with memory.sessions() as session, session.begin():
        customer = customer_from_input(
            CustomerInput(full_name="Fictional caller", email="fictional@example.com"),
            actor,
        )
        session.add(customer)
        session.flush()
        intake = ConversationIntake(
            agency_id=actor.agency_id,
            customer_id=customer.id,
            conversation_session_id=session_id,
            created_by=actor.app_user_id,
            intake_intent="Fictional equipment discussion",
            confirmed_at=confirmed_at or datetime.now(UTC),
            confirmed_transcript=[
                {"speaker": "USER", "text": statement},
                {
                    "speaker": "AGENT",
                    "text": "May I save this fictional request and transcript?",
                },
                {"speaker": "USER", "text": "yes"},
            ],
        )
        session.add(intake)
        session.flush()
        return intake.id


def save_control(
    memory: CustomerMemoryService, actor: ActorContext, value: str = "AFTERNOON"
) -> MemoryFactSaveInput:
    data = MemoryFactSaveInput(
        expected_revision=revision(memory, actor),
        request_id=uuid4(),
        facts=[MemoryFactInput(key="appointment_time", value=value)],
        explicit_confirmation=True,
    )
    memory.save(actor, data, uuid4())
    return data


def test_memory_recalls_across_sessions_without_cross_customer_or_tenant_leak(
    harness: MemoryHarness,
) -> None:
    memory, owner = harness.memory, harness.owner
    enable(memory, owner)
    saved = save_control(memory, owner)
    memory.save(owner, saved, uuid4())
    first, second = conversation(memory, owner), conversation(memory, owner)
    assert "afternoon appointments" in str(
        memory.view(owner, context_only=True, browser_session_id=first)["summary"]
    )
    assert "afternoon appointments" in str(
        memory.view(owner, context_only=True, browser_session_id=second)["summary"]
    )
    assert memory.view(harness.other)["facts"] == []
    assert memory.view(harness.foreign)["facts"] == []
    for actor in (harness.other, harness.foreign):
        with pytest.raises(ApiError):
            memory.view(actor, context_only=True, browser_session_id=first)
    with memory.sessions() as session:
        assert session.scalar(select(func.count()).select_from(CustomerMemoryFact)) == 1


def test_only_authorized_owned_sources_support_facts_and_transcripts_are_not_duplicated(
    harness: MemoryHarness,
) -> None:
    memory, owner = harness.memory, harness.owner
    enable(memory, owner)
    session_id = conversation(memory, owner)
    intake_id = authorized_intake(memory, owner, session_id)
    memory.save(
        owner,
        MemoryFactSaveInput(
            expected_revision=revision(memory, owner),
            request_id=uuid4(),
            facts=[MemoryFactInput(key="equipment_type", value="FURNACE")],
            source_intake_id=intake_id,
            explicit_confirmation=True,
        ),
        uuid4(),
    )
    assert "furnace" in str(memory.view(owner, context_only=True)["summary"])
    with memory.sessions() as session:
        assert (
            session.scalar(select(func.count()).select_from(CustomerMemorySummary)) == 1
        )
        assert (
            session.scalar(
                select(func.count())
                .select_from(ConversationIntake)
                .where(ConversationIntake.id == intake_id)
            )
            == 1
        )
    memory.remove_fact(
        owner,
        "equipment_type",
        MemoryMutation(
            expected_revision=revision(memory, owner),
            request_id=uuid4(),
        ),
        uuid4(),
    )
    assert "furnace" not in str(memory.view(owner, context_only=True)["summary"])
    for actor in (harness.other, harness.foreign):
        with memory.sessions() as session, pytest.raises(ApiError):
            memory.source(session, memory.account(session, actor), intake_id)
    with pytest.raises(ApiError):
        memory.save(
            owner,
            MemoryFactSaveInput(
                expected_revision=revision(memory, owner),
                request_id=uuid4(),
                facts=[MemoryFactInput(key="equipment_type", value="HEAT_PUMP")],
                source_intake_id=intake_id,
                explicit_confirmation=True,
            ),
            uuid4(),
        )


def test_corrections_conflicts_erasure_and_retention_prevent_resurrection(
    harness: MemoryHarness,
) -> None:
    memory, owner = harness.memory, harness.owner
    enable(memory, owner)
    old = save_control(memory, owner)
    save_control(memory, owner, "MORNING")
    with pytest.raises(ApiError):
        memory.save(owner, old, uuid4())
    assert "morning appointments" in str(
        memory.view(owner, context_only=True)["summary"]
    )
    with memory.sessions() as session, session.begin():
        row = session.scalar(select(CustomerMemoryFact))
        assert row is not None
        row.updated_at = datetime.now(UTC) - timedelta(days=100)
        row.expires_at = datetime.now(UTC) - timedelta(days=1)
    assert memory.view(owner)["facts"] == []
    with memory.sessions() as session, session.begin():
        assert purge_expired(session, 90) == 1
    save_control(memory, owner)
    stale = conversation(memory, owner)
    memory.set_consent(
        owner,
        MemoryMutation(
            expected_revision=revision(memory, owner),
            request_id=uuid4(),
        ),
        None,
        uuid4(),
    )
    assert memory.view(owner)["facts"] == []
    with pytest.raises(ApiError):
        memory.view(owner, context_only=True, browser_session_id=stale)
    with pytest.raises(ApiError):
        memory.save(owner, old, uuid4())


def test_whatsapp_requires_browser_approved_link_and_unlink_revokes_current_tools(
    harness: MemoryHarness,
) -> None:
    memory, owner = harness.memory, harness.owner
    enable(memory, owner)
    save_control(memory, owner)
    call_session = conversation(memory, harness.other, "WHATSAPP")
    now = datetime.now(UTC)
    with memory.sessions() as session, session.begin():
        binding = WhatsAppConversation(
            agency_id=owner.agency_id,
            session_id=call_session,
            conversation_id=f"conv_{uuid4()}",
            phone_number_id="synthetic-business-id",
            caller_digest="a" * 64,
            initialized_at=now,
            expires_at=now + timedelta(seconds=180),
        )
        session.add(binding)
        session.flush()
        binding_id = binding.id
    assert memory.whatsapp_actor(binding_id) is None
    code = memory.begin_pairing(binding_id)
    enable(memory, harness.foreign)
    with pytest.raises(ApiError):
        memory.approve_pairing(
            harness.foreign,
            MemoryPairInput(
                expected_revision=revision(memory, harness.foreign),
                request_id=uuid4(),
                code=code,
                explicit_confirmation=True,
            ),
            code,
            uuid4(),
        )
    memory.approve_pairing(
        owner,
        MemoryPairInput(
            expected_revision=revision(memory, owner),
            request_id=uuid4(),
            code=code,
            explicit_confirmation=True,
        ),
        code,
        uuid4(),
    )
    linked = memory.whatsapp_actor(binding_id)
    assert linked is not None and linked.app_user_id == owner.app_user_id
    assert "afternoon appointments" in str(
        memory.view(linked, context_only=True, whatsapp_binding_id=binding_id)[
            "summary"
        ]
    )
    sanitized = redact_pairing_codes(
        [
            ConversationTurn(speaker="AGENT", text=f"Your linking code is {code}."),
        ]
    )
    assert code not in sanitized[0].text
    with memory.sessions() as session, session.begin():
        previous = session.get(WhatsAppConversation, binding_id)
        assert previous is not None
        previous.finalized_at = datetime.now(UTC)
        previous_session = session.get(ConversationSession, call_session)
        assert previous_session is not None
        previous_session.ended_at = datetime.now(UTC)
    second_session = conversation(memory, harness.other, "WHATSAPP")
    now = datetime.now(UTC)
    with memory.sessions() as session, session.begin():
        returning = WhatsAppConversation(
            agency_id=owner.agency_id,
            session_id=second_session,
            conversation_id=f"conv_{uuid4()}",
            phone_number_id="synthetic-business-id",
            caller_digest="a" * 64,
            initialized_at=now,
            expires_at=now + timedelta(seconds=180),
        )
        session.add(returning)
        session.flush()
        returning_id = returning.id
    returning_actor = memory.whatsapp_actor(returning_id)
    assert (
        returning_actor is not None and returning_actor.app_user_id == owner.app_user_id
    )
    assert "afternoon appointments" in str(
        memory.view(
            returning_actor, context_only=True, whatsapp_binding_id=returning_id
        )["summary"]
    )
    with memory.sessions() as session, session.begin():
        account = memory.account(session, owner)
        factor = session.get(CustomerMfaFactor, account.id)
        assert factor is not None
        factor.version += 1
    assert memory.view(owner)["whatsapp_linked"] is False
    assert memory.whatsapp_actor(returning_id) is None
    with pytest.raises(ApiError):
        memory.view(
            returning_actor, context_only=True, whatsapp_binding_id=returning_id
        )
    memory.unlink(
        owner,
        MemoryMutation(
            expected_revision=revision(memory, owner),
            request_id=uuid4(),
        ),
        uuid4(),
    )
    assert memory.whatsapp_actor(binding_id) is None
    with pytest.raises(ApiError):
        memory.view(
            returning_actor, context_only=True, whatsapp_binding_id=returning_id
        )


def test_customer_can_delete_optional_data_when_business_disables_memory(
    harness: MemoryHarness,
) -> None:
    memory, owner = harness.memory, harness.owner
    enable(memory, owner)
    save_control(memory, owner)
    memory.settings.customer_memory_enabled = False
    assert memory.view(owner)["available"] is False
    with pytest.raises(ApiError):
        memory.view(owner, context_only=True)
    memory.set_consent(
        owner,
        MemoryMutation(
            expected_revision=revision(memory, owner),
            request_id=uuid4(),
        ),
        None,
        uuid4(),
    )
    assert memory.view(owner)["facts"] == []


def test_increasing_business_retention_does_not_silently_increase_customer_cap(
    harness: MemoryHarness,
) -> None:
    memory, owner = harness.memory, harness.owner
    enable(memory, owner)
    save_control(memory, owner)
    memory.settings.customer_memory_retention_days = 1
    assert memory.view(owner)["retention_days"] == 1
    memory.settings.customer_memory_retention_days = 90
    assert memory.view(owner)["retention_days"] == 1
    memory.set_consent(
        owner,
        MemoryMutation(
            expected_revision=revision(memory, owner),
            request_id=uuid4(),
        ),
        None,
        uuid4(),
    )
    assert memory.view(owner)["retention_days"] == 90
    assert memory.view(owner)["facts"] == []


def memory_application(harness: MemoryHarness) -> FastAPI:
    def correlation(request: Request) -> None:
        request.state.correlation_id = str(uuid4())

    def actor() -> ActorContext:
        return harness.owner

    app = FastAPI(dependencies=[Depends(correlation)])

    @app.exception_handler(ApiError)
    async def failure(_request: Request, error: ApiError) -> JSONResponse:
        return JSONResponse(status_code=error.status_code, content={"code": error.code})

    app.include_router(
        create_customer_memory_router(
            harness.memory.settings,
            harness.memory.sessions,
            actor,
        )
    )
    return app


def test_confirmed_preference_flow_uses_same_postgres_memory_for_voice_and_text(
    harness: MemoryHarness,
) -> None:
    memory, owner = harness.memory, harness.owner
    app = memory_application(harness)

    async def exercise() -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            first = conversation(memory, owner)
            disabled = await client.post(
                f"/conversation-sessions/{first}/memory/context"
            )
            assert disabled.json()["summary"] == ""
            with pytest.raises(ApiError):
                save_control(memory, owner)
            enable(memory, owner)
            intake_id = authorized_intake(
                memory, owner, first, "I prefer weekday mornings for appointments."
            )
            facts = [
                {"key": "appointment_time", "value": "MORNING"},
                {"key": "appointment_days", "value": "WEEKDAYS"},
            ]
            prepared = await client.post(
                f"/conversation-sessions/{first}/memory/readback", json={"facts": facts}
            )
            assert prepared.status_code == 200
            metadata = prepared.json()
            assert metadata["source_intake_id"] == str(intake_id)
            body = {key: value for key, value in metadata.items() if key != "readback"}
            body.update(
                facts=facts,
                explicit_confirmation=True,
                transcript=[
                    {"speaker": "AGENT", "text": metadata["readback"]},
                    {"speaker": "USER", "text": "no"},
                ],
            )
            path = f"/conversation-sessions/{first}/memory/remember"
            assert (await client.post(path, json=body)).status_code == 409
            assert memory.view(owner)["facts"] == []
            body["transcript"][-1]["text"] = "yes"
            body["explicit_confirmation"] = False
            assert (await client.post(path, json=body)).status_code == 422
            body["explicit_confirmation"] = True
            saved = await client.post(path, json=body)
            assert saved.status_code == 204
            assert saved.headers["cache-control"] == "no-store"
            assert (await client.post(path, json=body)).status_code == 204
            body["transcript"] = [
                {"speaker": "USER", "text": "Please retry the same save."},
                {"speaker": "AGENT", "text": metadata["readback"]},
                {"speaker": "USER", "text": "yes please"},
            ]
            assert (await client.post(path, json=body)).status_code == 204
            with memory.sessions() as session, session.begin():
                ended = session.get(ConversationSession, first)
                assert ended is not None
                ended.ended_at = datetime.now(UTC)
            for mode in ("VOICE", "TEXT"):
                returning = conversation(memory, owner, input_mode=mode)
                context = await client.post(
                    f"/conversation-sessions/{returning}/memory/context"
                )
                assert context.status_code == 200
                assert "morning appointments" in context.json()["summary"]
                assert "weekday appointments" in context.json()["summary"]
                assert (
                    len(context.json()["summary"])
                    <= memory.settings.customer_memory_context_characters
                )
            save_control(memory, owner, "AFTERNOON")
            assert "afternoon appointments" in str(
                memory.view(owner, context_only=True)["summary"]
            )
            memory.remove_fact(
                owner,
                "appointment_time",
                MemoryMutation(
                    expected_revision=revision(memory, owner),
                    request_id=uuid4(),
                ),
                uuid4(),
            )
            assert "afternoon appointments" not in str(
                memory.view(owner, context_only=True)["summary"]
            )
            memory.set_consent(
                owner,
                MemoryMutation(
                    expected_revision=revision(memory, owner),
                    request_id=uuid4(),
                ),
                None,
                uuid4(),
            )
            cleared = memory.view(owner)
            assert cleared["enabled"] is False
            assert cleared["facts"] == cleared["sources"] == []
            assert memory.view(owner, context_only=True)["summary"] == ""
            with pytest.raises(ApiError):
                save_control(memory, owner)
            with memory.sessions() as session:
                assert session.get(ConversationIntake, intake_id) is not None

    asyncio.run(exercise())


def test_disable_rejects_writes_and_retrieval_until_fresh_consent(
    harness: MemoryHarness,
) -> None:
    memory, owner = harness.memory, harness.owner
    enable(memory, owner)
    stale = conversation(memory, owner)
    save_control(memory, owner)
    memory.set_consent(
        owner,
        MemoryConsentInput(
            expected_revision=revision(memory, owner),
            request_id=uuid4(),
            enabled=False,
            explicit_confirmation=True,
        ),
        False,
        uuid4(),
    )
    assert memory.view(owner)["facts"] == []
    with pytest.raises(ApiError):
        save_control(memory, owner)
    enable(memory, owner)
    with pytest.raises(ApiError):
        memory.view(owner, context_only=True, browser_session_id=stale)
    assert (
        memory.view(
            owner, context_only=True, browser_session_id=conversation(memory, owner)
        )["summary"]
        == ""
    )


def test_expired_source_cannot_refresh_old_facts(harness: MemoryHarness) -> None:
    memory, owner = harness.memory, harness.owner
    enable(memory, owner)
    session_id = conversation(memory, owner)
    intake_id = authorized_intake(
        memory,
        owner,
        session_id,
        confirmed_at=datetime.now(UTC) - timedelta(days=100),
    )
    facts = [MemoryFactInput(key="equipment_type", value="FURNACE")]
    with pytest.raises(ApiError):
        memory.prepare(owner, session_id, facts)
    with pytest.raises(ApiError):
        memory.save(
            owner,
            MemoryFactSaveInput(
                expected_revision=revision(memory, owner),
                request_id=uuid4(),
                facts=facts,
                source_intake_id=intake_id,
                explicit_confirmation=True,
            ),
            uuid4(),
        )
    assert memory.view(owner)["sources"] == []


@pytest.fixture
def committed_memory(
    migrated_database: Engine, database_settings: DatabaseSettings
) -> Iterator[tuple[CustomerMemoryService, ActorContext]]:
    sessions = sessionmaker(bind=migrated_database, expire_on_commit=False)
    with sessions() as session, session.begin():
        agency = Agency(
            name="Disposable memory HVAC",
            slug=f"memory-{uuid4()}",
            environment_kind="DEVELOPMENT",
        )
        user = AppUser(auth_subject=uuid4(), display_name="Fictional customer")
        session.add_all([agency, user])
        session.flush()
        account = CustomerAccount(
            agency_id=agency.id,
            app_user_id=user.id,
            email=f"memory-{uuid4()}@example.test",
            password_hash="synthetic-not-a-login-hash",
            created_at=datetime.now(UTC),
        )
        session.add(account)
        session.flush()
        actor = ActorContext(
            app_user_id=user.id,
            agency_id=agency.id,
            display_name=user.display_name,
            agency_name=agency.name,
            agency_environment="DEVELOPMENT",
        )
    settings = ApiSettings(
        _env_file=None,
        app_environment="development",
        api_host="127.0.0.1",
        api_port=8000,
        database_url=database_settings.runtime_database_url,
        database_ssl_mode=database_settings.database_ssl_mode,
        customer_memory_enabled=True,
    )
    try:
        yield CustomerMemoryService(sessions, settings), actor
    finally:
        with sessions() as session, session.begin():
            for model in (CustomerMemoryFact, CustomerMemoryPolicy):
                session.execute(delete(model).where(model.account_id == account.id))
            session.execute(delete(AuditEvent).where(AuditEvent.agency_id == agency.id))
            session.execute(
                delete(ConversationSession).where(
                    ConversationSession.agency_id == agency.id
                )
            )
            session.delete(session.get(CustomerAccount, account.id))
            session.delete(session.get(AppUser, user.id))
            session.flush()
            session.delete(session.get(Agency, agency.id))


def test_committed_memory_survives_new_service_and_database_connections(
    committed_memory: tuple[CustomerMemoryService, ActorContext],
    database_settings: DatabaseSettings,
) -> None:
    memory, owner = committed_memory
    enable(memory, owner)
    save_control(memory, owner, "MORNING")
    restarted_process = subprocess.run(
        [
            sys.executable,
            "-c",
            """
import sys
from uuid import UUID
from sqlalchemy.orm import sessionmaker
from insurance_operations.actors import ActorContext
from insurance_operations.customer_memory.service import CustomerMemoryService
from insurance_operations.database.connection import create_database_engine
from insurance_operations.settings import ApiSettings, DatabaseSettings
database = DatabaseSettings()
settings = ApiSettings(
    _env_file=None, app_environment="development", api_host="127.0.0.1",
    api_port=8000, database_url=database.runtime_database_url,
    database_ssl_mode=database.database_ssl_mode, customer_memory_enabled=True,
)
engine = create_database_engine(settings, service_name="memory-process-test")
try:
    actor = ActorContext(
        app_user_id=UUID(sys.argv[1]), agency_id=UUID(sys.argv[2]),
        display_name="Synthetic", agency_name="Synthetic",
        agency_environment="DEVELOPMENT",
    )
    print(CustomerMemoryService(sessionmaker(bind=engine), settings).view(
        actor, context_only=True,
    )["summary"])
finally:
    engine.dispose()
""",
            str(owner.app_user_id),
            str(owner.agency_id),
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=15,
    )
    assert "morning appointments" in restarted_process.stdout
    for mode in ("VOICE", "TEXT"):
        engine = create_database_engine(
            database_settings, service_name="memory-restart-test"
        )
        try:
            restarted = CustomerMemoryService(
                sessionmaker(bind=engine), memory.settings
            )
            returning = conversation(restarted, owner, input_mode=mode)
            assert "morning appointments" in str(
                restarted.view(
                    owner,
                    context_only=True,
                    browser_session_id=returning,
                )["summary"]
            )
        finally:
            engine.dispose()


def test_concurrent_repeated_saves_are_idempotent_and_conflicts_do_not_overwrite(
    committed_memory: tuple[CustomerMemoryService, ActorContext],
) -> None:
    memory, owner = committed_memory
    enable(memory, owner)
    data = MemoryFactSaveInput(
        expected_revision=revision(memory, owner),
        request_id=uuid4(),
        facts=[MemoryFactInput(key="appointment_time", value="MORNING")],
        explicit_confirmation=True,
    )

    def race(first: MemoryFactSaveInput, second: MemoryFactSaveInput) -> list[str]:
        barrier = Barrier(2)

        def save(value: MemoryFactSaveInput) -> str:
            barrier.wait(timeout=5)
            try:
                memory.save(owner, value, uuid4())
                return "saved"
            except ApiError as error:
                return error.code

        with ThreadPoolExecutor(max_workers=2) as pool:
            return list(pool.map(save, (first, second)))

    assert race(data, data) == ["saved", "saved"]
    assert revision(memory, owner) == data.expected_revision + 1
    first = data.model_copy(
        update={"request_id": uuid4(), "expected_revision": revision(memory, owner)}
    )
    second = first.model_copy(
        update={
            "request_id": uuid4(),
            "facts": [MemoryFactInput(key="appointment_time", value="AFTERNOON")],
        }
    )
    assert sorted(race(first, second)) == ["MEMORY_CONFLICT", "saved"]
    with memory.sessions() as session:
        assert (
            session.scalar(
                select(func.count())
                .select_from(CustomerMemoryFact)
                .where(
                    CustomerMemoryFact.agency_id == owner.agency_id,
                )
            )
            == 1
        )
