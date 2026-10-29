from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class HomepageChatInput(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    message: str = Field(min_length=1, max_length=1000, repr=False)
    request_id: UUID
    ai_disclosure_accepted: Literal[True]

    @field_validator("message")
    @classmethod
    def meaningful_message(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Enter a message for Line")
        return value


class HomepageChatStatus(BaseModel):
    state: Literal["ready", "used", "busy"]
    remaining: Literal[0, 1]


class HomepageChatReply(BaseModel):
    reply: str = Field(min_length=1, max_length=4000, repr=False)
    remaining: Literal[0] = 0
