from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

WorkspaceRole = Literal["OWNER", "ADMIN", "STAFF"]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BusinessInput(Input):
    creation_key: UUID
    name: str = Field(min_length=1, max_length=160)
    slug: str = Field(min_length=3, max_length=63, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    owner_email: EmailStr

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Business name is required")
        return value.strip()


class InvitationInput(Input):
    email: EmailStr
    role: WorkspaceRole


class EnrollmentInput(Input):
    token: str = Field(pattern=r"^[A-Za-z0-9_-]{43}$")
    display_name: str = Field(min_length=1, max_length=160)
    password: str = Field(min_length=15, max_length=128)

    @field_validator("display_name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Staff name is required")
        return value.strip()


class AcceptInput(Input):
    token: str = Field(pattern=r"^[A-Za-z0-9_-]{43}$")


class EnrollmentConfirmation(AcceptInput):
    code: str = Field(pattern=r"^[0-9]{6}$")


class LoginInput(Input):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    code: str = Field(pattern=r"^[0-9]{6}$")


class VersionInput(Input):
    expected_row_version: int = Field(ge=1)


class MembershipInput(VersionInput):
    role: WorkspaceRole
    active: bool
