import asyncio
import hashlib
import json
from typing import Any
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from sqlalchemy.engine import Engine

from insurance_operations.application import create_app
from insurance_operations.errors import ApiError
from insurance_operations.settings import ApiSettings
from insurance_operations.telephony.contracts import (
    TelephonyAdapterError,
    TransferInstruction,
)
from insurance_operations.telephony.ingress import configure_telephony_ingress
from insurance_operations.telephony.phone_service import (
    normalize_post_call,
    post_call_fingerprint,
)
from insurance_operations.telephony.providers.telnyx_sip import (
    MAX_INITIATION_BYTES,
    TelnyxSipAdapter,
)
from insurance_operations.telephony.settings import (
    TelephoneProvider,
    TelephonyProviderSettings,
)

AGENT_ID = "agent_synthetic_phone"
INIT_SECRET = "synthetic-init-secret-at-least-32-characters"
INIT_HEADERS = {"Authorization": f"Bearer {INIT_SECRET}"}


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    for field in TelephonyProviderSettings.model_fields:
        monkeypatch.delenv(field.upper(), raising=False)


def sip_settings(**overrides: object) -> TelephonyProviderSettings:
    values: dict[str, Any] = {
        "app_environment": "development",
        "telephony_provider_enabled": True,
        "telephony_provider": "telnyx_sip",
        "development_actor_user_id": str(uuid4()),
        "elevenlabs_phone_agent_id": AGENT_ID,
        "elevenlabs_phone_initiation_secret": INIT_SECRET,
        "elevenlabs_phone_tool_secret": "synthetic-tools-secret",
        "elevenlabs_post_call_webhook_secret": "synthetic-post-call-secret",
        "elevenlabs_privacy_confirmed": True,
        **overrides,
    }
    return TelephonyProviderSettings(_env_file=None, **values)


def adapter() -> TelnyxSipAdapter:
    return TelnyxSipAdapter(
        agent_id=AGENT_ID,
        initiation_secret=INIT_SECRET,
        maximum_duration_seconds=180,
    )


def initiation_body(**overrides: object) -> bytes:
    return json.dumps(
        {
            "caller_id": "+15559990002",
            "called_number": "+15559990001",
            "agent_id": AGENT_ID,
            "call_sid": "",
            "conversation_id": "conv_synthetic_sip",
            "call_id": "opaque-sip-call@carrier.example.test",
            **overrides,
        }
    ).encode()


def test_telnyx_selection_needs_no_twilio_or_elevenlabs_rest_credentials() -> None:
    settings = sip_settings()
    assert settings.provider_enabled is True
    assert settings.telephony_provider is TelephoneProvider.TELNYX_SIP
    assert settings.twilio_account_sid is None
    assert settings.twilio_auth_token is None
    assert settings.elevenlabs_api_key is None


@pytest.mark.parametrize("enabled", [False, True])
def test_explicit_disabled_provider_does_not_require_credentials(enabled: bool) -> None:
    settings = TelephonyProviderSettings(
        _env_file=None,
        app_environment="development",
        telephony_provider=TelephoneProvider.DISABLED,
        telephony_provider_enabled=enabled,
    )
    assert settings.provider_enabled is False
    app = FastAPI()
    assert configure_telephony_ingress(app, settings, Mock(spec=Engine)) is None


def test_legacy_enabled_flag_still_selects_and_validates_twilio() -> None:
    with pytest.raises(ValidationError, match="TWILIO_ACCOUNT_SID"):
        TelephonyProviderSettings(
            _env_file=None,
            app_environment="development",
            telephony_provider_enabled=True,
        )
    settings = sip_settings(
        telephony_provider="twilio",
        elevenlabs_phone_initiation_secret=None,
        twilio_account_sid="AC" + "a" * 32,
        twilio_auth_token="synthetic-twilio-token",
        twilio_inbound_webhook_url="https://api.example.test/twilio/inbound",
        twilio_transfer_callback_url="https://api.example.test/twilio/transfer-result",
        elevenlabs_api_key="synthetic-api-key",
    )
    assert settings.telephony_provider is TelephoneProvider.TWILIO
    assert settings.provider_enabled is True


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("elevenlabs_phone_initiation_secret", None),
        ("elevenlabs_phone_initiation_secret", "too-short"),
        ("elevenlabs_phone_tool_secret", None),
        ("elevenlabs_post_call_webhook_secret", None),
        ("elevenlabs_phone_agent_id", None),
        ("elevenlabs_privacy_confirmed", False),
        ("development_actor_user_id", None),
        ("app_environment", "production"),
    ],
)
def test_telnyx_configuration_fails_closed(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        sip_settings(**{field: value})


def test_initiation_secret_is_separate_from_other_phone_secrets() -> None:
    with pytest.raises(ValidationError, match="separate webhook secret"):
        sip_settings(elevenlabs_phone_tool_secret=INIT_SECRET)


def test_sip_identity_is_not_validated_as_a_twilio_sid() -> None:
    call, context = adapter().verify_initiation(
        headers=INIT_HEADERS,
        body=initiation_body(
            call_sid="not-a-twilio-SID",
            sip_headers={"X-Tenant-ID": str(uuid4()), "Authorization": "untrusted"},
        ),
    )
    assert call.adapter_name == "telnyx_sip"
    assert call.source_call_reference == "opaque-sip-call@carrier.example.test"
    assert context.provider_call_id == call.source_call_reference
    assert context.conversation_id == "conv_synthetic_sip"
    assert "sip_headers" not in context.metadata()
    assert "Authorization" not in json.dumps(context.metadata())


@pytest.mark.parametrize("include_plus", [False, True])
def test_sip_numbers_are_canonicalized_at_the_provider_boundary(
    include_plus: bool,
) -> None:
    prefix = "+" if include_plus else ""
    call, _ = adapter().verify_initiation(
        headers=INIT_HEADERS,
        body=initiation_body(
            caller_id=f"{prefix}15559990002",
            called_number=f"{prefix}15559990001",
        ),
    )
    assert call.called_number_e164 == "+15559990001"
    assert call.caller_number_e164 == "+15559990002"


def test_documented_initiation_fields_do_not_require_optional_sip_fields() -> None:
    payload = json.loads(initiation_body())
    del payload["call_id"]
    del payload["call_sid"]
    call, context = adapter().verify_initiation(
        headers=INIT_HEADERS, body=json.dumps(payload).encode()
    )
    assert context.provider_call_id is None
    assert call.source_call_reference == "conversation:conv_synthetic_sip"


def test_missing_sip_id_uses_conversation_identity_without_inventing_a_carrier_id() -> (
    None
):
    call, context = adapter().verify_initiation(
        headers=INIT_HEADERS,
        body=initiation_body(
            call_id=None, caller_id="anonymous", call_sid="irrelevant"
        ),
    )
    assert call.source_call_reference == "conversation:conv_synthetic_sip"
    assert call.caller_number_e164 is None
    assert context.provider_call_id is None


@pytest.mark.parametrize(
    "authorization", [None, "", "Basic test", "Bearer wrong", "Bearer é"]
)
def test_invalid_initiation_authentication_is_rejected(
    authorization: str | None,
) -> None:
    with pytest.raises(ApiError) as rejected:
        adapter().verify_authorization(authorization)
    assert rejected.value.status_code == 401


def test_sip_headers_cannot_authenticate_the_webhook() -> None:
    with pytest.raises(ApiError) as rejected:
        adapter().verify_initiation(
            headers={}, body=initiation_body(sip_headers=INIT_HEADERS)
        )
    assert rejected.value.status_code == 401


@pytest.mark.parametrize(
    ("changes", "expected_status"),
    [
        ({"agent_id": "wrong-agent"}, 403),
        ({"called_number": "not-E164"}, 422),
        ({"called_number": "05559990001"}, 422),
        ({"called_number": "0015559990001"}, 422),
        ({"called_number": "1 (555) 999-0001"}, 422),
        ({"called_number": "sip:15559990001@example.test"}, 422),
        ({"called_number": "\uff11\uff15\uff15\uff15\uff19\uff19\uff19\uff10"}, 422),
        ({"called_number": "1555999"}, 422),
        ({"called_number": "1555999000112345"}, 422),
        ({"called_number": 15559990001}, 422),
        ({"conversation_id": ""}, 422),
        ({"conversation_id": "x" * 181}, 422),
        ({"call_id": "x" * 201}, 422),
        ({"call_id": "bad\u0000id"}, 422),
        ({"caller_id": "bad\u0000caller"}, 422),
        ({"sip_headers": {"X-Header": "x" * 1001}}, 422),
        ({"tenant_id": str(uuid4())}, 422),
    ],
)
def test_sip_request_validation(
    changes: dict[str, object], expected_status: int
) -> None:
    with pytest.raises(ApiError) as rejected:
        adapter().verify_initiation(
            headers=INIT_HEADERS, body=initiation_body(**changes)
        )
    assert rejected.value.status_code == expected_status


def test_oversized_sip_body_is_rejected() -> None:
    with pytest.raises(ApiError) as rejected:
        adapter().verify_initiation(
            headers=INIT_HEADERS, body=b" " * (MAX_INITIATION_BYTES + 1)
        )
    assert rejected.value.status_code == 413


@pytest.mark.parametrize(
    ("changes", "expected_path", "expected_type"),
    [
        ({"called_number": "private-number"}, "called_number", "value_error"),
        ({"conversation_id": None}, "conversation_id", "string_type"),
        ({"private-field-name": "private-value"}, "*", "extra_forbidden"),
        (
            {"sip_headers": {"private-header-name": "private-value" * 100}},
            "sip_headers.*",
            "string_too_long",
        ),
    ],
)
def test_initiation_diagnostics_expose_only_safe_paths_and_types(
    caplog: pytest.LogCaptureFixture,
    changes: dict[str, object],
    expected_path: str,
    expected_type: str,
) -> None:
    with pytest.raises(ApiError) as rejected:
        adapter().verify_initiation(
            headers=INIT_HEADERS, body=initiation_body(**changes)
        )
    assert rejected.value.code == "PHONE_INITIATION_INVALID"
    assert rejected.value.details == {}
    assert len(caplog.records) == 1
    assert caplog.records[0].args == ([{"path": expected_path, "type": expected_type}],)
    assert caplog.records[0].exc_info is None
    assert "private" not in caplog.text
    assert INIT_SECRET not in caplog.text
    assert "+15559990002" not in caplog.text
    assert AGENT_ID not in caplog.text


def test_initiation_diagnostics_identify_missing_fields_and_malformed_json(
    caplog: pytest.LogCaptureFixture,
) -> None:
    payload = json.loads(initiation_body())
    del payload["conversation_id"]
    for body, path, kind in (
        (json.dumps(payload).encode(), "conversation_id", "missing"),
        (b'{"private":', "$", "json_invalid"),
    ):
        caplog.clear()
        with pytest.raises(ApiError):
            adapter().verify_initiation(headers=INIT_HEADERS, body=body)
        assert caplog.records[0].args == ([{"path": path, "type": kind}],)
        assert "private" not in caplog.text


def test_unauthenticated_initiation_emits_no_payload_diagnostics(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with pytest.raises(ApiError) as rejected:
        adapter().verify_initiation(headers={}, body=b"private-invalid-json")
    assert rejected.value.status_code == 401
    assert not caplog.records


def test_telnyx_transfer_adapter_fails_closed() -> None:
    with pytest.raises(TelephonyAdapterError, match="verification is unavailable"):
        adapter().request_transfer(
            source_call_reference="opaque-sip-id",
            instruction=TransferInstruction(
                destination_e164="+15559990003", ring_timeout_seconds=20
            ),
        )


def test_telnyx_wiring_never_initializes_twilio(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden_twilio(**kwargs: object) -> None:
        raise AssertionError("Telnyx must not construct a Twilio adapter")

    monkeypatch.setattr(
        "insurance_operations.telephony.ingress.TwilioTelephonyAdapter",
        forbidden_twilio,
    )
    engine = Mock(spec=Engine)
    app = create_app(
        ApiSettings(
            _env_file=None,
            app_environment="development",
            api_host="127.0.0.1",
            api_port=8000,
            database_url="postgresql://synthetic:synthetic@localhost/development",
            conversation_ai_enabled=False,
            google_calendar_enabled=False,
            booking_email_enabled=False,
            customer_portal_enabled=False,
            homepage_chat_enabled=False,
        ),
        engine,
    )
    configure_telephony_ingress(app, sip_settings(), engine)

    async def exercise() -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            for path in ("twilio/inbound", "twilio/transfer-result"):
                response = await client.post("/api/v1/providers/" + path)
                assert response.status_code == 404
            response = await client.post("/api/v1/providers/elevenlabs/sip/initialize")
            assert response.status_code == 401
            response = await client.post(
                "/api/v1/providers/elevenlabs/tools/availability",
                json={
                    "inbound_call_id": str(uuid4()),
                    "conversation_id": "conv_synthetic",
                    "postal_code": "10001",
                    "day": "2026-11-01",
                },
            )
            assert response.status_code == 401

    asyncio.run(exercise())


def test_twilio_event_fingerprints_match_the_historical_serialization() -> None:
    legacy_event = {
        "event_type": "call_initiation_failure",
        "event_timestamp": 1_786_550_400,
        "inbound_call_id": None,
        "source_call_reference": "CA" + "b" * 32,
        "conversation_id": "conv_synthetic_legacy",
        "transcript": [],
    }
    payload: dict[str, object] = {
        "type": "call_initiation_failure",
        "event_timestamp": legacy_event["event_timestamp"],
        "data": {
            "conversation_id": legacy_event["conversation_id"],
            "metadata": {
                "type": "twilio",
                "body": {
                    "CallSid": legacy_event["source_call_reference"],
                },
            },
        },
    }
    expected = hashlib.sha256(
        json.dumps(legacy_event, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    assert post_call_fingerprint(normalize_post_call(payload)) == expected
