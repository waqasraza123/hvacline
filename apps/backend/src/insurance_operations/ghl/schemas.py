from typing import Annotated, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)

GhlId = Annotated[str, Field(pattern=r"^[a-zA-Z0-9_-]{1,128}$")]
Outcome = Literal["new", "booked", "cancelled", "attention"]


class StrictInput(BaseModel):
    model_config = ConfigDict(
        extra="forbid", str_strip_whitespace=True, hide_input_in_errors=True
    )


class CredentialInput(StrictInput):
    location_id: GhlId
    token: SecretStr

    @field_validator("token")
    @classmethod
    def valid_token(cls, value: SecretStr) -> SecretStr:
        token = value.get_secret_value()
        if not 16 <= len(token) <= 4096 or any(
            not 33 <= ord(char) <= 126 for char in token
        ):
            raise ValueError("Enter a valid private integration token.")
        return value


class StageMapping(StrictInput):
    new: GhlId
    booked: GhlId
    cancelled: GhlId
    attention: GhlId

    @model_validator(mode="after")
    def distinct(self) -> Self:
        if len(set(self.model_dump().values())) != 4:
            raise ValueError("Select four different pipeline stages.")
        return self


class FieldMapping(StrictInput):
    reference: GhlId
    summary: GhlId
    booking: GhlId

    @model_validator(mode="after")
    def distinct(self) -> Self:
        if len(set(self.model_dump().values())) != 3:
            raise ValueError("Select three different opportunity fields.")
        return self


class ConnectionInput(CredentialInput):
    pipeline_id: GhlId
    stages: StageMapping
    fields: FieldMapping
    multiple_opportunities_confirmed: Literal[True]


class ConnectionAction(StrictInput):
    action: Literal["pause", "resume", "disconnect"]


class RetryInput(StrictInput):
    remote_opportunity_id: GhlId | None = None
    confirm_remote_absent: bool = False
    remote_note_id: GhlId | None = None
    confirm_note_absent: bool = False

    @model_validator(mode="after")
    def one_recovery(self) -> Self:
        if self.remote_opportunity_id and self.confirm_remote_absent:
            raise ValueError("Choose an existing opportunity or confirm absence.")
        if self.remote_note_id and self.confirm_note_absent:
            raise ValueError("Choose an existing note or confirm its absence.")
        return self


class CalendarRoute(StrictInput):
    team_key: str = Field(pattern=r"^[a-z0-9-]{1,40}$")
    calendar_id: GhlId


class VoiceConfiguration(StrictInput):
    calendars: list[CalendarRoute] = Field(default_factory=list, max_length=50)
    contact_notes: bool = False
    note_user_id: GhlId | None = None

    @model_validator(mode="after")
    def valid_routes(self) -> Self:
        if len({row.team_key for row in self.calendars}) != len(self.calendars):
            raise ValueError("Each team can have only one GHL calendar.")
        if len({row.calendar_id for row in self.calendars}) != len(self.calendars):
            raise ValueError("Use a separate GHL calendar for each team.")
        if self.contact_notes and self.note_user_id is None:
            raise ValueError("A GHL user ID is required for contact summaries.")
        return self


class VoiceConfigurationInput(VoiceConfiguration):
    expected_version: int = Field(ge=0)


class BookingRecoveryInput(StrictInput):
    remote_event_id: GhlId | None = None
    confirm_remote_absent: bool = False

    @model_validator(mode="after")
    def one_action(self) -> Self:
        if bool(self.remote_event_id) == self.confirm_remote_absent:
            raise ValueError("Link an existing appointment or confirm its absence.")
        return self
