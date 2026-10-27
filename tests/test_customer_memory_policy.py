from uuid import uuid4

import pytest
from pydantic import ValidationError

from insurance_operations.conversations.schemas import ConversationTurn
from insurance_operations.conversations.spoken import require_spoken_confirmation
from insurance_operations.customer_memory.schemas import MemoryFactInput, memory_readback
from insurance_operations.customer_memory.service import supported_facts
from insurance_operations.database.models.conversation import ConversationIntake


def test_memory_rejects_secrets_free_text_and_live_business_claims() -> None:
    for key, value in (
        ("password", "never-store-this"), ("appointment_time", "arbitrary narrative"),
        ("booking_status", "CONFIRMED"), ("price", "100"),
        ("equipment_brand", "unrecognized-free-text"),
    ):
        with pytest.raises(ValidationError):
            MemoryFactInput(key=key, value=value)


def test_only_user_evidence_creates_suggestions_and_ambiguity_is_not_resolved_by_ai() -> None:
    source = ConversationIntake(
        id=uuid4(), confirmed_transcript=[
            {"speaker": "AGENT", "text": "You prefer morning appointments."},
            {"speaker": "USER", "text": "My furnace needs attention."},
        ],
    )
    assert supported_facts(source) == [MemoryFactInput(key="equipment_type", value="FURNACE")]
    source.confirmed_transcript = [{
        "speaker": "USER", "text": "Morning appointments or afternoon appointments, I am unsure.",
    }]
    assert supported_facts(source) == []


def test_memory_has_its_own_readback_and_needs_a_fresh_explicit_answer() -> None:
    facts = [MemoryFactInput(key="equipment_type", value="HEAT_PUMP")]
    readback = memory_readback(facts)
    turns = [ConversationTurn(speaker="AGENT", text=readback),
             ConversationTurn(speaker="USER", text="yes")]
    require_spoken_confirmation(turns, readback, "remember these details")
    for answer in ("no", "maybe", "yes but that is wrong"):
        with pytest.raises(ValueError):
            require_spoken_confirmation(
                [turns[0], ConversationTurn(speaker="USER", text=answer)], readback,
                "remember these details",
            )
