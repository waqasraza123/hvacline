from urllib.parse import urlsplit

import httpx
from pydantic import BaseModel, Field, ValidationError

from insurance_operations.conversations.contracts import (
    ConnectionGrant,
    ConversationInputMode,
    ConversationProviderError,
    ProviderSessionMetadata,
)

ELEVENLABS_API_BASE_URL = "https://api.elevenlabs.io"
ELEVENLABS_ADAPTER_VERSION = "1"


class ConversationTokenResponse(BaseModel):
    token: str = Field(min_length=1)
    conversation_id: str = Field(min_length=1, max_length=200)


class ConversationSignedUrlResponse(BaseModel):
    signed_url: str = Field(min_length=1, max_length=16000)
    conversation_id: str | None = Field(default=None, min_length=1, max_length=200)


class ElevenLabsConversationProvider:
    def __init__(
        self,
        *,
        api_key: str,
        agent_id: str,
        client: httpx.Client | None = None,
    ) -> None:
        self._api_key = api_key
        self._agent_id = agent_id
        self._client = client or httpx.Client(
            base_url=ELEVENLABS_API_BASE_URL,
            timeout=httpx.Timeout(10),
        )
        self._owns_client = client is None

    def authorize_session(
        self, *, input_mode: ConversationInputMode = "VOICE"
    ) -> ConnectionGrant:
        try:
            if input_mode == "TEXT":
                return self._authorize_text_session()
            response = self._client.get(
                "/v1/convai/conversation/token",
                params={"agent_id": self._agent_id},
                headers={"xi-api-key": self._api_key},
            )
            response.raise_for_status()
            token_response = ConversationTokenResponse.model_validate(response.json())
        except (httpx.HTTPError, ValidationError, ValueError) as error:
            raise ConversationProviderError(
                "conversation provider authorization failed"
            ) from error

        return ConnectionGrant(
            transport="webrtc",
            credential=token_response.token,
            metadata=ProviderSessionMetadata(
                adapter="elevenlabs_agents",
                adapter_version=ELEVENLABS_ADAPTER_VERSION,
                external_session_reference=token_response.conversation_id,
            ),
        )

    def _authorize_text_session(self) -> ConnectionGrant:
        response = self._client.get(
            "/v1/convai/conversation/get-signed-url",
            params={"agent_id": self._agent_id, "include_conversation_id": "true"},
            headers={"xi-api-key": self._api_key},
        )
        response.raise_for_status()
        signed = ConversationSignedUrlResponse.model_validate(response.json())
        url = urlsplit(signed.signed_url)
        if (
            url.scheme != "wss"
            or url.hostname != "api.elevenlabs.io"
            or url.port not in {None, 443}
            or url.username is not None
            or url.password is not None
            or url.path != "/v1/convai/conversation"
            or not url.query
            or url.fragment
        ):
            raise ValueError("Invalid conversation connection URL")
        return ConnectionGrant(
            transport="websocket",
            credential=signed.signed_url,
            metadata=ProviderSessionMetadata(
                adapter="elevenlabs_agents",
                adapter_version=ELEVENLABS_ADAPTER_VERSION,
                external_session_reference=signed.conversation_id,
            ),
        )

    def close(self) -> None:
        if self._owns_client:
            self._client.close()
