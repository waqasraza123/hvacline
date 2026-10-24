from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr, field_validator


class LoginInput(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    email: EmailStr = Field(max_length=254)
    password: SecretStr = Field(min_length=1, max_length=128)


class SignupInput(LoginInput):
    full_name: str = Field(min_length=1, max_length=160)
    password: SecretStr = Field(min_length=15, max_length=128)
    fictional_data_acknowledged: bool

    @field_validator("full_name")
    @classmethod
    def normalized_name(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("Please enter your name")
        return value


class AccountView(BaseModel):
    id: UUID
    full_name: str
    email: str


class LoginResponse(BaseModel):
    user: AccountView
    session_token: str
    expires_in: int
