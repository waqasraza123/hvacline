import pytest
from pydantic import ValidationError

from insurance_operations.application import default_conversation_provider
from insurance_operations.conversations.providers import (
    ElevenLabsConversationProvider,
    LocalConversationProvider,
)
from insurance_operations.settings import ApiSettings, DatabaseSslMode


@pytest.fixture(autouse=True)
def isolate_settings_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for field_name in ApiSettings.model_fields:
        monkeypatch.delenv(field_name.upper(), raising=False)


def settings_for(provider: str) -> ApiSettings:
    values: dict[str, object] = {
        "app_environment": "development",
        "api_host": "127.0.0.1",
        "api_port": 8000,
        "database_url": "postgresql://user:password@localhost/development",
        "database_ssl_mode": DatabaseSslMode.DISABLE,
        "conversation_ai_enabled": True,
        "conversation_provider": provider,
        "development_actor_user_id": "00000000-0000-4000-8000-000000000002",
    }
    if provider == "elevenlabs":
        values.update(
            elevenlabs_api_key="test-secret",
            elevenlabs_agent_id="agent_test",
            elevenlabs_privacy_confirmed=True,
        )
    return ApiSettings(_env_file=None, **values)


def test_provider_selection_defaults_to_unchanged_elevenlabs_adapter() -> None:
    provider = default_conversation_provider(settings_for("elevenlabs"))
    try:
        assert isinstance(provider, ElevenLabsConversationProvider)
    finally:
        if provider is not None:
            provider.close()


def test_provider_selection_uses_local_adapter() -> None:
    provider = default_conversation_provider(settings_for("local"))

    assert isinstance(provider, LocalConversationProvider)


def test_local_workspace_cannot_replace_customer_account_provider() -> None:
    values = settings_for("local").model_dump()
    values["customer_portal_enabled"] = True
    with pytest.raises(ValidationError, match="development workspace only"):
        ApiSettings(_env_file=None, **values)


@pytest.mark.parametrize(
    "url",
    [
        "https://remote.example.test",
        "http://localhost:11434/api",
        "http://user:password@localhost:11434",
    ],
)
def test_local_extraction_cannot_send_conversation_to_remote_or_credentialed_url(
    url: str,
) -> None:
    values = settings_for("local").model_dump()
    values["local_ollama_base_url"] = url
    with pytest.raises(ValidationError, match="loopback"):
        ApiSettings(_env_file=None, **values)
