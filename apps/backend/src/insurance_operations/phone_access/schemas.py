from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from insurance_operations.telephony.context import PhoneCallContext


class PhoneAccessContext(PhoneCallContext):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class PhoneAccessStart(PhoneAccessContext):
    explicit_request: Literal[True]


class AccessCodeInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    code: str = Field(pattern=r"^CALL-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}$")


class AccessApprovalInput(AccessCodeInput):
    access_id: UUID
    explicit_confirmation: Literal[True]
    share_memory: bool = False
