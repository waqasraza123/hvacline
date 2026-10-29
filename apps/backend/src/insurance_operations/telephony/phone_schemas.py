from enum import StrEnum
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from insurance_operations.approved_faqs.schemas import ApprovedFaqLookupResponse
from insurance_operations.conversations.schemas import ConversationTurn
from insurance_operations.customers import CustomerInput
from insurance_operations.database.models.lead import LeadUrgency
from insurance_operations.telephony.context import PhoneCallContext as PhoneCallContext
from insurance_operations.telephony.schemas import CallAction


class PhoneConsentInput(PhoneCallContext):
    ai_disclosure_accepted: bool
    microphone_consent_granted: bool
    call_id: str | None = Field(default=None, min_length=1, max_length=200)

    @model_validator(mode="after")
    def require_all_consent(self) -> Self:
        if not all(
            (
                self.ai_disclosure_accepted,
                self.microphone_consent_granted,
            )
        ):
            raise ValueError("all phone consent acknowledgements are required")
        return self


class PhoneConsentResponse(BaseModel):
    conversation_session_id: UUID
    accepted: bool
    maximum_duration_seconds: int


class PhoneFaqLookupInput(PhoneCallContext):
    query: str = Field(min_length=1, max_length=2_000)


class PhoneFaqLookupResponse(ApprovedFaqLookupResponse):
    pass


class PhoneIntakeConfirmationInput(PhoneCallContext):
    customer: CustomerInput
    intake_intent: str = Field(min_length=1, max_length=2_000)
    urgency: LeadUrgency = LeadUrgency.NORMAL
    explicit_verbal_confirmation: bool

    @model_validator(mode="after")
    def require_confirmation_and_contact(self) -> Self:
        if not self.explicit_verbal_confirmation:
            raise ValueError("explicit verbal confirmation is required")
        if self.customer.email is None and self.customer.phone is None:
            raise ValueError("customer email or phone is required")
        return self


class PhoneIntakeConfirmationResponse(BaseModel):
    conversation_session_id: UUID
    confirmation_recorded: bool
    replayed: bool = False


class PhoneHandoffKind(StrEnum):
    LIVE_TRANSFER = "LIVE_TRANSFER"
    CALLBACK = "CALLBACK"


class PhoneHandoffInput(PhoneCallContext):
    kind: PhoneHandoffKind


class PhoneHandoffResponse(BaseModel):
    action: CallAction
    message: str | None = None
    replayed: bool = False


class NormalizedPostCall(BaseModel):
    event_type: str
    event_timestamp: int = Field(ge=0, le=253_402_300_799)
    inbound_call_id: UUID | None = None
    source_call_reference: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )
    source_adapter_name: Literal["twilio", "telnyx_sip"] = "twilio"
    conversation_id: str = Field(min_length=1, max_length=200)
    transcript: list[ConversationTurn] = Field(default_factory=list, max_length=60)

    @model_validator(mode="after")
    def validate_transcript(self) -> Self:
        if self.event_type == "post_call_transcription":
            if self.inbound_call_id is None or self.source_call_reference is not None:
                raise ValueError("transcription webhook requires the inbound call id")
            if sum(len(turn.text) for turn in self.transcript) > 30_000:
                raise ValueError("confirmed phone transcript is too large")
        elif self.source_call_reference is None or self.inbound_call_id is not None:
            raise ValueError("initiation failure webhook requires the provider call id")
        return self
