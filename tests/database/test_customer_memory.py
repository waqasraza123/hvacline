from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.actors import ActorContext
from insurance_operations.conversations.schemas import ConversationTurn
from insurance_operations.customer_memory.purge import purge_expired
from insurance_operations.customer_memory.schemas import (
    MemoryConsentInput, MemoryFactInput, MemoryFactSaveInput, MemoryMutation, MemoryPairInput,
)
from insurance_operations.customer_memory.service import CustomerMemoryService, redact_pairing_codes
from insurance_operations.customers import CustomerInput, customer_from_input
from insurance_operations.database.models.conversation import ConversationIntake, ConversationSession
from insurance_operations.database.models.customer_account import CustomerAccount
from insurance_operations.database.models.customer_memory import CustomerMemoryFact, CustomerMemorySummary
from insurance_operations.database.models.customer_mfa import CustomerMfaFactor
from insurance_operations.database.models.identity import Agency, AppUser
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
def harness(migrated_database: Engine, database_settings: DatabaseSettings) -> Iterator[MemoryHarness]:
    with migrated_database.connect() as connection:
        transaction = connection.begin()
        sessions = sessionmaker(
            bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint",
        )
        actors: list[ActorContext] = []
        with sessions() as session, session.begin():
            agency = Agency(name="Synthetic Memory HVAC", slug=f"memory-{uuid4()}", environment_kind="DEVELOPMENT")
            foreign = Agency(name="Separate HVAC", slug=f"memory-{uuid4()}", environment_kind="DEVELOPMENT")
            session.add_all([agency, foreign])
            session.flush()
            for business in (agency, agency, foreign):
                user = AppUser(auth_subject=uuid4(), display_name="Fictional memory customer")
                session.add(user)
                session.flush()
                account = CustomerAccount(
                    agency_id=business.id, app_user_id=user.id,
                    email=f"memory-{uuid4()}@example.test", password_hash="synthetic-not-a-login-hash",
                    created_at=datetime.now(UTC),
                )
                session.add(account)
                session.flush()
                session.add(CustomerMfaFactor(
                    account_id=account.id, agency_id=business.id, version=1,
                    secret_ciphertext="synthetic-service-fixture-not-an-encrypted-secret",
                    enabled_at=datetime.now(UTC), last_counter=1, failed_attempts=0,
                ))
                actors.append(ActorContext(
                    app_user_id=user.id, display_name=user.display_name,
                    agency_id=business.id, agency_name=business.name,
                    agency_environment="DEVELOPMENT",
                ))
        settings = ApiSettings(
            _env_file=None, app_environment="development", api_host="127.0.0.1", api_port=8000,
            database_url=database_settings.runtime_database_url,
            database_ssl_mode=database_settings.database_ssl_mode,
            customer_memory_enabled=True,
        )
        try:
            yield MemoryHarness(
                CustomerMemoryService(sessions, settings), actors[0], actors[1], actors[2]
            )
        finally:
            transaction.rollback()


def revision(memory: CustomerMemoryService, actor: ActorContext) -> int:
    value = memory.view(actor)["revision"]
    assert isinstance(value, int)
    return value


def enable(memory: CustomerMemoryService, actor: ActorContext) -> None:
    memory.set_consent(actor, MemoryConsentInput(
        expected_revision=revision(memory, actor), request_id=uuid4(),
        enabled=True, explicit_confirmation=True,
    ), True, uuid4())


def conversation(memory: CustomerMemoryService, actor: ActorContext, channel: str = "BROWSER") -> UUID:
    now = datetime.now(UTC)
    with memory.sessions() as session, session.begin():
        row = ConversationSession(
            agency_id=actor.agency_id, initiated_by=actor.app_user_id, channel=channel,
            input_mode="VOICE", status="AUTHORIZED", provider_metadata={},
            disclosure_accepted_at=now, microphone_consent_at=now,
            synthetic_data_acknowledged_at=now, maximum_duration_seconds=180,
            authorization_expires_at=now + timedelta(seconds=180),
            confirmation_expires_at=now + timedelta(minutes=30), authorized_at=now,
            created_at=now, updated_at=now,
        )
        session.add(row)
        session.flush()
        return row.id


def authorized_intake(memory: CustomerMemoryService, actor: ActorContext, session_id: UUID) -> UUID:
    with memory.sessions() as session, session.begin():
        customer = customer_from_input(CustomerInput(
            full_name="Fictional caller", email="fictional@example.test"
        ), actor)
        session.add(customer)
        session.flush()
        intake = ConversationIntake(
            agency_id=actor.agency_id, customer_id=customer.id,
            conversation_session_id=session_id, created_by=actor.app_user_id,
            intake_intent="Fictional equipment discussion", confirmed_at=datetime.now(UTC),
            confirmed_transcript=[
                {"speaker": "USER", "text": "My furnace needs service."},
                {"speaker": "AGENT", "text": "May I save this fictional request and transcript?"},
                {"speaker": "USER", "text": "yes"},
            ],
        )
        session.add(intake)
        session.flush()
        return intake.id


def save_control(memory: CustomerMemoryService, actor: ActorContext, value: str = "AFTERNOON") -> MemoryFactSaveInput:
    data = MemoryFactSaveInput(
        expected_revision=revision(memory, actor), request_id=uuid4(),
        facts=[MemoryFactInput(key="appointment_time", value=value)],
        explicit_confirmation=True,
    )
    memory.save(actor, data, uuid4())
    return data


def test_memory_recalls_across_sessions_without_cross_customer_or_tenant_leak(harness: MemoryHarness) -> None:
    memory, owner = harness.memory, harness.owner
    enable(memory, owner)
    saved = save_control(memory, owner)
    memory.save(owner, saved, uuid4())
    first, second = conversation(memory, owner), conversation(memory, owner)
    assert "afternoon appointments" in str(memory.view(owner, context_only=True, browser_session_id=first)["summary"])
    assert "afternoon appointments" in str(memory.view(owner, context_only=True, browser_session_id=second)["summary"])
    assert memory.view(harness.other)["facts"] == []
    assert memory.view(harness.foreign)["facts"] == []
    for actor in (harness.other, harness.foreign):
        with pytest.raises(ApiError):
            memory.view(actor, context_only=True, browser_session_id=first)
    with memory.sessions() as session:
        assert session.scalar(select(func.count()).select_from(CustomerMemoryFact)) == 1


def test_only_authorized_owned_sources_support_facts_and_transcripts_are_not_duplicated(harness: MemoryHarness) -> None:
    memory, owner = harness.memory, harness.owner
    enable(memory, owner)
    session_id = conversation(memory, owner)
    intake_id = authorized_intake(memory, owner, session_id)
    memory.save(owner, MemoryFactSaveInput(
        expected_revision=revision(memory, owner), request_id=uuid4(),
        facts=[MemoryFactInput(key="equipment_type", value="FURNACE")],
        source_intake_id=intake_id, explicit_confirmation=True,
    ), uuid4())
    assert "furnace" in str(memory.view(owner, context_only=True)["summary"])
    with memory.sessions() as session:
        assert session.scalar(select(func.count()).select_from(CustomerMemorySummary)) == 1
        assert session.scalar(select(func.count()).select_from(ConversationIntake).where(ConversationIntake.id == intake_id)) == 1
    memory.remove_fact(owner, "equipment_type", MemoryMutation(
        expected_revision=revision(memory, owner), request_id=uuid4(),
    ), uuid4())
    assert "furnace" not in str(memory.view(owner, context_only=True)["summary"])
    for actor in (harness.other, harness.foreign):
        with memory.sessions() as session, pytest.raises(ApiError):
            memory.source(session, memory.account(session, actor), intake_id)
    with pytest.raises(ApiError):
        memory.save(owner, MemoryFactSaveInput(
            expected_revision=revision(memory, owner), request_id=uuid4(),
            facts=[MemoryFactInput(key="equipment_type", value="HEAT_PUMP")],
            source_intake_id=intake_id, explicit_confirmation=True,
        ), uuid4())


def test_corrections_conflicts_erasure_and_retention_prevent_resurrection(harness: MemoryHarness) -> None:
    memory, owner = harness.memory, harness.owner
    enable(memory, owner)
    old = save_control(memory, owner)
    save_control(memory, owner, "MORNING")
    with pytest.raises(ApiError):
        memory.save(owner, old, uuid4())
    assert "morning appointments" in str(memory.view(owner, context_only=True)["summary"])
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
    memory.set_consent(owner, MemoryMutation(
        expected_revision=revision(memory, owner), request_id=uuid4(),
    ), None, uuid4())
    assert memory.view(owner)["facts"] == []
    with pytest.raises(ApiError):
        memory.view(owner, context_only=True, browser_session_id=stale)
    with pytest.raises(ApiError):
        memory.save(owner, old, uuid4())


def test_whatsapp_requires_browser_approved_link_and_unlink_revokes_current_tools(harness: MemoryHarness) -> None:
    memory, owner = harness.memory, harness.owner
    enable(memory, owner)
    save_control(memory, owner)
    call_session = conversation(memory, harness.other, "WHATSAPP")
    now = datetime.now(UTC)
    with memory.sessions() as session, session.begin():
        binding = WhatsAppConversation(
            agency_id=owner.agency_id, session_id=call_session,
            conversation_id=f"conv_{uuid4()}", phone_number_id="synthetic-business-id",
            caller_digest="a" * 64, initialized_at=now,
            expires_at=now + timedelta(seconds=180),
        )
        session.add(binding)
        session.flush()
        binding_id = binding.id
    assert memory.whatsapp_actor(binding_id) is None
    code = memory.begin_pairing(binding_id)
    enable(memory, harness.foreign)
    with pytest.raises(ApiError):
        memory.approve_pairing(harness.foreign, MemoryPairInput(
            expected_revision=revision(memory, harness.foreign), request_id=uuid4(),
            code=code, explicit_confirmation=True,
        ), code, uuid4())
    memory.approve_pairing(owner, MemoryPairInput(
        expected_revision=revision(memory, owner), request_id=uuid4(),
        code=code, explicit_confirmation=True,
    ), code, uuid4())
    linked = memory.whatsapp_actor(binding_id)
    assert linked is not None and linked.app_user_id == owner.app_user_id
    assert "afternoon appointments" in str(memory.view(
        linked, context_only=True, whatsapp_binding_id=binding_id
    )["summary"])
    sanitized = redact_pairing_codes([
        ConversationTurn(speaker="AGENT", text=f"Your linking code is {code}."),
    ])
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
            agency_id=owner.agency_id, session_id=second_session,
            conversation_id=f"conv_{uuid4()}", phone_number_id="synthetic-business-id",
            caller_digest="a" * 64, initialized_at=now,
            expires_at=now + timedelta(seconds=180),
        )
        session.add(returning)
        session.flush()
        returning_id = returning.id
    returning_actor = memory.whatsapp_actor(returning_id)
    assert returning_actor is not None and returning_actor.app_user_id == owner.app_user_id
    assert "afternoon appointments" in str(memory.view(
        returning_actor, context_only=True, whatsapp_binding_id=returning_id
    )["summary"])
    with memory.sessions() as session, session.begin():
        account = memory.account(session, owner)
        factor = session.get(CustomerMfaFactor, account.id)
        assert factor is not None
        factor.version += 1
    assert memory.view(owner)["whatsapp_linked"] is False
    assert memory.whatsapp_actor(returning_id) is None
    with pytest.raises(ApiError):
        memory.view(returning_actor, context_only=True, whatsapp_binding_id=returning_id)
    memory.unlink(owner, MemoryMutation(
        expected_revision=revision(memory, owner), request_id=uuid4(),
    ), uuid4())
    assert memory.whatsapp_actor(binding_id) is None
    with pytest.raises(ApiError):
        memory.view(returning_actor, context_only=True, whatsapp_binding_id=returning_id)


def test_customer_can_delete_optional_data_when_business_disables_memory(harness: MemoryHarness) -> None:
    memory, owner = harness.memory, harness.owner
    enable(memory, owner)
    save_control(memory, owner)
    memory.settings.customer_memory_enabled = False
    assert memory.view(owner)["available"] is False
    with pytest.raises(ApiError):
        memory.view(owner, context_only=True)
    memory.set_consent(owner, MemoryMutation(
        expected_revision=revision(memory, owner), request_id=uuid4(),
    ), None, uuid4())
    assert memory.view(owner)["facts"] == []


def test_increasing_business_retention_does_not_silently_increase_customer_cap(harness: MemoryHarness) -> None:
    memory, owner = harness.memory, harness.owner
    enable(memory, owner)
    save_control(memory, owner)
    memory.settings.customer_memory_retention_days = 1
    assert memory.view(owner)["retention_days"] == 1
    memory.settings.customer_memory_retention_days = 90
    assert memory.view(owner)["retention_days"] == 1
    memory.set_consent(owner, MemoryMutation(
        expected_revision=revision(memory, owner), request_id=uuid4(),
    ), None, uuid4())
    assert memory.view(owner)["retention_days"] == 90
    assert memory.view(owner)["facts"] == []
