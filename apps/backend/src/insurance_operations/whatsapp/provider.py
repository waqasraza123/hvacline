import hashlib
import hmac
import json
import time
from collections.abc import Callable, Mapping
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from insurance_operations.conversations.contracts import (
    ConnectionGrant,
    ConversationInputMode,
    ConversationProviderError,
)
from insurance_operations.conversations.schemas import ConversationTurn
from insurance_operations.errors import ApiError
from insurance_operations.telephony.contracts import TelephonyAdapterError
from insurance_operations.telephony.providers.elevenlabs import (
    MAX_WEBHOOK_BYTES,
    WEBHOOK_TOLERANCE_SECONDS,
    header_value,
    parse_signature,
)


class WhatsAppInitiation(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    caller_id: str = Field(min_length=1, max_length=200)
    called_number: str = Field(min_length=1, max_length=200)
    agent_id: str = Field(min_length=1, max_length=200)
    call_sid: Literal[""]
    conversation_id: str = Field(min_length=1, max_length=200)


class PostCallData(BaseModel):
    agent_id: str = Field(min_length=1, max_length=200)
    conversation_id: str = Field(min_length=1, max_length=200)


class WhatsAppPostCall(BaseModel):
    type: Literal["post_call_transcription", "call_initiation_failure"]
    event_timestamp: int = Field(ge=0)
    data: PostCallData


class HistoryEntry(BaseModel):
    role: Literal["user", "agent", "tool"]
    message: str | None = Field(default=None, max_length=2000)


class ProviderHistory(BaseModel):
    entries: list[HistoryEntry] = Field(max_length=180)


def spoken_history(value: str | None) -> list[ConversationTurn]:
    try:
        if value is None:
            raise ValueError("missing history")
        history = ProviderHistory.model_validate_json(value)
        turns = [
            ConversationTurn(
                speaker="USER" if entry.role == "user" else "AGENT", text=entry.message
            )
            for entry in history.entries
            if entry.role != "tool" and entry.message and entry.message.strip()
        ]
        if len(turns) > 60 or sum(len(turn.text) for turn in turns) > 30_000:
            raise ValueError("history exceeds consent bounds")
        return turns
    except (ValueError, ValidationError) as error:
        raise ApiError(
            status_code=422,
            code="WHATSAPP_HISTORY_REQUIRED",
            message=(
                "Supply the provider conversation history "
                "using a system dynamic variable"
            ),
        ) from error


def rejected() -> ApiError:
    return ApiError(
        status_code=401,
        code="WHATSAPP_AUTHENTICATION_FAILED",
        message="The WhatsApp request could not be authenticated",
    )


class ElevenLabsWhatsAppAdapter:
    def __init__(
        self,
        *,
        agent_id: str,
        number_id: str,
        init_secret: str,
        tool_secret: str,
        session_secret: str,
        post_call_secret: str,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.agent_id = agent_id
        self.number_id = number_id
        self._init_secret = init_secret
        self._tool_secret = tool_secret
        self._session_secret = session_secret.encode()
        self._post_call_secret = post_call_secret.encode()
        self._clock = clock

    def verify_initialization(
        self, authorization: str | None, data: WhatsAppInitiation
    ) -> None:
        if (
            not hmac.compare_digest(
                (authorization or "").encode(), f"Bearer {self._init_secret}".encode()
            )
            or data.agent_id != self.agent_id
            or data.called_number != self.number_id
        ):
            raise rejected()

    def caller_digest(self, caller_id: str) -> str:
        return hmac.new(
            self._session_secret, b"caller:" + caller_id.encode(), hashlib.sha256
        ).hexdigest()

    def session_token(self, binding_id: str, conversation_id: str) -> str:
        content = json.dumps(
            [binding_id, self.agent_id, self.number_id, conversation_id]
        ).encode()
        return hmac.new(self._session_secret, content, hashlib.sha256).hexdigest()

    def verify_tool(
        self,
        authorization: str | None,
        token: str | None,
        binding_id: str,
        conversation_id: str,
    ) -> None:
        if not hmac.compare_digest(
            (authorization or "").encode(), f"Bearer {self._tool_secret}".encode()
        ) or not hmac.compare_digest(
            (token or "").encode(),
            self.session_token(binding_id, conversation_id).encode(),
        ):
            raise rejected()

    def verify_post_call(
        self, headers: Mapping[str, str], body: bytes
    ) -> WhatsAppPostCall:
        try:
            if len(body) > MAX_WEBHOOK_BYTES:
                raise ValueError("oversized webhook")
            timestamp, signature = parse_signature(
                header_value(headers, "ElevenLabs-Signature") or ""
            )
            expected = hmac.new(
                self._post_call_secret,
                str(timestamp).encode() + b"." + body,
                hashlib.sha256,
            ).hexdigest()
            if abs(
                self._clock() - timestamp
            ) > WEBHOOK_TOLERANCE_SECONDS or not hmac.compare_digest(
                expected, signature
            ):
                raise ValueError("invalid signature")
            event = WhatsAppPostCall.model_validate_json(body)
            if event.data.agent_id != self.agent_id:
                raise ValueError("wrong agent")
            return event
        except (ValueError, ValidationError, TelephonyAdapterError) as error:
            raise rejected() from error

    def authorize_session(
        self, *, input_mode: ConversationInputMode = "VOICE"
    ) -> ConnectionGrant:
        raise ConversationProviderError(
            "WhatsApp calls are initialized by authenticated webhooks"
        )

    def close(self) -> None:
        return None
