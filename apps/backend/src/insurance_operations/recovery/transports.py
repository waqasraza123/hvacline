import json
import re
from typing import Any
from urllib.parse import quote
from uuid import UUID

import httpx

from insurance_operations.job_execution import JobDeadlineExceeded, check_job_deadline, provider_client
from insurance_operations.errors import ApiError
from insurance_operations.recovery.configuration import channel_configured
from insurance_operations.recovery.providers import DeliveryOutcome, RecoveryContact, RECOVERY_VOICE_INSTRUCTIONS, VOICE_FIRST_MESSAGE, sms_message
from insurance_operations.settings import DatabaseSettings
from insurance_operations.telephony.outbound.destinations import validate_us_destination

SMS_STATUSES = {"accepted": "QUEUED", "scheduled": "QUEUED", "queued": "QUEUED", "sending": "QUEUED", "sent": "SENT", "delivered": "DELIVERED", "undelivered": "FAILED", "failed": "FAILED", "canceled": "FAILED"}
VOICE_TOOLS = {f"recovery_{name}" for name in ("continue", "context", "availability", "reserve", "readback", "confirm", "release", "finish")}


class TransportFailure(RuntimeError):
    def __init__(self, code: str, *, unknown: bool = False) -> None:
        super().__init__(code)
        self.code, self.unknown = code, unknown


def json_request(method: str, url: str, *, auth: tuple[str, str] | None = None, headers: dict[str, str] | None = None,
                 data: dict[str, str] | None = None, payload: dict[str, object] | None = None) -> dict[str, Any]:
    check_job_deadline()
    try:
        with provider_client() as client, client.stream(method, url, auth=auth, headers=headers, data=data,
                json=payload, follow_redirects=False, timeout=httpx.Timeout(8, connect=3)) as response:
            if response.status_code >= 300:
                raise TransportFailure("PROVIDER_REJECTED", unknown=method == "POST" and response.status_code not in {400, 401, 403, 404, 422, 429})
            content = bytearray()
            for chunk in response.iter_bytes():
                check_job_deadline()
                content.extend(chunk)
                if len(content) > 262144:
                    raise ValueError
            result = json.loads(content)
            if not isinstance(result, dict):
                raise ValueError
            return result
    except TransportFailure:
        raise
    except (httpx.HTTPError, ValueError, TypeError):
        raise TransportFailure("PROVIDER_OUTCOME_UNRESOLVED", unknown=method == "POST") from None


class TwilioRecoverySms:
    def __init__(self, settings: DatabaseSettings) -> None:
        self.settings = settings

    def _auth(self) -> tuple[str, str]:
        if not self.settings.recovery_twilio_account_sid or not self.settings.recovery_twilio_auth_token:
            raise TransportFailure("SMS_PROVIDER_UNAVAILABLE")
        return self.settings.recovery_twilio_account_sid, self.settings.recovery_twilio_auth_token.get_secret_value()

    def send(self, contact: RecoveryContact, *, body: str | None = None, reply_grant_id: UUID | None = None) -> DeliveryOutcome:
        if not channel_configured(self.settings, contact.agency_id, "SMS") or contact.attempt_id is None:
            return DeliveryOutcome("FAILED", failure_code="SMS_PROVIDER_UNAVAILABLE")
        configuration = contact.configuration or {}
        expected = {"account_sid": self.settings.recovery_twilio_account_sid,
            "from_number": self.settings.recovery_sms_from_number,
            "api_origin": self.settings.recovery_public_api_origin,
            "web_origin": self.settings.recovery_web_origin}
        if any(configuration.get(key) != value for key, value in expected.items()) or contact.phone == expected["from_number"]:
            return DeliveryOutcome("FAILED", failure_code="SMS_CONFIGURATION_CHANGED")
        try:
            validate_us_destination(contact.phone)
        except ApiError:
            return DeliveryOutcome("FAILED", failure_code="RECOVERY_RECIPIENT_INVALID")
        callback = f"{str(expected['api_origin']).rstrip('/')}/api/v1/providers/recovery/twilio/"
        callback += f"reply-status/{reply_grant_id}" if reply_grant_id else f"status/{contact.attempt_id}"
        account, _ = self._auth()
        try:
            result = json_request("POST", f"https://api.twilio.com/2010-04-01/Accounts/{account}/Messages.json", auth=self._auth(),
                data={"To": contact.phone, "From": str(expected["from_number"]),
                      "Body": body if body is not None else sms_message(contact.business_name), "StatusCallback": callback})
            sid = result.get("sid")
            if not isinstance(sid, str) or not re.fullmatch(r"SM[0-9a-fA-F]{32}", sid) or result.get("account_sid") != account or result.get("to") != contact.phone or result.get("from") != expected["from_number"]:
                raise TransportFailure("SMS_RECEIPT_INVALID", unknown=True)
            status = SMS_STATUSES.get(str(result.get("status")), "UNKNOWN")
            return DeliveryOutcome(status, sid, "PROVIDER_REPORTED_FAILURE" if status == "FAILED"
                else "PROVIDER_OUTCOME_UNRESOLVED" if status == "UNKNOWN" else None)
        except TransportFailure as error:
            return DeliveryOutcome("UNKNOWN" if error.unknown else "FAILED", failure_code=error.code)

    def message(self, reference: str) -> dict[str, Any]:
        if not re.fullmatch(r"SM[0-9a-fA-F]{32}", reference):
            raise TransportFailure("SMS_REFERENCE_INVALID")
        account, _ = self._auth()
        result = json_request("GET", f"https://api.twilio.com/2010-04-01/Accounts/{account}/Messages/{reference}.json", auth=self._auth())
        if result.get("account_sid") != account or result.get("sid") != reference:
            raise TransportFailure("SMS_RECEIPT_INVALID")
        return result


class ElevenLabsRecoveryVoice:
    def __init__(self, settings: DatabaseSettings) -> None:
        self.settings = settings

    def request(self, method: str, path: str, payload: dict[str, object] | None = None) -> dict[str, Any]:
        secret = self.settings.recovery_voice_api_key
        if secret is None:
            raise TransportFailure("VOICE_PROVIDER_UNAVAILABLE")
        return json_request(method, "https://api.elevenlabs.io" + path,
            headers={"xi-api-key": secret.get_secret_value()}, payload=payload)

    def preflight(self, contact: RecoveryContact) -> None:
        s = self.settings
        agent = self.request("GET", f"/v1/convai/agents/{quote(s.recovery_voice_agent_id or '', safe='')}")
        config = agent.get("conversation_config") or {}
        agent_config = config.get("agent") or {}
        prompt = agent_config.get("prompt") or {}
        platform = agent.get("platform_settings") or {}
        privacy = platform.get("privacy") or {}
        workspace = platform.get("workspace_overrides") or {}
        hooks = workspace.get("webhooks") or {}
        duration = (config.get("conversation") or {}).get("max_duration_seconds")
        if (agent.get("agent_id") != s.recovery_voice_agent_id or agent_config.get("first_message") != VOICE_FIRST_MESSAGE
            or str(prompt.get("prompt", "")).strip() != RECOVERY_VOICE_INSTRUCTIONS.strip()
            or type(duration) is not int or not 1 <= duration <= s.recovery_voice_max_seconds
            or privacy.get("record_voice") is not False or privacy.get("retention_days") != 0
            or (platform.get("auth") or {}).get("enable_auth") is not True
            or agent.get("workflow") or agent.get("procedures") or prompt.get("knowledge_base")
            or prompt.get("mcp_server_ids") or config.get("language_presets")
            or (workspace.get("conversation_initiation_client_data_webhook") or {}).get("url")
            or hooks.get("post_call_webhook_id") != s.recovery_voice_webhook_id
            or set(hooks.get("events") or []) != {"transcript", "call_initiation_failure"}):
            raise TransportFailure("RECOVERY_AGENT_CONFIGURATION_INVALID")
        tools = list(prompt.get("tools") or [])
        ids = prompt.get("tool_ids") or []
        if not isinstance(ids, list) or len(ids) > 9 or not all(isinstance(identifier, str) for identifier in ids):
            raise TransportFailure("RECOVERY_TOOLS_INVALID")
        for identifier in ids:
            tools.append(self.request("GET", f"/v1/convai/tools/{quote(identifier, safe='')}").get("tool_config"))
        tools.extend((prompt.get("built_in_tools") or {}).values())
        found: set[str] = set()
        ended = False
        for tool in tools:
            if not isinstance(tool, dict):
                raise TransportFailure("RECOVERY_TOOLS_INVALID")
            if tool.get("type") == "system" and (tool.get("params") or {}).get("system_tool_type") == "end_call":
                ended = True
                continue
            name = tool.get("name")
            api = tool.get("api_schema") or {}
            headers = api.get("request_headers") or {}
            if (tool.get("type") != "webhook" or name not in VOICE_TOOLS or name in found
                or api.get("method") != "POST"
                or api.get("url") != f"{str(s.recovery_public_api_origin).rstrip('/')}/api/v1/providers/recovery/voice/tools/{str(name).removeprefix('recovery_')}"
                or headers.get("X-Recovery-Context") != {"variable_name": "secret__recovery_context"}
                or headers.get("X-Recovery-Conversation") != {"variable_name": "system__conversation_id"}
                or not isinstance(headers.get("Authorization"), dict)
                or not headers["Authorization"].get("secret_id")):
                raise TransportFailure("RECOVERY_TOOLS_INVALID")
            found.add(str(name))
        if found != VOICE_TOOLS or not ended:
            raise TransportFailure("RECOVERY_TOOLS_INVALID")
        phone = self.request("GET", f"/v1/convai/phone-numbers/{quote(s.recovery_voice_phone_number_id or '', safe='')}")
        trunk = phone.get("outbound_trunk") or {}
        if (phone.get("phone_number_id") != s.recovery_voice_phone_number_id or phone.get("provider") != "sip_trunk"
            or phone.get("phone_number") != s.recovery_voice_from_number or phone.get("phone_number") == contact.phone
            or trunk.get("transport") != "tls" or trunk.get("has_auth_credentials") is not True):
            raise TransportFailure("RECOVERY_PHONE_CONFIGURATION_INVALID")

    def send(self, contact: RecoveryContact) -> DeliveryOutcome:
        s = self.settings
        if not channel_configured(s, contact.agency_id, "VOICE") or not contact.attempt_id or not contact.grant_token:
            return DeliveryOutcome("FAILED", failure_code="VOICE_PROVIDER_UNAVAILABLE")
        configuration = contact.configuration or {}
        if any(configuration.get(key) != value for key, value in {
            "agent_id": s.recovery_voice_agent_id, "phone_id": s.recovery_voice_phone_number_id,
            "from_number": s.recovery_voice_from_number, "api_origin": s.recovery_public_api_origin,
        }.items()):
            return DeliveryOutcome("FAILED", failure_code="VOICE_CONFIGURATION_CHANGED")
        try:
            validate_us_destination(contact.phone)
            self.preflight(contact)
        except TransportFailure as error:
            return DeliveryOutcome("FAILED", failure_code=error.code)
        except (ApiError, JobDeadlineExceeded, ValueError, TypeError, AttributeError):
            return DeliveryOutcome("FAILED", failure_code="RECOVERY_AGENT_CONFIGURATION_INVALID")
        try:
            result = self.request("POST", "/v1/convai/sip-trunk/outbound-call", {
                "agent_id": s.recovery_voice_agent_id, "agent_phone_number_id": s.recovery_voice_phone_number_id,
                "to_number": contact.phone, "telephony_call_config": {"ringing_timeout_secs": 25},
                "conversation_initiation_client_data": {"dynamic_variables": {
                    "recovery_attempt_id": str(contact.attempt_id), "recovery_business_name": contact.business_name,
                    "secret__recovery_context": contact.grant_token,
                }},
            })
            reference = result.get("conversation_id")
            if result.get("success") is not True or not isinstance(reference, str) or not 1 <= len(reference) <= 200:
                raise TransportFailure("VOICE_RECEIPT_INVALID", unknown=True)
            return DeliveryOutcome("SENT", reference)
        except TransportFailure as error:
            return DeliveryOutcome("UNKNOWN" if error.unknown else "FAILED", failure_code=error.code)
        except (JobDeadlineExceeded, ValueError, TypeError, AttributeError):
            return DeliveryOutcome("UNKNOWN", failure_code="PROVIDER_OUTCOME_UNRESOLVED")

    def conversation(self, reference: str) -> dict[str, Any]:
        data = self.request("GET", f"/v1/convai/conversations/{quote(reference, safe='')}")
        if data.get("conversation_id") != reference or data.get("agent_id") != self.settings.recovery_voice_agent_id:
            raise TransportFailure("VOICE_REFERENCE_MISMATCH")
        return data


class ConfiguredRecoveryProvider:
    def __init__(self, settings: DatabaseSettings) -> None:
        self.settings = settings

    def available(self, agency_id: UUID, channel: str) -> bool:
        return channel_configured(self.settings, agency_id, channel)

    def send(self, contact: RecoveryContact, channel: str) -> DeliveryOutcome:
        if channel == "SMS":
            return TwilioRecoverySms(self.settings).send(contact)
        if channel == "VOICE":
            return ElevenLabsRecoveryVoice(self.settings).send(contact)
        return DeliveryOutcome("FAILED", failure_code="RECOVERY_CHANNEL_UNSUPPORTED")
