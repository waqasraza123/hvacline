from datetime import datetime, time
from enum import StrEnum
from typing import Literal, Self
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator
from insurance_operations.hvac.schemas import AppointmentView


class RecoveryStatus(StrEnum):
    PENDING = "PENDING"
    READY = "READY"
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    AWAITING_RESPONSE = "AWAITING_RESPONSE"
    RECOVERED = "RECOVERED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    SUPPRESSED = "SUPPRESSED"
    CLOSED = "CLOSED"


class StrictInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class PolicyInput(StrictInput):
    expected_row_version: int = Field(ge=0)
    enabled: bool = False
    channels: list[Literal["SMS", "VOICE"]] = Field(default_factory=list, max_length=2)
    timezone: str = "America/New_York"
    contact_start: time = time(9)
    contact_end: time = time(18)
    max_attempts: int = Field(default=2, ge=1, le=2)
    interval_hours: int = Field(default=24, ge=24, le=168)
    expiry_days: int = Field(default=7, ge=1, le=7)
    abandoned_delay_minutes: int = Field(default=10, ge=10, le=1440)
    booking_delay_minutes: int = Field(default=30, ge=30, le=1440)

    @model_validator(mode="after")
    def valid(self) -> Self:
        try:
            ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError, ValueError) as error:
            raise ValueError("A valid agency IANA timezone is required") from error
        if self.contact_start.tzinfo or self.contact_end.tzinfo or self.contact_start >= self.contact_end:
            raise ValueError("Contact windows must start and end on the same local day")
        if self.contact_start < time(9) or self.contact_end > time(18):
            raise ValueError("Contact windows must stay within 09:00–18:00 local time")
        if len(set(self.channels)) != len(self.channels):
            raise ValueError("Choose distinct channels")
        return self


class CaseAction(StrictInput):
    expected_row_version: int = Field(ge=1)
    action: Literal["PAUSE", "RESUME", "RETRY", "ASSIGN", "CLOSE"]
    assigned_to: UUID | None = None


class PermissionInput(StrictInput):
    expected_row_version: int = Field(ge=0)
    channel: Literal["SMS", "VOICE", "ALL"]
    granted: bool
    source: Literal["SIGNED_FORM", "RECORDED_EXPLICIT_PERMISSION", "CUSTOMER_REVOCATION"]
    evidence_reference: str = Field(pattern=r"^[A-Za-z0-9_.:-]{1,128}$")
    observed_at: AwareDatetime

    @model_validator(mode="after")
    def explicit_only(self) -> Self:
        if self.granted and (self.channel == "ALL" or self.source == "CUSTOMER_REVOCATION"):
            raise ValueError("Permission must explicitly name SMS or AI voice recovery")
        return self


class AiInput(StrictInput):
    expected_row_version: int = Field(ge=0)
    provider: Literal["OPENAI", "OPENAI_COMPATIBLE"]
    model: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_./:-]{0,127}$")
    endpoint: str = Field(default="https://api.openai.com/v1", max_length=255)
    api_key: SecretStr | None = None

    @field_validator("api_key")
    @classmethod
    def key_valid(cls, value: SecretStr | None) -> SecretStr | None:
        if value is not None and (not 8 <= len(value.get_secret_value()) <= 4096 or any(not 33 <= ord(c) <= 126 for c in value.get_secret_value())):
            raise ValueError("Enter a valid API credential")
        return value


class VersionInput(StrictInput):
    expected_row_version: int = Field(ge=1)


class OutcomeInput(StrictInput):
    expected_row_version: int = Field(ge=1)
    provider_reference: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]{1,200}$")
    carrier_ended_confirmed: bool = Field(default=False, strict=True)
    grant_id: UUID | None = None


class ContinuationView(BaseModel):
    id: UUID
    attempt_id: UUID
    channel: str
    status: str
    expires_at: datetime
    reply_status: str | None
    failure_code: str | None


class AttemptView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    channel: str
    attempt_number: int
    status: str
    scheduled_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    failure_code: str | None


class CaseView(BaseModel):
    id: UUID
    row_version: int
    service_request_id: UUID
    inbound_call_id: UUID | None
    conversation_session_id: UUID | None
    lead_id: UUID | None
    customer: str
    summary: str
    source_type: str
    source_reference: UUID
    status: RecoveryStatus
    eligible_at: datetime
    last_activity_at: datetime
    recovered_appointment_id: UUID | None
    booking: AppointmentView | None
    paused: bool
    assigned_to: UUID | None
    reason: str | None
    next_attempt: datetime | None
    attempts: list[AttemptView]
    continuations: list[ContinuationView] = Field(default_factory=list)
    permissions: list[dict[str, object]]
