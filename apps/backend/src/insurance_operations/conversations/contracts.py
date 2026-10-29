from dataclasses import dataclass
from typing import Literal, Protocol

ConversationInputMode = Literal["VOICE", "TEXT"]
ConversationTransport = Literal["webrtc", "websocket"]


class ConversationProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class ProviderSessionMetadata:
    adapter: str
    adapter_version: str
    external_session_reference: str | None = None

    def as_storage_value(self) -> dict[str, object]:
        result: dict[str, object] = {
            "adapter": self.adapter,
            "adapter_version": self.adapter_version,
        }
        if self.external_session_reference is not None:
            result["external_session_reference"] = self.external_session_reference
        return result


@dataclass(frozen=True)
class ConnectionGrant:
    transport: ConversationTransport
    credential: str
    metadata: ProviderSessionMetadata
    provider: Literal["elevenlabs", "local"] = "elevenlabs"
    websocket_path: str | None = None


class ConversationProvider(Protocol):
    def authorize_session(
        self, *, input_mode: ConversationInputMode = "VOICE"
    ) -> ConnectionGrant: ...

    def close(self) -> None: ...
