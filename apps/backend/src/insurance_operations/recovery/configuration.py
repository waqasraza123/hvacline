import ipaddress
import re
from typing import TYPE_CHECKING
from urllib.parse import urlsplit
from uuid import UUID

if TYPE_CHECKING:
    from insurance_operations.settings import DatabaseSettings


def validate_transport(settings: "DatabaseSettings") -> None:
    for origin in (settings.recovery_public_api_origin, settings.recovery_web_origin):
        if origin:
            parsed = urlsplit(origin)
            if (
                parsed.scheme != "https" or not parsed.hostname
                or parsed.username or parsed.password or parsed.query or parsed.fragment
                or parsed.path not in {"", "/"} or parsed.port not in {None, 443}
            ):
                raise ValueError("Recovery origins require an exact public HTTPS origin")
            try:
                ipaddress.ip_address(parsed.hostname)
            except ValueError:
                if parsed.hostname == "localhost" or parsed.hostname.endswith((".localhost", ".local", ".internal")):
                    raise ValueError("Recovery origins require a public DNS hostname") from None
            else:
                raise ValueError("Recovery origins require a public DNS hostname")
    for number in (settings.recovery_sms_from_number, settings.recovery_voice_from_number):
        if number and not re.fullmatch(r"\+[1-9][0-9]{7,14}", number):
            raise ValueError("Recovery sender numbers require E.164")
    if settings.recovery_twilio_account_sid and not re.fullmatch(
        r"AC[0-9a-fA-F]{32}", settings.recovery_twilio_account_sid
    ):
        raise ValueError("Invalid recovery Twilio account SID")
    if settings.recovery_sms_enabled or settings.recovery_voice_enabled:
        if not all((settings.recovery_agency_id, settings.recovery_public_api_origin,
                    settings.recovery_web_origin, settings.recovery_token_encryption_key)):
            raise ValueError("Recovery delivery needs an agency, HTTPS origins and encryption key")
        configured_web_origin = getattr(settings, "web_origin", None)
        if configured_web_origin and str(settings.recovery_web_origin).rstrip("/") != str(configured_web_origin).rstrip("/"):
            raise ValueError("Recovery web origin must match the application's configured web origin")
        from insurance_operations.settings import RuntimeEnvironment

        if settings.app_environment is RuntimeEnvironment.PRODUCTION:
            raise ValueError("Recovery retains the existing development administrator identity gate")
    if settings.recovery_sms_enabled and not all((
        settings.recovery_sms_compliance_confirmed, settings.recovery_twilio_account_sid,
        settings.recovery_twilio_auth_token, settings.recovery_sms_from_number,
    )):
        raise ValueError("Recovery SMS requires a messaging account, sender and compliance acknowledgement")
    if settings.recovery_voice_enabled:
        if not all((
            settings.recovery_voice_compliance_confirmed, settings.recovery_voice_api_key,
            settings.recovery_voice_agent_id, settings.recovery_voice_phone_number_id,
            settings.recovery_voice_from_number, settings.recovery_voice_tool_secret,
            settings.recovery_voice_webhook_secret, settings.recovery_voice_webhook_id,
        )):
            raise ValueError("Recovery voice requires a dedicated agent, number, tool/webhook secrets and compliance acknowledgement")
        if any(
            secret is None or len(secret.get_secret_value()) < 32
            for secret in (settings.recovery_voice_tool_secret, settings.recovery_voice_webhook_secret)
        ):
            raise ValueError("Recovery voice secrets require at least 32 characters")
        if settings.recovery_voice_tool_secret == settings.recovery_voice_webhook_secret:
            raise ValueError("Recovery voice tool and webhook secrets must differ")
        from insurance_operations.settings import RuntimeEnvironment

        if settings.app_environment is RuntimeEnvironment.PRODUCTION:
            raise ValueError("Recovery voice retains the existing development identity gate")
        for existing in ("elevenlabs_agent_id", "elevenlabs_phone_agent_id", "outbound_demo_agent_id"):
            if settings.recovery_voice_agent_id == getattr(settings, existing, None):
                raise ValueError("Recovery voice must use a dedicated agent")


def channel_configured(settings: "DatabaseSettings", agency_id: UUID, channel: str) -> bool:
    if agency_id != settings.recovery_agency_id:
        return False
    common = bool(settings.recovery_token_encryption_key and settings.recovery_public_api_origin and settings.recovery_web_origin)
    if channel == "SMS":
        return common and bool(settings.recovery_sms_enabled and settings.recovery_sms_compliance_confirmed
            and settings.recovery_twilio_account_sid and settings.recovery_twilio_auth_token and settings.recovery_sms_from_number)
    if channel == "VOICE":
        return common and bool(settings.recovery_voice_enabled and settings.recovery_voice_compliance_confirmed
            and settings.recovery_voice_api_key and settings.recovery_voice_agent_id and settings.recovery_voice_phone_number_id
            and settings.recovery_voice_from_number and settings.recovery_voice_tool_secret and settings.recovery_voice_webhook_secret
            and settings.recovery_voice_webhook_id)
    return False


def provider_status(settings: "DatabaseSettings", agency_id: UUID) -> dict[str, dict[str, object]]:
    return {
        channel: {
            "available": channel_configured(settings, agency_id, channel),
            "reason": (
                "Twilio messaging configured; signed receipts and explicit SMS permission are required."
                if channel == "SMS" and channel_configured(settings, agency_id, channel)
                else "Dedicated ElevenLabs recovery agent configured; every call preflights agent privacy, tools and telephony."
                if channel == "VOICE" and channel_configured(settings, agency_id, channel)
                else "Configure dedicated recovery messaging credentials, sender, HTTPS callbacks and compliance acknowledgement."
                if channel == "SMS" else "Configure a dedicated recovery voice agent, SIP number, signed callbacks and compliance acknowledgement."
            ),
        } for channel in ("SMS", "VOICE")
    }
