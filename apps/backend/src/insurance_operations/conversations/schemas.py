from datetime import datetime
from enum import StrEnum
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from insurance_operations.conversations.contracts import (
    ConversationInputMode,
    ConversationTransport,
)
from insurance_operations.conversations.spoken import (
    intake_readback,
    require_spoken_confirmation,
)
from insurance_operations.customers import CustomerInput, CustomerView
from insurance_operations.database.models.lead import LeadUrgency
from insurance_operations.hvac.schemas import ServiceDetails, ServiceRequestInput


class ConversationSessionCreateInput(BaseModel):
    input_mode: ConversationInputMode = "VOICE"
    ai_disclosure_accepted: bool
    microphone_consent_granted: bool
    synthetic_data_acknowledged: bool


class ConversationConnection(BaseModel):
    transport: ConversationTransport
    credential: str


class ConversationSessionResponse(BaseModel):
    session_id: UUID
    input_mode: ConversationInputMode = "VOICE"
    connection: ConversationConnection
    maximum_duration_seconds: int
    authorization_expires_at: datetime | None = None
    confirmation_expires_at: datetime


class ConversationEndOutcome(StrEnum):
    COMPLETED = "COMPLETED"
    INTERRUPTED = "INTERRUPTED"
    FAILED = "FAILED"


class ConversationEndInput(BaseModel):
    outcome: ConversationEndOutcome


class ConversationEndResponse(BaseModel):
    session_id: UUID
    status: str
    review_available: bool
    confirmation_expires_at: datetime


class ConversationTurn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    speaker: Literal["USER", "AGENT"]
    text: str = Field(min_length=1, max_length=2_000)


class ConversationIntakeConfirmationInput(BaseModel):
    conversation_session_id: UUID
    customer: CustomerInput
    intake_intent: str = Field(min_length=1, max_length=2_000)
    service: ServiceDetails | None = None
    spoken_confirmation: bool = False
    urgency: LeadUrgency = LeadUrgency.NORMAL
    transcript: list[ConversationTurn] = Field(min_length=2, max_length=60)

    @model_validator(mode="after")
    def validate_confirmation(self) -> Self:
        if self.customer.email is None and self.customer.phone is None:
            raise ValueError("customer email or phone is required")
        speakers = {turn.speaker for turn in self.transcript}
        if speakers != {"USER", "AGENT"}:
            raise ValueError("transcript requires user and agent turns")
        if sum(len(turn.text) for turn in self.transcript) > 30_000:
            raise ValueError("transcript cannot exceed 30000 characters")
        if self.service is not None:
            service_request = ServiceRequestInput(
                customer=self.customer,
                service=self.service,
                explicit_confirmation=True,
            )
            if self.spoken_confirmation:
                if self.intake_intent.strip() != self.service.equipment_issue:
                    raise ValueError("The spoken request must match the readback issue")
                require_spoken_confirmation(
                    self.transcript, intake_readback(service_request)
                )
        elif self.spoken_confirmation:
            raise ValueError("Spoken confirmation requires complete HVAC details")
        return self


class ConversationIntakeResponse(BaseModel):
    conversation_intake_id: UUID
    conversation_session_id: UUID
    customer: CustomerView
    confirmed_at: datetime
    lead_id: UUID | None = None
    service_request_id: UUID | None = None
