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

    @model_validator(mode="after")
    def one_recovery(self) -> Self:
        if self.remote_opportunity_id and self.confirm_remote_absent:
            raise ValueError("Choose an existing opportunity or confirm absence.")
        return self
