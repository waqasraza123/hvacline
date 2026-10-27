from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from insurance_operations.conversations.schemas import ConversationTurn

FACT_OPTIONS: dict[str, dict[str, str]] = {
    "appointment_time": {
        "MORNING": "morning appointments",
        "AFTERNOON": "afternoon appointments",
    },
    "appointment_days": {
        "WEEKDAYS": "weekday appointments",
        "WEEKENDS": "weekend appointments",
    },
    "contact_preference": {"PHONE": "phone contact", "EMAIL": "email contact"},
    "equipment_type": {
        "CENTRAL_AC": "central air conditioning", "HEAT_PUMP": "heat pump",
        "FURNACE": "furnace", "BOILER": "boiler", "MINI_SPLIT": "mini split",
    },
    "equipment_brand": {
        name: name.title() for name in (
            "CARRIER", "TRANE", "LENNOX", "GOODMAN", "DAIKIN", "RHEEM",
            "MITSUBISHI", "YORK", "BRYANT", "AMANA",
        )
    },
    "equipment_fuel": {
        "ELECTRIC": "electric heating", "GAS": "gas heating", "OIL": "oil heating",
    },
    "arrival_preference": {"CALL_FIRST": "call before arrival"},
    "site_access": {"GATE": "gated access", "PETS": "pets on site"},
}


class MemoryFactInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(min_length=1, max_length=40)
    value: str = Field(min_length=1, max_length=40)

    @model_validator(mode="after")
    def permitted_fact(self) -> Self:
        if self.value not in FACT_OPTIONS.get(self.key, {}):
            raise ValueError("Choose an available memory field and value")
        return self


class MemoryMutation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_revision: int = Field(ge=0)
    request_id: UUID


class MemoryConsentInput(MemoryMutation):
    enabled: bool
    explicit_confirmation: Literal[True]


class MemoryFactSaveInput(MemoryMutation):
    facts: list[MemoryFactInput] = Field(min_length=1, max_length=8)
    source_intake_id: UUID | None = None
    explicit_confirmation: Literal[True]

    @model_validator(mode="after")
    def unique_keys(self) -> Self:
        if len({fact.key for fact in self.facts}) != len(self.facts):
            raise ValueError("Each memory field may appear only once")
        return self


class MemoryReadbackInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    facts: list[MemoryFactInput] = Field(min_length=1, max_length=8)


class MemorySpokenSaveInput(MemoryFactSaveInput):
    transcript: list[ConversationTurn] = Field(default_factory=list, max_length=60)
    provider_history: str | None = Field(default=None, max_length=65_536)


class MemoryPairInput(MemoryMutation):
    code: str = Field(pattern=r"^HVACMEM-[A-Za-z0-9_-]{32}$")
    explicit_confirmation: Literal[True]


def fact_label(fact: MemoryFactInput) -> str:
    return f"{fact.key.replace('_', ' ')}: {FACT_OPTIONS[fact.key][fact.value]}"


def memory_readback(facts: list[MemoryFactInput]) -> str:
    details = "; ".join(fact_label(fact) for fact in facts)
    return (
        f"May I remember these optional details for future conversations: {details}? "
        "You can view, correct or delete them in Memory settings. "
        "Reply yes to remember these details, or tell me what to correct."
    )
