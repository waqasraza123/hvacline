import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from insurance_operations.conversations.spoken import require_spoken_confirmation
from insurance_operations.customers import CustomerInput
from insurance_operations.database.models.whatsapp import WhatsAppConversation
from insurance_operations.errors import ApiError
from insurance_operations.whatsapp.provider import (
    ElevenLabsWhatsAppAdapter,
    WhatsAppInitiation,
    spoken_history,
)
from insurance_operations.whatsapp.routes import CONSENT_READBACK, callback_readback
from insurance_operations.whatsapp.service import WhatsAppService
from insurance_operations.whatsapp.settings import WhatsAppSettings


def adapter() -> ElevenLabsWhatsAppAdapter:
    return ElevenLabsWhatsAppAdapter(
        agent_id="synthetic-whatsapp-agent",
        number_id="synthetic-meta-number-id",
        init_secret="synthetic-init",
        tool_secret="synthetic-tool",
        session_secret="synthetic-session",
        post_call_secret="synthetic-post",
        clock=lambda: 1000,
    )


def initialization(**changes: str) -> WhatsAppInitiation:
    return WhatsAppInitiation.model_validate(
        {
            "caller_id": "BSUID:opaque-not-a-phone-number",
            "called_number": "synthetic-meta-number-id",
            "agent_id": "synthetic-whatsapp-agent",
            "call_sid": "",
            "conversation_id": "synthetic-conversation",
            **changes,
        }
    )


def test_initialization_requires_secret_agent_number_and_empty_call_sid() -> None:
    provider = adapter()
    provider.verify_initialization("Bearer synthetic-init", initialization())
    for auth, data in [
        (None, initialization()),
        ("Bearer synthetic-init", initialization(agent_id="different-agent")),
        ("Bearer synthetic-init", initialization(called_number="different-number")),
        ("Bearer non-ascii-\u00e9", initialization()),
    ]:
        with pytest.raises(ApiError):
            provider.verify_initialization(auth, data)
    with pytest.raises(ValidationError):
        initialization(call_sid="CA-unexpected")


def test_tools_require_call_scoped_token_and_independent_tool_secret() -> None:
    provider = adapter()
    token = provider.session_token("binding-one", "conversation-one")
    provider.verify_tool(
        "Bearer synthetic-tool", token, "binding-one", "conversation-one"
    )
    for auth, supplied, binding, conversation in [
        (None, token, "binding-one", "conversation-one"),
        ("Bearer synthetic-tool", None, "binding-one", "conversation-one"),
        ("Bearer synthetic-tool", token, "binding-two", "conversation-one"),
        ("Bearer synthetic-tool", token, "binding-one", "conversation-two"),
    ]:
        with pytest.raises(ApiError):
            provider.verify_tool(auth, supplied, binding, conversation)
    assert provider.caller_digest("BSUID:opaque") != provider.caller_digest(
        "+15550100100"
    )


def test_post_call_requires_raw_body_signature_freshness_and_bound_agent() -> None:
    provider = adapter()

    def signed(body: bytes, timestamp: int = 1000) -> dict[str, str]:
        signature = hmac.new(
            b"synthetic-post", str(timestamp).encode() + b"." + body, hashlib.sha256
        ).hexdigest()
        return {"ElevenLabs-Signature": f"t={timestamp},v0={signature}"}

    body = json.dumps(
        {
            "type": "post_call_transcription",
            "event_timestamp": 990,
            "data": {
                "agent_id": "synthetic-whatsapp-agent",
                "conversation_id": "synthetic-conversation",
            },
        }
    ).encode()
    assert (
        provider.verify_post_call(signed(body), body).data.conversation_id
        == "synthetic-conversation"
    )
    for headers, payload in [
        ({}, body),
        (signed(body), body + b" "),
        (signed(body, 1), body),
        (
            signed(body.replace(b"synthetic-whatsapp-agent", b"wrong-agent")),
            body.replace(b"synthetic-whatsapp-agent", b"wrong-agent"),
        ),
    ]:
        with pytest.raises(ApiError):
            provider.verify_post_call(headers, payload)


def test_provider_history_enforces_actual_disclosure_and_callback_readbacks() -> None:
    history = json.dumps(
        {
            "entries": [
                {"role": "agent", "message": CONSENT_READBACK},
                {"role": "user", "message": "yes"},
                {"role": "agent", "tool_requests": []},
                {"role": "tool", "tool_results": []},
            ]
        }
    )
    require_spoken_confirmation(spoken_history(history), CONSENT_READBACK)
    refused = history.replace('"message": "yes"', '"message": "no"')
    with pytest.raises(ValueError):
        require_spoken_confirmation(spoken_history(refused), CONSENT_READBACK)
    with pytest.raises(ApiError):
        spoken_history("invalid-json")
    with pytest.raises(ApiError):
        callback_readback(CustomerInput(full_name="Fictional Caller"))


def test_disabled_whatsapp_needs_no_twilio_or_provider_credentials() -> None:
    settings = WhatsAppSettings(_env_file=None, app_environment="development")
    assert settings.whatsapp_enabled is False
    with pytest.raises(ValidationError):
        WhatsAppSettings(
            _env_file=None, app_environment="development", whatsapp_enabled=True
        )


def test_whatsapp_configuration_preserves_production_gate() -> None:
    with pytest.raises(ValidationError, match="development"):
        WhatsAppSettings(
            _env_file=None, app_environment="production", whatsapp_enabled=True
        )


def test_expired_or_finalized_binding_cannot_authorize_tools() -> None:
    now = datetime.now(UTC)
    for expires_at, finalized_at in [
        (now - timedelta(seconds=1), None),
        (now + timedelta(seconds=30), now),
    ]:
        binding = WhatsAppConversation(expires_at=expires_at, finalized_at=finalized_at)
        with pytest.raises(ApiError):
            WhatsAppService.require_active_binding(binding, now)
