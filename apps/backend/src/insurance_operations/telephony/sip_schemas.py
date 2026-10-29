from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from insurance_operations.telephony.schemas import validate_e164

SipHeaderName = Annotated[str, StringConstraints(min_length=1, max_length=100)]
SipHeaderValue = Annotated[str, StringConstraints(max_length=1000)]


class SipConversationInitiation(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    caller_id: str = Field(min_length=1, max_length=200)
    called_number: str = Field(min_length=8, max_length=16)
    agent_id: str = Field(min_length=1, max_length=200)
    call_sid: str = Field(default="", max_length=200)
    conversation_id: str = Field(min_length=1, max_length=180)
    call_id: str | None = Field(default=None, max_length=200)
    sip_headers: dict[SipHeaderName, SipHeaderValue] | None = Field(
        default=None, max_length=40
    )

    @field_validator("called_number")
    @classmethod
    def validate_called_number(cls, value: str) -> str:
        return validate_e164(value)

    @field_validator("caller_id", "agent_id", "conversation_id", "call_sid")
    @classmethod
    def validate_identifier(cls, value: str) -> str:
        if any(ord(character) < 32 or ord(character) == 127 for character in value):
            raise ValueError("phone identifier contains control characters")
        return value

    @field_validator("call_id")
    @classmethod
    def normalize_call_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if any(ord(character) < 32 or ord(character) == 127 for character in value):
            raise ValueError("SIP call ID contains control characters")
        return value or None


class PhoneDynamicVariables(BaseModel):
    phone_inbound_call_id: str
    phone_max_duration_seconds: int


class PhoneInitiationResponse(BaseModel):
    type: Literal["conversation_initiation_client_data"] = (
        "conversation_initiation_client_data"
    )
    dynamic_variables: PhoneDynamicVariables
