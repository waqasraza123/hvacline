import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi import FastAPI
from pydantic import ValidationError

from insurance_operations.actors import ActorContext
from insurance_operations.errors import ApiError
from insurance_operations.voice_languages import (
    ProviderLanguageEvidence,
    CHANNELS,
    VoiceLanguageConfiguration,
    authorize_language,
    create_voice_language_router,
    registry,
    require_readback_language,
)
from insurance_operations.database.models.conversation import ConversationSession


def configured() -> tuple[UUID, VoiceLanguageConfiguration, SimpleNamespace]:
    agency = uuid4()
    config = VoiceLanguageConfiguration.model_validate({
        "enabled_languages": ["en", "es"], "automatic_switching": True,
        "presets": {"browser": {
            "en": {"voice_id": "fictional-en", "greeting": "Fictional English AI disclosure."},
            "es": {"voice_id": "fictional-es", "greeting": "Divulgación ficticia de IA."},
        }},
    })
    evidence = ProviderLanguageEvidence(
        agency_id=agency, agent_id="fictional-browser",
        verified_at=datetime.now(UTC) - timedelta(minutes=1),
        supported_languages=["en", "es"], presets={code: preset.model_copy(deep=True) for code, preset in config.presets["browser"].items()},
        language_override=True, language_detection=True, mid_call_switching=True,
        safety_prompt_verified=True, stack_verified=True,
    )
    settings = SimpleNamespace(elevenlabs_agent_id="fictional-browser",
        conversation_provider="elevenlabs", voice_language_provider_evidence={"browser": evidence})
    return agency, config, settings


def test_pending_languages_preserve_existing_english_and_do_not_attest_provider() -> None:
    agency, config, settings = configured()
    settings.voice_language_provider_evidence = {}
    result = authorize_language(settings, agency, config, None, "browser")
    assert result == {"language": "en", "allowed_languages": ["en"], "automatic_switching": False, "overrides": None}
    with pytest.raises(ApiError):
        authorize_language(settings, agency, config, "es", "browser")


def test_capabilities_are_bound_to_agency_agent_channel_and_exact_configuration() -> None:
    agency, config, settings = configured()
    assert authorize_language(settings, agency, config, "es", "browser")["language"] == "es"
    for channel in CHANNELS[1:]:
        with pytest.raises(ApiError):
            authorize_language(settings, agency, config, "es", channel)
    with pytest.raises(ApiError):
        authorize_language(settings, uuid4(), config, "es", "browser")
    settings.elevenlabs_agent_id = "different-agent"
    with pytest.raises(ApiError):
        authorize_language(settings, agency, config, "es", "browser")
    settings.elevenlabs_agent_id = "fictional-browser"
    config.presets["browser"]["es"].greeting = "Changed greeting"
    with pytest.raises(ApiError):
        authorize_language(settings, agency, config, "es", "browser")


def test_urdu_is_never_available_from_target_language_intent_alone() -> None:
    agency, config, settings = configured()
    config.enabled_languages.append("ur")
    assert not any(item["available"] for item in registry(settings, agency, config)["languages"] if item["code"] == "ur")


def test_languages_cannot_expand_a_previously_authorized_session() -> None:
    row = ConversationSession(provider_metadata={"voice_language": {"allowed_languages": ["en"]}})
    require_readback_language(row, "en")
    with pytest.raises(ApiError):
        require_readback_language(row, "es")


def test_evidence_requires_full_stack_and_real_timezone_aware_verification() -> None:
    agency, config, settings = configured()
    value = settings.voice_language_provider_evidence["browser"].model_dump()
    with pytest.raises(ValidationError):
        ProviderLanguageEvidence.model_validate({**value, "verified_at": datetime.now()})
    settings.voice_language_provider_evidence["browser"].stack_verified = False
    with pytest.raises(ApiError):
        authorize_language(settings, agency, config, "es", "browser")


def test_language_administration_requires_token_even_outside_demo_sandbox() -> None:
    sessions = Mock()
    actor = ActorContext(uuid4(), "Fictional Admin", uuid4(), "Fictional Agency", "development")
    app = FastAPI()
    app.include_router(create_voice_language_router(sessions, SimpleNamespace(
        demo_admin_token=None, app_environment="development", demo_sandbox_enabled=False),
        lambda: actor, administrator=True))
    async def request() -> None:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            with pytest.raises(ApiError) as error:
                await client.get("/api/v1/development/voice-languages")
            assert error.value.status_code == 401
    asyncio.run(request())
    sessions.assert_not_called()
