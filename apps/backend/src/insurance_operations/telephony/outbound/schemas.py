from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic_core import PydanticCustomError

from insurance_operations.telephony.outbound.destinations import normalize_phone_number


class DemoScenario(StrEnum):
    COOLING = "cooling"
    HEATING = "heating"
    MAINTENANCE = "maintenance"


class DemoCallStatus(StrEnum):
    RESERVED = "reserved"
    DIALING = "dialing"
    IN_PROGRESS = "in_progress"
    PROCESSING = "processing"
    UNKNOWN = "unknown"
    FAILED = "failed"
    REJECTED = "rejected"
    UNANSWERED = "unanswered"
    COMPLETED = "completed"
    DISCONNECTED = "disconnected"


TERMINAL_STATUSES = frozenset(
    {
        DemoCallStatus.FAILED,
        DemoCallStatus.REJECTED,
        DemoCallStatus.UNANSWERED,
        DemoCallStatus.COMPLETED,
        DemoCallStatus.DISCONNECTED,
    }
)


class DemoCallInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: UUID
    phone_number: str = Field(min_length=1, max_length=64)
    scenario: DemoScenario
    consent: Literal[True]
    consent_version: Literal["outbound-demo-v1"]

    @field_validator("phone_number")
    @classmethod
    def normalize_destination(cls, value: str) -> str:
        try:
            return normalize_phone_number(value)
        except ValueError as error:
            raise PydanticCustomError("phone_number_invalid", str(error)) from None

    @field_validator("consent", mode="before")
    @classmethod
    def explicit_consent(cls, value: object) -> object:
        if value is not True:
            raise ValueError("Explicit one-time AI call consent is required")
        return value


class DemoCallResponse(BaseModel):
    id: UUID
    status: DemoCallStatus
    transfer_status: Literal["not_requested", "refer_accepted", "failed", "unconfirmed"]
    created_at: datetime
    terminal: bool
    message: str


MESSAGES = {
    DemoCallStatus.RESERVED: "Your request is reserved. Do not submit another request.",
    DemoCallStatus.DIALING: "The call was requested. Your phone may ring shortly.",
    DemoCallStatus.IN_PROGRESS: "Your conversation with Line is in progress.",
    DemoCallStatus.PROCESSING: "The call has ended. Its final status is being processed.",
    DemoCallStatus.UNKNOWN: "The call outcome is unconfirmed. Do not request another call; contact the demo owner.",
    DemoCallStatus.FAILED: "The call could not be completed. No automatic redial will occur.",
    DemoCallStatus.REJECTED: "The call was declined or busy. No automatic redial will occur.",
    DemoCallStatus.UNANSWERED: "The call was not answered. No automatic redial will occur.",
    DemoCallStatus.COMPLETED: "The demo call ended. No appointment was booked.",
    DemoCallStatus.DISCONNECTED: "The call disconnected. No automatic redial will occur.",
}
