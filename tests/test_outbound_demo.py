import asyncio
import copy
import hashlib
import hmac
import json
import time
from pathlib import Path
from typing import Any
from unittest.mock import Mock
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI
from pydantic import ValidationError
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.errors import ApiError, api_error_handler
from insurance_operations.settings import ApiSettings
from insurance_operations.telephony.contracts import TelephonyAdapterError
from insurance_operations.telephony.outbound.prompt import (
    DEMO_PROMPT,
    FIRST_MESSAGE,
    TRANSFER_CONDITION,
)
from insurance_operations.telephony.outbound.provider import (
    ElevenLabsOutboundProvider,
    OutboundProviderError,
    transfer_outcome,
    validate_agent,
)
from insurance_operations.telephony.outbound.routes import create_outbound_demo_router
from insurance_operations.telephony.outbound.schemas import DemoCallInput
from insurance_operations.telephony.outbound.settings import OutboundDemoSettings

NUMBER = "+15559990002"
HUMAN = "+15559990003"
SECRET = "synthetic-outbound-secret-at-least-32-characters"
WEBHOOK_SECRET = "synthetic-outbound-webhook-secret-at-least-32-characters"


@pytest.fixture(autouse=True)
def isolate(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in OutboundDemoSettings.model_fields:
        monkeypatch.delenv(name.upper(), raising=False)


def settings(**overrides: Any) -> OutboundDemoSettings:
    return OutboundDemoSettings(
        _env_file=None,
        **{
            "app_environment": "development",
            "outbound_demo_enabled": True,
            "outbound_demo_agent_id": "synthetic-outbound-agent",
            "outbound_demo_phone_number_id": "synthetic-sip-number-id",
            "outbound_demo_allowed_numbers": NUMBER,
            "outbound_demo_human_number": HUMAN,
            "outbound_demo_secret": SECRET,
            "outbound_demo_webhook_secret": WEBHOOK_SECRET,
            "elevenlabs_api_key": "synthetic-api-key",
            **overrides,
        },
    )


def call_input(**overrides: Any) -> DemoCallInput:
    return DemoCallInput(
        **{
            "request_id": uuid4(),
            "phone_number": NUMBER,
            "scenario": "cooling",
            "consent": True,
            "consent_version": "outbound-demo-v1",
            **overrides,
        }
    )


def agent_config(transfer: bool = False) -> dict[str, Any]:
    tools: dict[str, Any] = {
        "end_call": {
            "type": "system",
            "name": "end_call",
            "params": {"system_tool_type": "end_call"},
        }
    }
    if transfer:
        tools["transfer_to_number"] = {
            "type": "system",
            "name": "transfer_to_number",
            "params": {
                "system_tool_type": "transfer_to_number",
                "transfers": [
                    {
                        "transfer_type": "sip_refer",
                        "condition": TRANSFER_CONDITION,
                        "transfer_destination": {
                            "type": "phone",
                            "phone_number": HUMAN,
                        },
                    }
                ],
            },
        }
    return {
        "agent_id": "synthetic-outbound-agent",
        "conversation_config": {
            "conversation": {"max_duration_seconds": 180},
            "agent": {
                "first_message": FIRST_MESSAGE,
                "prompt": {"prompt": DEMO_PROMPT, "built_in_tools": tools},
            },
        },
        "platform_settings": {
            "privacy": {"record_voice": False, "retention_days": 0},
            "auth": {"enable_auth": True},
            "workspace_overrides": {
                "webhooks": {
                    "post_call_webhook_id": "synthetic-hook",
                    "events": ["transcript", "call_initiation_failure"],
                }
            },
        },
    }


@pytest.mark.parametrize(
    "overrides",
    [
        {"outbound_demo_allowed_numbers": "5551234"},
        {"outbound_demo_secret": "short"},
        {"outbound_demo_webhook_secret": SECRET},
        {"outbound_demo_agent_id": "shared", "elevenlabs_phone_agent_id": "shared"},
        {"outbound_demo_website_enabled": True},
        {"outbound_demo_transfer_enabled": True},
        {"outbound_demo_max_duration_seconds": 181},
        {"app_environment": "production"},
    ],
)
def test_configuration_fails_closed(overrides: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        settings(**overrides)


@pytest.mark.parametrize(
    "overrides",
    [
        {"consent": False},
        {"consent": 1},
        {"consent_version": "old"},
        {"phone_number": "15559990002"},
        {"scenario": "anything"},
    ],
)
def test_request_requires_current_explicit_consent_and_bounded_scenario(
    overrides: dict[str, Any],
) -> None:
    with pytest.raises(ValidationError):
        call_input(**overrides)


def test_blank_disabled_configuration_is_valid() -> None:
    assert (
        OutboundDemoSettings(
            _env_file=None,
            app_environment="test",
            outbound_demo_agent_id="",
            outbound_demo_phone_number_id="",
        ).outbound_demo_enabled
        is False
    )


def test_preflight_accepts_fixed_native_sip_transfer_only() -> None:
    config = agent_config(True)
    enabled = settings(
        outbound_demo_transfer_enabled=True, outbound_demo_carrier_limit_confirmed=True
    )
    validate_agent(config, enabled)
    for destination in (
        {"type": "phone_dynamic_variable", "dynamic_variable": "user_number"},
        {"type": "phone", "phone_number": NUMBER},
    ):
        changed = copy.deepcopy(config)
        changed["conversation_config"]["agent"]["prompt"]["built_in_tools"][
            "transfer_to_number"
        ]["params"]["transfers"][0]["transfer_destination"] = destination
        with pytest.raises(OutboundProviderError):
            validate_agent(changed, enabled)
    with pytest.raises(OutboundProviderError):
        validate_agent(config, settings())


def test_dashboard_template_matches_the_enforced_prompt() -> None:
    config = json.loads(
        (
            Path(__file__).resolve().parents[1] / "docs/elevenlabs-outbound-agent.json"
        ).read_text()
    )
    config["agent_id"] = "synthetic-outbound-agent"
    validate_agent(config, settings())


@pytest.mark.parametrize(
    "path,value",
    [
        (("conversation_config", "conversation", "max_duration_seconds"), 181),
        (("conversation_config", "agent", "prompt", "tool_ids"), ["external-tool"]),
        (("conversation_config", "agent", "prompt", "prompt"), "Book a real service"),
        (("platform_settings", "privacy", "record_voice"), True),
        (("workflow",), {"nodes": {"arbitrary-transfer": {}}}),
    ],
)
def test_preflight_rejects_agent_drift(path: tuple[str, ...], value: Any) -> None:
    config = agent_config()
    target = config
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(OutboundProviderError):
        validate_agent(config, settings())


def test_outbound_uses_official_sip_contract_without_retry() -> None:
    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "success": True,
                "message": "accepted",
                "conversation_id": "conv-synthetic",
                "sip_call_id": "sip-synthetic",
            },
        )

    with httpx.Client(
        base_url="https://api.elevenlabs.io", transport=httpx.MockTransport(handle)
    ) as client:
        provider = ElevenLabsOutboundProvider(settings(), client)
        receipt = provider.dial(call_input(), "synthetic-call-id")
    assert receipt.conversation_id == "conv-synthetic"
    assert len(requests) == 1
    request = requests[0]
    assert request.url.path == "/v1/convai/sip-trunk/outbound-call"
    payload = json.loads(request.content)
    assert payload["to_number"] == NUMBER
    assert payload["agent_phone_number_id"] == "synthetic-sip-number-id"
    assert (
        payload["conversation_initiation_client_data"]["dynamic_variables"][
            "outbound_demo_call_id"
        ]
        == "synthetic-call-id"
    )
    assert payload["telephony_call_config"] == {"ringing_timeout_secs": 25}


@pytest.mark.parametrize(
    "status,unknown", [(403, False), (422, False), (500, True), (200, True)]
)
def test_provider_rejections_and_ambiguous_responses(
    status: int, unknown: bool
) -> None:
    with httpx.Client(
        base_url="https://api.elevenlabs.io",
        transport=httpx.MockTransport(lambda _: httpx.Response(status, json={})),
    ) as client:
        with pytest.raises(OutboundProviderError) as caught:
            ElevenLabsOutboundProvider(settings(), client).dial(
                call_input(), str(uuid4())
            )
    assert caught.value.outcome_unknown is unknown


def test_post_timeout_is_unknown_and_never_retried() -> None:
    requests: list[httpx.Request] = []

    def timeout(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        raise httpx.ReadTimeout("Synthetic timeout", request=request)

    with httpx.Client(
        base_url="https://api.elevenlabs.io", transport=httpx.MockTransport(timeout)
    ) as client:
        with pytest.raises(OutboundProviderError) as caught:
            ElevenLabsOutboundProvider(settings(), client).dial(
                call_input(), str(uuid4())
            )
    assert caught.value.outcome_unknown is True
    assert len(requests) == 1


@pytest.mark.parametrize(
    "timestamp_delta,agent,tamper",
    [
        (0, "synthetic-outbound-agent", False),
        (-301, "synthetic-outbound-agent", False),
        (0, "other-agent", False),
        (0, "synthetic-outbound-agent", True),
    ],
)
def test_webhook_signature_freshness_body_and_agent_binding(
    timestamp_delta: int, agent: str, tamper: bool
) -> None:
    body = json.dumps(
        {
            "type": "call_initiation_failure",
            "data": {"agent_id": agent, "conversation_id": "conv-synthetic"},
        }
    ).encode()
    timestamp = int(time.time()) + timestamp_delta
    signature = hmac.new(
        WEBHOOK_SECRET.encode(), str(timestamp).encode() + b"." + body, hashlib.sha256
    ).hexdigest()
    headers = {"ElevenLabs-Signature": f"t={timestamp},v0={signature}"}
    provider = ElevenLabsOutboundProvider(settings())
    if timestamp_delta or agent != "synthetic-outbound-agent" or tamper:
        with pytest.raises(TelephonyAdapterError):
            provider.verify_webhook(headers, body + b" " if tamper else body)
    else:
        assert (
            provider.verify_webhook(headers, body)["type"] == "call_initiation_failure"
        )


def test_sip_refer_is_not_reported_as_a_human_answer() -> None:
    data = {
        "transcript": [
            {
                "tool_results": [
                    {
                        "tool_name": "transfer_to_number",
                        "result": {
                            "result_type": "transfer_to_number_sip_success",
                            "transfer_number": HUMAN,
                        },
                    }
                ]
            }
        ]
    }
    assert transfer_outcome(data, HUMAN) == "refer_accepted"
    assert transfer_outcome(data, NUMBER) == "unconfirmed"
    assert (
        transfer_outcome(
            {
                "transcript": [
                    {
                        "tool_results": [
                            {"tool_name": "transfer_to_number", "is_error": True}
                        ]
                    }
                ]
            },
            HUMAN,
        )
        == "failed"
    )


def test_transfer_without_a_result_stays_unconfirmed() -> None:
    assert (
        transfer_outcome(
            {
                "transcript": [
                    {
                        "tool_calls": [
                            {
                                "tool_name": "transfer_to_number",
                                "request_id": "synthetic-transfer",
                            }
                        ]
                    }
                ]
            },
            HUMAN,
        )
        == "unconfirmed"
    )


@pytest.mark.parametrize(
    "transcript",
    [
        [None],
        [{"tool_calls": "invalid"}],
        [{"tool_results": {"tool_name": "transfer_to_number"}}],
        [{"tool_results": [None]}],
    ],
)
def test_malformed_transfer_evidence_is_rejected(transcript: object) -> None:
    with pytest.raises(ValueError, match="Invalid demo call transcript"):
        transfer_outcome({"transcript": transcript}, HUMAN)


def test_later_failure_does_not_erase_a_possible_live_transfer_leg() -> None:
    assert (
        transfer_outcome(
            {
                "transcript": [
                    {
                        "tool_results": [
                            {
                                "tool_name": "transfer_to_number",
                                "result": {
                                    "result_type": "transfer_to_number_sip_success",
                                    "transfer_number": HUMAN,
                                },
                            },
                            {"tool_name": "transfer_to_number", "is_error": True},
                        ]
                    }
                ]
            },
            HUMAN,
        )
        == "refer_accepted"
    )


def test_admin_gate_is_required_even_without_general_sandbox() -> None:
    api = ApiSettings(
        _env_file=None,
        app_environment="development",
        api_host="localhost",
        api_port=8000,
        database_url="postgresql://synthetic:synthetic@localhost/synthetic",
        demo_sandbox_enabled=False,
        conversation_ai_enabled=False,
        customer_portal_enabled=False,
        demo_admin_token=SECRET,
        development_actor_user_id=uuid4(),
    )
    sessions = Mock(spec=sessionmaker[Session])
    application = FastAPI()
    application.add_exception_handler(ApiError, api_error_handler)  # type: ignore[arg-type]
    application.include_router(create_outbound_demo_router(api, sessions, settings()))

    async def request() -> httpx.Response:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=application), base_url="http://test"
        ) as client:
            return await client.post(
                "/api/v1/outbound-demo/admin/calls",
                json=call_input().model_dump(mode="json"),
            )

    assert asyncio.run(request()).status_code == 401
    sessions.assert_not_called()
