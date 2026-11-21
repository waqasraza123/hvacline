import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import httpx

from insurance_operations.telephony.contracts import TelephonyAdapterError
from insurance_operations.telephony.outbound.destinations import E164
from insurance_operations.telephony.outbound.prompt import (
    DEMO_PROMPT,
    FIRST_MESSAGE,
    TRANSFER_CONDITION,
)
from insurance_operations.telephony.outbound.schemas import DemoCallInput
from insurance_operations.telephony.outbound.settings import OutboundDemoSettings
from insurance_operations.telephony.providers.elevenlabs import (
    ELEVENLABS_API_BASE_URL,
    ElevenLabsPhoneProvider,
)


class OutboundProviderError(RuntimeError):
    def __init__(self, *, outcome_unknown: bool) -> None:
        super().__init__("Outbound provider unavailable")
        self.outcome_unknown = outcome_unknown


@dataclass(frozen=True)
class OutboundCallReceipt:
    conversation_id: str
    sip_call_id: str


def object_value(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def validate_agent(agent: dict[str, Any], settings: OutboundDemoSettings) -> None:
    configuration = object_value(agent.get("conversation_config"))
    conversation = object_value(configuration.get("conversation"))
    agent_config = object_value(configuration.get("agent"))
    prompt = object_value(agent_config.get("prompt"))
    platform = object_value(agent.get("platform_settings"))
    privacy = object_value(platform.get("privacy"))
    workspace = object_value(platform.get("workspace_overrides"))
    hooks = object_value(workspace.get("webhooks"))
    duration = conversation.get("max_duration_seconds")
    if (
        agent.get("agent_id") != settings.outbound_demo_agent_id
        or type(duration) is not int
        or not 1 <= duration <= settings.outbound_demo_max_duration_seconds
        or agent_config.get("first_message") != FIRST_MESSAGE
        or str(prompt.get("prompt", "")).strip() != DEMO_PROMPT.strip()
        or privacy.get("record_voice") is not False
        or privacy.get("retention_days") != 0
        or object_value(platform.get("auth")).get("enable_auth") is not True
        or prompt.get("knowledge_base")
        or configuration.get("language_presets")
        or agent.get("procedures")
        or object_value(
            workspace.get("conversation_initiation_client_data_webhook")
        ).get("url")
        or not hooks.get("post_call_webhook_id")
        or not {"transcript", "call_initiation_failure"}.issubset(
            hooks.get("events") or []
        )
    ):
        raise OutboundProviderError(outcome_unknown=False)
    explicit_tools = prompt.get("tools") or []
    if not isinstance(explicit_tools, list):
        raise OutboundProviderError(outcome_unknown=False)
    tools = list(explicit_tools)
    tools.extend(
        value
        for value in object_value(prompt.get("built_in_tools")).values()
        if value is not None
    )
    found: set[str] = set()
    for tool in tools:
        if not isinstance(tool, dict):
            raise OutboundProviderError(outcome_unknown=False)
        config = tool
        if config.get("type") != "system":
            continue
        params = object_value(config.get("params"))
        kind = params.get("system_tool_type")
        if kind == "end_call":
            found.add("end_call")
        if kind == "transfer_to_number":
            found.add("transfer_to_number")
            transfers = params.get("transfers")
            if (
                not settings.outbound_demo_transfer_enabled
                or not isinstance(transfers, list)
                or len(transfers) != 1
            ):
                raise OutboundProviderError(outcome_unknown=False)
            rule = object_value(transfers[0])
            destination = object_value(rule.get("transfer_destination"))
            if (
                destination
                != {
                    "type": "phone",
                    "phone_number": (
                        settings.outbound_demo_human_number.get_secret_value()
                    ),
                }
                or rule.get("transfer_type") != "sip_refer"
                or rule.get("condition") != TRANSFER_CONDITION
                or rule.get("custom_sip_headers")
                or rule.get("uui")
                or rule.get("post_dial_digits")
                or rule.get("phone_number")
            ):
                raise OutboundProviderError(outcome_unknown=False)
    if "end_call" not in found or (
        settings.outbound_demo_transfer_enabled and "transfer_to_number" not in found
    ):
        raise OutboundProviderError(outcome_unknown=False)


class ElevenLabsOutboundProvider:
    def __init__(
        self, settings: OutboundDemoSettings, client: httpx.Client | None = None
    ) -> None:
        self.settings = settings
        self.client = client

    def _request(
        self, method: str, path: str, payload: dict[str, object] | None = None
    ) -> httpx.Response:
        secret = self.settings.elevenlabs_api_key
        if secret is None:
            raise OutboundProviderError(outcome_unknown=False)
        client = self.client or httpx.Client(
            base_url=ELEVENLABS_API_BASE_URL,
            timeout=httpx.Timeout(12),
            follow_redirects=False,
        )
        try:
            return client.request(
                method,
                path,
                headers={"xi-api-key": secret.get_secret_value()},
                json=payload,
            )
        finally:
            if self.client is None:
                client.close()

    def preflight(self, phone_number: str) -> None:
        agent_id = quote(self.settings.outbound_demo_agent_id or "", safe="")
        phone_id = quote(self.settings.outbound_demo_phone_number_id or "", safe="")
        try:
            agent = self._request(
                "GET",
                f"/v1/convai/agents/{agent_id}",
            )
            agent.raise_for_status()
            validate_agent(object_value(agent.json()), self.settings)
            phone = self._request(
                "GET",
                f"/v1/convai/phone-numbers/{phone_id}",
            )
            phone.raise_for_status()
            value = object_value(phone.json())
            trunk = object_value(value.get("outbound_trunk"))
            caller = value.get("phone_number")
            human = self.settings.outbound_demo_human_number.get_secret_value()
            if (
                value.get("phone_number_id")
                != self.settings.outbound_demo_phone_number_id
                or value.get("provider") != "sip_trunk"
                or trunk.get("address") != "sip.telnyx.com"
                or trunk.get("transport") != "tls"
                or trunk.get("has_auth_credentials") is not True
                or not isinstance(caller, str)
                or E164.fullmatch(caller) is None
                or caller in (phone_number, human)
                or caller in self.settings.allowed_numbers
            ):
                raise OutboundProviderError(outcome_unknown=False)
        except (httpx.HTTPError, ValueError, TypeError) as error:
            raise OutboundProviderError(outcome_unknown=False) from error

    def dial(self, data: DemoCallInput, call_id: str) -> OutboundCallReceipt:
        settings = self.settings
        try:
            response = self._request(
                "POST",
                "/v1/convai/sip-trunk/outbound-call",
                {
                    "agent_id": settings.outbound_demo_agent_id,
                    "agent_phone_number_id": settings.outbound_demo_phone_number_id,
                    "to_number": data.phone_number,
                    "telephony_call_config": {
                        "ringing_timeout_secs": settings.outbound_demo_ringing_seconds
                    },
                    "conversation_initiation_client_data": {
                        "dynamic_variables": {
                            "outbound_demo_call_id": call_id,
                            "demo_scenario": data.scenario.value,
                            "demo_transfer_enabled": (
                                settings.outbound_demo_transfer_enabled
                            ),
                            "demo_max_duration_seconds": (
                                settings.outbound_demo_max_duration_seconds
                            ),
                        }
                    },
                },
            )
        except httpx.HTTPError as error:
            raise OutboundProviderError(outcome_unknown=True) from error
        # An undocumented error or malformed response may follow a successful dial.
        if response.status_code >= 400:
            raise OutboundProviderError(
                outcome_unknown=response.status_code
                not in {400, 401, 403, 404, 422, 429}
            )
        try:
            receipt = object_value(response.json())
            conversation_id = receipt.get("conversation_id")
            sip_call_id = receipt.get("sip_call_id")
            if (
                receipt.get("success") is not True
                or not isinstance(conversation_id, str)
                or not 1 <= len(conversation_id) <= 200
                or not isinstance(sip_call_id, str)
                or not 1 <= len(sip_call_id) <= 512
            ):
                raise OutboundProviderError(outcome_unknown=True)
            return OutboundCallReceipt(conversation_id, sip_call_id)
        except (ValueError, TypeError) as error:
            raise OutboundProviderError(outcome_unknown=True) from error

    def conversation(self, conversation_id: str) -> dict[str, Any]:
        try:
            response = self._request(
                "GET", f"/v1/convai/conversations/{quote(conversation_id, safe='')}"
            )
            response.raise_for_status()
            data = object_value(response.json())
            if (
                data.get("agent_id") != self.settings.outbound_demo_agent_id
                or data.get("conversation_id") != conversation_id
            ):
                raise OutboundProviderError(outcome_unknown=True)
            return data
        except (httpx.HTTPError, ValueError, TypeError) as error:
            raise OutboundProviderError(outcome_unknown=True) from error

    def verify_webhook(
        self, headers: Mapping[str, str], body: bytes
    ) -> dict[str, object]:
        secret = self.settings.outbound_demo_webhook_secret
        if secret is None:
            raise TelephonyAdapterError("Outbound webhook unavailable")
        return ElevenLabsPhoneProvider(
            api_key=None,
            agent_id=self.settings.outbound_demo_agent_id or "",
            post_call_webhook_secret=secret.get_secret_value(),
        ).verify_post_call_webhook(headers=headers, body=body)


def _transcript_objects(value: object) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise ValueError("Invalid demo call transcript")
    return value


def transfer_outcome(data: dict[str, Any], human_number: str) -> str:
    outcomes: set[str] = set()
    pending: set[str] = set()
    answered: set[str] = set()
    for turn in _transcript_objects(data.get("transcript")):
        for call in _transcript_objects(turn.get("tool_calls")):
            if call.get("tool_name") == "transfer_to_number":
                pending.add(str(call.get("request_id", "missing")))
        for value in _transcript_objects(turn.get("tool_results")):
            if value.get("tool_name") != "transfer_to_number":
                continue
            answered.add(str(value.get("request_id", "missing")))
            result = object_value(value.get("result"))
            if not result:
                try:
                    result = object_value(json.loads(value.get("result_value", "")))
                except (ValueError, TypeError):
                    result = {}
            if (
                value.get("is_error") is True
                or result.get("result_type") == "transfer_to_number_error"
            ):
                outcomes.add("failed")
            elif (
                result.get("result_type") == "transfer_to_number_sip_success"
                and result.get("transfer_number") == human_number
            ):
                # REFER acceptance does not establish that a human answered.
                outcomes.add("refer_accepted")
            else:
                outcomes.add("unconfirmed")
    if pending - answered:
        outcomes.add("unconfirmed")
    for outcome in ("refer_accepted", "unconfirmed", "failed"):
        if outcome in outcomes:
            return outcome
    return "not_requested"
