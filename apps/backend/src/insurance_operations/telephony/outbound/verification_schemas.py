from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from insurance_operations.telephony.outbound.destinations import (
    normalize_phone_number,
)


class SmsStartInput(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    phone_number: str = Field(min_length=1, max_length=64, repr=False)
    sms_consent: Literal[True]
    sms_consent_version: Literal["outbound-sms-v1"]

    @field_validator("phone_number")
    @classmethod
    def normalize_destination(cls, value: str) -> str:
        return normalize_phone_number(value)

    @field_validator("sms_consent", mode="before")
    @classmethod
    def explicit_consent(cls, value: object) -> object:
        if value is not True:
            raise ValueError("Agree to receive one verification text")
        return value


class SmsVerifyInput(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    challenge_id: UUID
    code: str = Field(pattern=r"^[0-9]{6}$", repr=False)


class SmsChallengeResponse(BaseModel):
    challenge_id: UUID
    expires_at: datetime
    verified: bool
