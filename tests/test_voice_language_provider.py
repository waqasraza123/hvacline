from copy import deepcopy
from typing import Any

import httpx
import pytest

from insurance_operations.conversations.contracts import ConversationProviderError
from insurance_operations.conversations.providers.elevenlabs import ElevenLabsConversationProvider
from insurance_operations.voice_languages import VoiceLanguageConfiguration


def configuration() -> VoiceLanguageConfiguration:
    return VoiceLanguageConfiguration.model_validate({
        "enabled_languages": ["en", "es"], "automatic_switching": True,
        "presets": {"browser": {
            "en": {"voice_id": "fictional-en", "greeting": "Fictional disclosure"},
            "es": {"voice_id": "fictional-es", "greeting": "Divulgación ficticia"},
        }},
    })


def hosted() -> dict[str, Any]:
    return {
        "agent_id": "fictional-agent",
        "conversation_config": {
            "agent": {"language": "en", "first_message": "Fictional disclosure", "prompt": {"built_in_tools": {
                "language_detection": {"type": "system", "params": {"system_tool_type": "language_detection", "only_at_conversation_start": False}},
            }}},
            "tts": {"voice_id": "fictional-en"},
            "language_presets": {"es": {"overrides": {"agent": {"first_message": "Divulgación ficticia"}, "tts": {"voice_id": "fictional-es"}}}},
            "conversation": {"client_events": ["agent_tool_request", "agent_tool_response_full_payload"]},
        },
        "platform_settings": {"overrides": {"conversation_config_override": {"agent": {"language": True}}}},
    }


def test_multilingual_authorization_reads_current_hosted_configuration_without_writing() -> None:
    calls: list[httpx.Request] = []
    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json=hosted())
    with httpx.Client(base_url="https://api.elevenlabs.io", transport=httpx.MockTransport(handler)) as client:
        provider = ElevenLabsConversationProvider(api_key="fictional-key", agent_id="fictional-agent", client=client)
        provider.validate_language_configuration(configuration(), "browser")
    assert len(calls) == 1
    assert calls[0].method == "GET"
    assert calls[0].url.path == "/v1/convai/agents/fictional-agent"


@pytest.mark.parametrize("drift", ["languages", "voice", "greeting", "override", "start_only", "events"])
def test_hosted_drift_fails_closed(drift: str) -> None:
    value = deepcopy(hosted())
    config = value["conversation_config"]
    if drift == "languages":
        config["language_presets"]["fr"] = {}
    elif drift == "voice":
        config["language_presets"]["es"]["overrides"]["tts"]["voice_id"] = "different-voice"
    elif drift == "greeting":
        config["agent"]["first_message"] = "Unreviewed greeting"
    elif drift == "override":
        value["platform_settings"]["overrides"]["conversation_config_override"]["agent"]["language"] = False
    elif drift == "start_only":
        config["agent"]["prompt"]["built_in_tools"]["language_detection"]["params"]["only_at_conversation_start"] = True
    else:
        config["conversation"]["client_events"] = []
    with httpx.Client(base_url="https://api.elevenlabs.io", transport=httpx.MockTransport(lambda _: httpx.Response(200, json=value))) as client:
        provider = ElevenLabsConversationProvider(api_key="fictional-key", agent_id="fictional-agent", client=client)
        with pytest.raises(ConversationProviderError, match="could not be verified"):
            provider.validate_language_configuration(configuration(), "browser")
