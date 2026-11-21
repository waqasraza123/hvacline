from urllib.parse import quote, urlsplit

import httpx
from pydantic import BaseModel, Field, ValidationError

from insurance_operations.conversations.contracts import (
    ConnectionGrant,
    ConversationInputMode,
    ConversationLanguageConfigurationError,
    ConversationProviderError,
    ProviderSessionMetadata,
)
from insurance_operations.voice_languages import VoiceChannel, VoiceLanguageConfiguration

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

    def validate_language_configuration(self, expected: VoiceLanguageConfiguration, channel: VoiceChannel) -> None:
        """Read hosted configuration before issuing a multilingual session grant."""
        try:
            response = self._client.get(
                f"/v1/convai/agents/{quote(self._agent_id, safe='')}",
                headers={"xi-api-key": self._api_key},
            )
            response.raise_for_status()
            data = response.json()
            if data.get("agent_id") != self._agent_id:
                raise ValueError("Hosted agent identity does not match")
            config = data["conversation_config"]
            agent = config["agent"]
            primary = agent.get("language", "en")
            presets = config.get("language_presets") or {}
            if primary != expected.default_language or {primary, *presets} != set(expected.enabled_languages):
                raise ValueError("Hosted languages differ from verified settings")
            security = data["platform_settings"]["overrides"]["conversation_config_override"]
            if security.get("agent", {}).get("language") is not True:
                raise ValueError("Hosted language override is disabled")
            prompt = agent.get("prompt") or {}
            tools = list((prompt.get("built_in_tools") or {}).values()) + list(prompt.get("tools") or [])
            detection = [tool for tool in tools if isinstance(tool, dict) and tool.get("type") == "system"
                and (tool.get("params") or {}).get("system_tool_type") == "language_detection"]
            if bool(detection) != expected.automatic_switching:
                raise ValueError("Hosted language detection differs from settings")
            if detection and (len(detection) != 1 or detection[0]["params"].get("only_at_conversation_start", False) is not False):
                raise ValueError("Hosted mid-call switching is restricted")
            events = (config.get("conversation") or {}).get("client_events", [])
            if expected.automatic_switching and not {"agent_tool_request", "agent_tool_response_full_payload"}.issubset(events):
                raise ValueError("Hosted language-tool request/result events are disabled")
            configured = expected.presets.get(channel)
            if configured is None:
                raise ValueError("Missing channel presets")
            for language in expected.enabled_languages:
                preset = configured[language]
                override = (presets.get(language) or {}).get("overrides") or {}
                voice = (override.get("tts") or {}).get("voice_id") or (config.get("tts") or {}).get("voice_id")
                greeting = (override.get("agent") or {}).get("first_message")
                if language == primary:
                    greeting = greeting or agent.get("first_message")
                else:
                    greeting = greeting or (presets[language].get("first_message_translation") or {}).get("text")
                if voice != preset.voice_id or greeting != preset.greeting:
                    raise ValueError("Hosted voice or reviewed greeting differs from settings")
        except (httpx.HTTPError, KeyError, TypeError, AttributeError, ValueError) as error:
            raise ConversationLanguageConfigurationError("Multilingual provider setup could not be verified") from error

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
