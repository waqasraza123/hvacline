from uuid import uuid4

import pytest
from pydantic import ValidationError

from insurance_operations.conversations.schemas import ConversationTurn
from insurance_operations.conversations.spoken import require_spoken_confirmation
from insurance_operations.customer_memory.schemas import (
    MemoryFactInput,
    memory_readback,
)
from insurance_operations.customer_memory.service import supported_facts
from insurance_operations.database.models.conversation import ConversationIntake


def test_memory_rejects_secrets_free_text_and_live_business_claims() -> None:
    for key, value in (
        ("password", "never-store-this"),
        ("appointment_time", "arbitrary narrative"),
        ("booking_status", "CONFIRMED"),
        ("price", "100"),
        ("equipment_brand", "unrecognized-free-text"),
    ):
        with pytest.raises(ValidationError):
            MemoryFactInput(key=key, value=value)


def test_only_customer_evidence_creates_unambiguous_suggestions() -> None:
    source = ConversationIntake(
        id=uuid4(),
        confirmed_transcript=[
            {"speaker": "AGENT", "text": "You prefer morning appointments."},
            {"speaker": "USER", "text": "My furnace needs attention."},
        ],
    )
    assert supported_facts(source) == [
        MemoryFactInput(key="equipment_type", value="FURNACE")
    ]
    source.confirmed_transcript = [
        {
            "speaker": "USER",
            "text": "Morning appointments or afternoon appointments, I am unsure.",
        }
    ]
    assert supported_facts(source) == []


def test_memory_has_its_own_readback_and_needs_a_fresh_explicit_answer() -> None:
    facts = [MemoryFactInput(key="equipment_type", value="HEAT_PUMP")]
    readback = memory_readback(facts)
    turns = [
        ConversationTurn(speaker="AGENT", text=readback),
        ConversationTurn(speaker="USER", text="yes"),
    ]
    require_spoken_confirmation(turns, readback, "remember these details")
    for answer in ("no", "maybe", "yes but that is wrong"):
        with pytest.raises(ValueError):
            require_spoken_confirmation(
                [turns[0], ConversationTurn(speaker="USER", text=answer)],
                readback,
                "remember these details",
            )


def test_weekday_mornings_are_supported_without_ai_inference() -> None:
    source = ConversationIntake(
        id=uuid4(),
        confirmed_transcript=[
            {"speaker": "USER", "text": "I prefer weekday mornings for appointments."},
        ],
    )
    assert supported_facts(source) == [
        MemoryFactInput(key="appointment_time", value="MORNING"),
        MemoryFactInput(key="appointment_days", value="WEEKDAYS"),
    ]


@pytest.mark.parametrize(
    "text",
    [
        "I do not want morning appointments.",
        "Maybe weekday mornings.",
        "Do you have a furnace?",
        "I used to prefer morning appointments.",
    ],
)
def test_negative_uncertain_or_questioned_details_are_not_suggested(text: str) -> None:
    source = ConversationIntake(
        id=uuid4(),
        confirmed_transcript=[
            {"speaker": "USER", "text": text},
        ],
    )
    assert supported_facts(source) == []


def test_later_negative_evidence_blocks_an_earlier_positive_suggestion() -> None:
    source = ConversationIntake(
        id=uuid4(),
        confirmed_transcript=[
            {"speaker": "USER", "text": "I prefer morning appointments."},
            {
                "speaker": "USER",
                "text": "Actually I do not prefer morning appointments.",
            },
        ],
    )
    assert supported_facts(source) == []


def test_separate_user_turns_cannot_be_joined_into_equipment_evidence() -> None:
    source = ConversationIntake(
        id=uuid4(),
        confirmed_transcript=[
            {"speaker": "USER", "text": "I need some heat."},
            {"speaker": "USER", "text": "Pump the brakes."},
        ],
    )
    assert supported_facts(source) == []


def test_location_cannot_be_inferred_to_be_an_equipment_brand() -> None:
    source = ConversationIntake(id=uuid4(), confirmed_transcript=[
        {"speaker": "USER", "text": "I live in New York."},
    ])
    assert supported_facts(source) == []


def test_brand_requires_an_explicit_equipment_or_brand_statement() -> None:
    source = ConversationIntake(id=uuid4(), confirmed_transcript=[
        {"speaker": "USER", "text": "My Trane furnace needs service."},
    ])
    assert supported_facts(source) == [
        MemoryFactInput(key="equipment_type", value="FURNACE"),
        MemoryFactInput(key="equipment_brand", value="TRANE"),
    ]
