import hashlib
import secrets

from insurance_operations.conversations.contracts import (
    ConnectionGrant,
    ConversationInputMode,
    ProviderSessionMetadata,
)

LOCAL_ADAPTER_VERSION = "1"
LOCAL_WEBSOCKET_PATH = "/api/v1/development/local-conversation"


class LocalConversationProvider:
    def authorize_session(
        self, *, input_mode: ConversationInputMode = "VOICE"
    ) -> ConnectionGrant:
        del input_mode
        credential = secrets.token_urlsafe(32)
        return ConnectionGrant(
            provider="local",
            transport="websocket",
            credential=credential,
            websocket_path=LOCAL_WEBSOCKET_PATH,
            metadata=ProviderSessionMetadata(
                adapter="local_browser_voice",
                adapter_version=LOCAL_ADAPTER_VERSION,
                external_session_reference=credential_digest(credential),
            ),
        )

    def close(self) -> None:
        return None


def credential_digest(credential: str) -> str:
    return hashlib.sha256(credential.encode()).hexdigest()
