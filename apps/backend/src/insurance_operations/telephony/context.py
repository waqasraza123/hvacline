from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PhoneCallContext(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    inbound_call_id: UUID
    conversation_id: str = Field(min_length=1, max_length=200)
