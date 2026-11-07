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
import phonenumbers
import pytest
from fastapi import FastAPI
from pydantic import ValidationError
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.errors import ApiError, api_error_handler
from insurance_operations.settings import ApiSettings
from insurance_operations.telephony.contracts import TelephonyAdapterError
from insurance_operations.telephony.outbound.destinations import validate_us_destination
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
from insurance_operations.telephony.outbound.service import OutboundDemoService
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
            "telnyx_verify_api_key": "synthetic-telnyx-verify-key",
            "telnyx_verify_profile_id": uuid4(),
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


def agent_config_with_extensions(transfer: bool = False) -> dict[str, Any]:
    config = agent_config(transfer)
    prompt = config["conversation_config"]["agent"]["prompt"]
    prompt["tool_ids"] = ["synthetic-external-tool"]
    prompt["mcp_server_ids"] = ["synthetic-mcp-server"]
    prompt["native_mcp_server_ids"] = ["synthetic-native-mcp-server"]
    prompt["tools"] = [
        {"type": "client", "name": "show_demo_details"},
        {"type": "webhook", "name": "lookup_demo_details"},
    ]
    prompt["built_in_tools"]["skip_turn"] = {
        "type": "system",
        "name": "skip_turn",
        "params": {"system_tool_type": "skip_turn"},
    }
    config["workflow"] = {
        "nodes": {
            "start_node": {"type": "start", "edge_order": ["start_to_demo"]},
            "demo": {
                "type": "override_agent",
                "additional_prompt": "Ask one demo question at a time.",
                "additional_tool_ids": ["synthetic-external-tool"],
                "conversation_config": {},
                "edge_order": [],
            },
        },
        "edges": {
            "start_to_demo": {
                "source": "start_node",
                "target": "demo",
                "forward_condition": {"type": "unconditional"},
            }
        },
    }
    return config


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
        {"outbound_demo_account_daily_limit": 0},
        {"outbound_demo_account_daily_limit": 3},
        {"outbound_demo_sms_daily_limit": 101},
        {"outbound_demo_sms_cooldown_seconds": 1},
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
        {"phone_number": "911"},
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


def test_preflight_requires_fixed_native_sip_transfer_with_additional_tools() -> None:
    config = agent_config_with_extensions(True)
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


@pytest.mark.parametrize("legacy_tools", [False, True])
def test_preflight_accepts_workflows_and_additional_tools(legacy_tools: bool) -> None:
    config = agent_config_with_extensions()
    if legacy_tools:
        prompt = config["conversation_config"]["agent"]["prompt"]
        prompt["tools"].extend(prompt.pop("built_in_tools").values())
    validate_agent(config, settings())


def test_preflight_still_requires_native_end_call_with_additional_tools() -> None:
    config = agent_config_with_extensions()
    prompt = config["conversation_config"]["agent"]["prompt"]
    del prompt["built_in_tools"]["end_call"]
    prompt["tools"].append({"type": "client", "name": "end_call"})
    with pytest.raises(OutboundProviderError):
        validate_agent(config, settings())


@pytest.mark.parametrize("tools", [{"unexpected": "mapping"}, ["tool-id"], [None]])
def test_preflight_rejects_malformed_inline_tools(tools: Any) -> None:
    config = agent_config_with_extensions()
    config["conversation_config"]["agent"]["prompt"]["tools"] = tools
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
        (("conversation_config", "agent", "prompt", "prompt"), "Book a real service"),
        (("conversation_config", "agent", "first_message"), "Different greeting"),
        (("platform_settings", "privacy", "record_voice"), True),
        (("platform_settings", "privacy", "retention_days"), 1),
        (("platform_settings", "auth", "enable_auth"), False),
        (("platform_settings", "workspace_overrides", "webhooks", "events"), []),
    ],
)
def test_preflight_rejects_agent_drift(path: tuple[str, ...], value: Any) -> None:
    config = agent_config_with_extensions()
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


def outbound_application(config: OutboundDemoSettings) -> tuple[FastAPI, Mock]:
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
    application.include_router(create_outbound_demo_router(api, sessions, config))
    return application, sessions


@pytest.mark.parametrize("policy", ["allowlist", "consented_us"])
@pytest.mark.parametrize("token", [None, "wrong-admin-token"])
def test_admin_gate_is_required_even_without_general_sandbox(
    policy: str, token: str | None
) -> None:
    application, sessions = outbound_application(
        settings(outbound_demo_number_policy=policy)
    )

    async def request() -> httpx.Response:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=application), base_url="http://test"
        ) as client:
            return await client.post(
                "/api/v1/outbound-demo/admin/calls",
                headers={"X-Demo-Admin-Token": token} if token is not None else {},
                json=call_input(phone_number="+12025550123").model_dump(mode="json"),
            )

    assert asyncio.run(request()).status_code == 401
    sessions.assert_not_called()


def test_number_policy_defaults_to_allowlist_and_requires_recipients() -> None:
    assert settings().outbound_demo_number_policy == "allowlist"
    with pytest.raises(ValidationError, match="allowlist is required"):
        settings(outbound_demo_allowed_numbers="")
    config = settings(
        outbound_demo_number_policy="consented_us", outbound_demo_allowed_numbers=""
    )
    assert config.allowed_numbers == frozenset()


@pytest.mark.parametrize(
    "overrides",
    [
        {"outbound_demo_number_policy": "any"},
        {"outbound_demo_website_enabled": True},
        {"outbound_demo_transfer_enabled": True},
        {"outbound_demo_secret": ""},
        {"outbound_demo_webhook_secret": ""},
        {"elevenlabs_api_key": ""},
    ],
)
def test_consented_us_configuration_fails_closed(overrides: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        settings(
            **{
                "outbound_demo_number_policy": "consented_us",
                "outbound_demo_allowed_numbers": "",
                **overrides,
            }
        )


@pytest.mark.parametrize(
    "value",
    ["+12025550123", "+1 (202) 555-0123", "202-555-0123", "1 202 555 0123"],
)
def test_destination_normalization_precedes_request_hashing(value: str) -> None:
    assert call_input(phone_number=value).phone_number == "+12025550123"


@pytest.mark.parametrize(
    "value",
    [
        "911",
        "988",
        "112",
        "211",
        "12345",
        "",
        "+1",
        "call +12025550123",
        "1-800-FLOWERS",
        "+12025550123 ext 4",
        "+12025550123;ext=4",
        "+12025550123,123",
        "+12025550123#",
        "sip:+12025550123@example.test",
        "+１２０２５５５０１２３",
        "2" * 65,
    ],
)
def test_malformed_and_short_destinations_are_rejected(value: str) -> None:
    with pytest.raises(ValidationError):
        call_input(phone_number=value)


@pytest.mark.parametrize(
    "number", ["+12025550123", "+12125550123", "+19075550123", "+18085550123"]
)
def test_consented_us_accepts_us_geographic_numbers(number: str) -> None:
    validate_us_destination(number)


@pytest.mark.parametrize("region", ["CA", "BS", "DO", "JM", "BB", "TT", "SX"])
def test_consented_us_rejects_other_nanp_regions(region: str) -> None:
    number = phonenumbers.example_number(region)
    assert number is not None
    assert number.country_code == 1
    value = phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)
    with pytest.raises(ApiError) as caught:
        validate_us_destination(value)
    assert caught.value.code == "DEMO_DESTINATION_UNSUPPORTED"


@pytest.mark.parametrize("region", ["US", "AS", "GU", "MP", "PR", "VI"])
def test_consented_us_accepts_us_and_territory_numbering_assignments(region: str) -> None:
    number = phonenumbers.example_number(region)
    assert number is not None
    value = phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)
    validate_us_destination(value)


@pytest.mark.parametrize(
    "kind", [phonenumbers.PhoneNumberType.FIXED_LINE, phonenumbers.PhoneNumberType.MOBILE]
)
def test_consented_us_accepts_mobile_and_landline_examples(kind: int) -> None:
    number = phonenumbers.example_number_for_type("US", kind)
    assert number is not None
    value = phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)
    validate_us_destination(value)


@pytest.mark.parametrize(
    "number,code",
    [
        ("+14165550123", "DEMO_DESTINATION_UNSUPPORTED"),
        ("+19002345678", "DEMO_DESTINATION_UNSUPPORTED"),
        ("+12001230101", "DEMO_PHONE_NUMBER_INVALID"),
    ],
)
def test_admin_destination_errors_use_the_existing_api_envelope(
    number: str, code: str
) -> None:
    application, sessions = outbound_application(
        settings(outbound_demo_number_policy="consented_us")
    )

    async def request() -> httpx.Response:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=application), base_url="http://test"
        ) as client:
            return await client.post(
                "/api/v1/outbound-demo/admin/calls",
                headers={"X-Demo-Admin-Token": SECRET},
                json=call_input(phone_number=number).model_dump(mode="json"),
            )

    response = asyncio.run(request())
    assert response.status_code == 422
    assert response.json()["error"]["code"] == code
    assert response.json()["error"]["details"] == {"field": "phone_number"}
    sessions.assert_not_called()


@pytest.mark.parametrize(
    "number,code",
    [
        ("+14165550123", "DEMO_DESTINATION_UNSUPPORTED"),
        ("+442079460123", "DEMO_DESTINATION_UNSUPPORTED"),
        ("+19002345678", "DEMO_DESTINATION_UNSUPPORTED"),
        ("+18002345678", "DEMO_DESTINATION_UNSUPPORTED"),
        ("+15002345678", "DEMO_DESTINATION_UNSUPPORTED"),
        ("+12001230101", "DEMO_PHONE_NUMBER_INVALID"),
        ("+12021110123", "DEMO_PHONE_NUMBER_INVALID"),
        ("+99912345678", "DEMO_PHONE_NUMBER_INVALID"),
    ],
)
@pytest.mark.parametrize("owner", ["admin", "synthetic-visitor"])
def test_consented_us_rejections_are_structured_and_never_reach_persistence(
    number: str, code: str, owner: str
) -> None:
    config = settings(
        outbound_demo_number_policy="consented_us",
        outbound_demo_allowed_numbers="",
        outbound_demo_website_enabled=True,
        outbound_demo_live_verified=True,
    )
    sessions = Mock(spec=sessionmaker[Session])
    provider = Mock(spec=ElevenLabsOutboundProvider)
    service = OutboundDemoService(sessions, Mock(spec=ApiSettings), config, provider)
    with pytest.raises(ApiError) as caught:
        service.create(call_input(phone_number=number), owner)
    assert caught.value.status_code == 422
    assert caught.value.code == code
    assert caught.value.details == {"field": "phone_number"}
    assert number not in caught.value.message
    sessions.assert_not_called()
    provider.preflight.assert_not_called()
    provider.dial.assert_not_called()


def test_consented_us_rejects_visitor_calls_when_website_is_disabled() -> None:
    config = settings(outbound_demo_number_policy="consented_us")
    sessions = Mock(spec=sessionmaker[Session])
    provider = Mock(spec=ElevenLabsOutboundProvider)
    service = OutboundDemoService(sessions, Mock(spec=ApiSettings), config, provider)
    with pytest.raises(ApiError) as caught:
        service.create(call_input(phone_number="+12025550123"), "synthetic-visitor")
    assert caught.value.code == "OUTBOUND_DEMO_UNAVAILABLE"
    sessions.assert_not_called()
    provider.dial.assert_not_called()


@pytest.mark.parametrize("consent", [False, None, 1, "true"])
def test_consented_us_admin_endpoint_requires_explicit_consent(consent: object) -> None:
    application, sessions = outbound_application(
        settings(outbound_demo_number_policy="consented_us")
    )
    payload = call_input(phone_number="+12025550123").model_dump(mode="json")
    payload["consent"] = consent

    async def request() -> httpx.Response:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=application), base_url="http://test"
        ) as client:
            return await client.post(
                "/api/v1/outbound-demo/admin/calls",
                headers={"X-Demo-Admin-Token": SECRET},
                json=payload,
            )

    assert asyncio.run(request()).status_code == 422
    sessions.assert_not_called()


@pytest.mark.parametrize("field", ["consent", "consent_version"])
def test_consented_us_admin_endpoint_requires_consent_fields(field: str) -> None:
    application, sessions = outbound_application(
        settings(outbound_demo_number_policy="consented_us")
    )
    payload = call_input(phone_number="+12025550123").model_dump(mode="json")
    del payload[field]

    async def request() -> httpx.Response:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=application), base_url="http://test"
        ) as client:
            return await client.post(
                "/api/v1/outbound-demo/admin/calls",
                headers={"X-Demo-Admin-Token": SECRET},
                json=payload,
            )

    assert asyncio.run(request()).status_code == 422
    sessions.assert_not_called()


def test_consented_us_website_requires_live_acceptance_even_if_flag_is_mutated() -> None:
    config = settings(outbound_demo_number_policy="consented_us")
    config.outbound_demo_website_enabled = True
    application, sessions = outbound_application(config)

    async def request() -> tuple[httpx.Response, httpx.Response]:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=application),
            base_url="http://test",
            headers={"X-Outbound-Demo-Key": SECRET, "X-Outbound-Visitor": "a" * 43},
        ) as client:
            available = await client.get("/api/v1/outbound-demo/availability")
            response = await client.post(
                "/api/v1/outbound-demo/calls",
                json=call_input(phone_number="+12025550123").model_dump(mode="json"),
            )
            return available, response

    available, response = asyncio.run(request())
    assert available.json() == {"available": False}
    assert response.status_code == 503
    sessions.assert_not_called()


@pytest.mark.parametrize("policy", ["allowlist", "consented_us"])
def test_website_supports_ai_only_calls_after_live_acceptance(policy: str) -> None:
    config = settings(
        outbound_demo_number_policy=policy,
        outbound_demo_website_enabled=True,
        outbound_demo_live_verified=True,
    )
    assert config.website_available
    assert not config.outbound_demo_transfer_enabled
    application, sessions = outbound_application(config)

    async def request() -> httpx.Response:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=application), base_url="http://test"
        ) as client:
            return await client.get(
                "/api/v1/outbound-demo/availability",
                headers={
                    "X-Outbound-Demo-Key": SECRET,
                    "X-Outbound-Visitor": "a" * 43,
                },
            )

    assert asyncio.run(request()).json() == {"available": True}
    sessions.assert_not_called()


def test_website_with_transfer_still_requires_transfer_acceptance() -> None:
    with pytest.raises(ValidationError, match="transfer acceptance when enabled"):
        settings(
            outbound_demo_website_enabled=True,
            outbound_demo_live_verified=True,
            outbound_demo_transfer_enabled=True,
            outbound_demo_carrier_limit_confirmed=True,
        )


@pytest.mark.parametrize("missing", ["telnyx_verify_api_key", "telnyx_verify_profile_id"])
def test_public_callbacks_require_sms_configuration(missing: str) -> None:
    with pytest.raises(ValidationError, match="Telnyx SMS configuration"):
        settings(**{
            "outbound_demo_website_enabled": True,
            "outbound_demo_live_verified": True, missing: None,
        })


@pytest.mark.parametrize("credential", ["missing", "bridge", "visitor"])
def test_public_callback_routes_require_bridge_and_visitor_credentials(
    credential: str,
) -> None:
    application, sessions = outbound_application(
        settings(
            outbound_demo_number_policy="consented_us",
            outbound_demo_website_enabled=True,
            outbound_demo_live_verified=True,
        )
    )
    headers = {"X-Outbound-Demo-Key": SECRET, "X-Outbound-Visitor": "a" * 43}
    if credential == "missing":
        headers = {}
    elif credential == "bridge":
        headers["X-Outbound-Demo-Key"] = "wrong"
    else:
        headers["X-Outbound-Visitor"] = "invalid"

    async def request() -> tuple[httpx.Response, httpx.Response]:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=application),
            base_url="http://test",
            headers=headers,
        ) as client:
            return (
                await client.get("/api/v1/outbound-demo/availability"),
                await client.post(
                    "/api/v1/outbound-demo/calls",
                    json=call_input(phone_number="+12025550123").model_dump(
                        mode="json"
                    ),
                ),
            )

    for response in asyncio.run(request()):
        assert response.status_code == (400 if credential == "visitor" else 401)
    sessions.assert_not_called()


@pytest.mark.parametrize(
    "trunk_overrides,caller,accepted",
    [
        ({}, "+12125550123", True),
        ({"transport": "tcp"}, "+12125550123", False),
        ({"transport": "udp"}, "+12125550123", False),
        ({"has_auth_credentials": False}, "+12125550123", False),
        ({"has_auth_credentials": "true"}, "+12125550123", False),
        ({"address": "other.example.test"}, "+12125550123", False),
        ({}, "+12025550123", False),
        ({}, None, False),
        ({}, "", False),
        ({}, "12125550123", False),
    ],
)
def test_consented_us_preflight_preserves_tls_digest_and_caller_loop_protection(
    trunk_overrides: dict[str, Any], caller: str | None, accepted: bool
) -> None:
    config = settings(
        outbound_demo_number_policy="consented_us", outbound_demo_allowed_numbers=""
    )
    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.startswith("/v1/convai/agents/"):
            return httpx.Response(200, json=agent_config_with_extensions())
        return httpx.Response(
            200,
            json={
                "phone_number_id": config.outbound_demo_phone_number_id,
                "provider": "sip_trunk",
                "phone_number": caller,
                "outbound_trunk": {
                    "address": "sip.telnyx.com",
                    "transport": "tls",
                    "has_auth_credentials": True,
                    **trunk_overrides,
                },
            },
        )

    with httpx.Client(
        base_url="https://api.elevenlabs.io", transport=httpx.MockTransport(handle)
    ) as client:
        provider = ElevenLabsOutboundProvider(config, client)
        if accepted:
            provider.preflight("+12025550123")
        else:
            with pytest.raises(OutboundProviderError) as caught:
                provider.preflight("+12025550123")
            assert caught.value.outcome_unknown is False
    assert all(request.method == "GET" for request in requests)
    assert all(request.headers["xi-api-key"] == "synthetic-api-key" for request in requests)
