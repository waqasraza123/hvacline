from datetime import UTC, datetime, timedelta
from email.utils import format_datetime
from unittest.mock import MagicMock, patch
from typing import Any
from urllib.parse import urlencode
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from pydantic import ValidationError
from twilio.request_validator import RequestValidator

from insurance_operations.database.models.recovery import RecoveryAttempt, RecoveryGrant
from insurance_operations.errors import ApiError
from insurance_operations.recovery.configuration import channel_configured
from insurance_operations.recovery.continuation import Confirmation, SlotSelection
from insurance_operations.recovery.delivery_jobs import read_provider_outcome
from insurance_operations.recovery.domain import destination_digest
from insurance_operations.recovery.grants import authenticate, grant_token
from insurance_operations.recovery.inbox import decrypt_recipient, encrypt_recipient, event_fingerprint
from insurance_operations.recovery.providers import RecoveryContact, sms_message, VOICE_FIRST_MESSAGE, RECOVERY_VOICE_INSTRUCTIONS
from insurance_operations.recovery.transports import ElevenLabsRecoveryVoice, TransportFailure, TwilioRecoverySms
from insurance_operations.recovery.webhooks import PREFIX, explicit_voice_opt_out, record_incoming, record_voice, twilio_form
from insurance_operations.recovery.voice import RecoveryVoice, SpokenTurn
from insurance_operations.settings import DatabaseSettings


def transport_settings(**changes: object) -> DatabaseSettings:
    values: dict[str, Any] = {
        "_env_file": None, "app_environment": "development",
        "database_url": "postgresql://synthetic:synthetic@localhost/synthetic",
        "recovery_token_encryption_key": Fernet.generate_key().decode(),
        "recovery_agency_id": uuid4(), "recovery_public_api_origin": "https://api.example.test",
        "recovery_web_origin": "https://www.example.test", "recovery_twilio_account_sid": "AC" + "1" * 32,
        "recovery_twilio_auth_token": "synthetic-twilio-token", "recovery_sms_from_number": "+12025550124",
        "recovery_sms_enabled": True, "recovery_sms_compliance_confirmed": True,
        "recovery_voice_enabled": True, "recovery_voice_compliance_confirmed": True,
        "recovery_voice_api_key": "synthetic-elevenlabs-key", "recovery_voice_agent_id": "synthetic-recovery-agent",
        "recovery_voice_phone_number_id": "synthetic-sip-number", "recovery_voice_from_number": "+12025550125",
        "recovery_voice_tool_secret": "synthetic-tool-secret-with-32-characters",
        "recovery_voice_webhook_secret": "synthetic-webhook-secret-with-32-characters",
        "recovery_voice_webhook_id": "synthetic-webhook-id",
    }
    return DatabaseSettings(**(values | changes))


def contact(settings: DatabaseSettings) -> RecoveryContact:
    assert settings.recovery_agency_id is not None
    return RecoveryContact(settings.recovery_agency_id, uuid4(), uuid4(), "Synthetic HVAC", "+12025550123", "synthetic-key",
        attempt_id=uuid4(), grant_token="synthetic-context", configuration={
            "business_name": "Synthetic HVAC", "account_sid": settings.recovery_twilio_account_sid,
            "api_origin": settings.recovery_public_api_origin, "web_origin": settings.recovery_web_origin,
            "from_number": settings.recovery_sms_from_number,
        })


def signed_form(settings: DatabaseSettings, path: str, values: dict[str, str]) -> tuple[dict[str, str], bytes]:
    assert settings.recovery_twilio_auth_token is not None
    signature = RequestValidator(settings.recovery_twilio_auth_token.get_secret_value()).compute_signature(
        str(settings.recovery_public_api_origin) + path, values)
    return {"content-type": "application/x-www-form-urlencoded", "x-twilio-signature": signature}, urlencode(values).encode()


def test_transports_are_tenant_bound_and_do_not_activate_global_automation() -> None:
    settings = transport_settings()
    assert not settings.recovery_enabled
    assert channel_configured(settings, settings.recovery_agency_id, "SMS")
    assert not channel_configured(settings, uuid4(), "SMS")
    assert not channel_configured(settings, uuid4(), "VOICE")
    with pytest.raises(ValidationError):
        transport_settings(recovery_voice_agent_id="shared-agent", outbound_demo_agent_id="shared-agent")
    with pytest.raises(ValidationError):
        transport_settings(recovery_sms_compliance_confirmed=False)
    with pytest.raises(ValidationError):
        transport_settings(recovery_public_api_origin="http://127.0.0.1")


def test_sms_timeout_is_unknown_and_never_reposted() -> None:
    settings = transport_settings()
    with patch("insurance_operations.recovery.transports.json_request", side_effect=TransportFailure("PROVIDER_OUTCOME_UNRESOLVED", unknown=True)) as send:
        outcome = TwilioRecoverySms(settings).send(contact(settings))
    assert outcome.status == "UNKNOWN" and outcome.provider_reference is None
    send.assert_called_once()
    assert send.call_args.args[0] == "POST"


def test_sms_submission_is_queued_without_claiming_delivery_or_customer_response() -> None:
    settings = transport_settings()
    request = contact(settings)
    with patch("insurance_operations.recovery.transports.json_request", return_value={
        "sid": "SM" + "2" * 32, "status": "queued", "account_sid": settings.recovery_twilio_account_sid,
        "to": request.phone, "from": settings.recovery_sms_from_number,
    }) as send:
        outcome = TwilioRecoverySms(settings).send(request)
    assert outcome.status == "QUEUED"
    assert send.call_args.kwargs["data"]["StatusCallback"].endswith(f"/status/{request.attempt_id}")
    assert "STOP" in send.call_args.kwargs["data"]["Body"]


def test_voice_preflight_failure_never_places_a_call() -> None:
    settings = transport_settings()
    request = contact(settings)
    request = RecoveryContact(request.agency_id, request.case_id, request.request_id, request.business_name, request.phone,
        request.idempotency_key, request.attempt_id, request.grant_token, {
            "agent_id": settings.recovery_voice_agent_id, "phone_id": settings.recovery_voice_phone_number_id,
            "from_number": settings.recovery_voice_from_number, "api_origin": settings.recovery_public_api_origin})
    with patch.object(ElevenLabsRecoveryVoice, "preflight", side_effect=TransportFailure("RECOVERY_TOOLS_INVALID")), patch.object(ElevenLabsRecoveryVoice, "request") as send:
        outcome = ElevenLabsRecoveryVoice(settings).send(request)
    assert outcome.status == "FAILED" and outcome.failure_code == "RECOVERY_TOOLS_INVALID"
    send.assert_not_called()


def test_recovery_preflight_rejects_non_english_without_confirmed_language_permission() -> None:
    settings = transport_settings()
    adapter = ElevenLabsRecoveryVoice(settings)
    with patch.object(adapter, "request", return_value={
        "agent_id": settings.recovery_voice_agent_id,
        "conversation_config": {
            "agent": {"language": "es", "first_message": VOICE_FIRST_MESSAGE, "prompt": {"prompt": RECOVERY_VOICE_INSTRUCTIONS}},
            "conversation": {"max_duration_seconds": settings.recovery_voice_max_seconds},
        },
        "platform_settings": {
            "privacy": {"record_voice": False, "retention_days": 0},
            "auth": {"enable_auth": True},
            "workspace_overrides": {"webhooks": {"post_call_webhook_id": settings.recovery_voice_webhook_id, "events": ["transcript", "call_initiation_failure"]}},
        },
    }) as request:
        with pytest.raises(TransportFailure, match="RECOVERY_AGENT_CONFIGURATION_INVALID"):
            adapter.preflight(contact(settings))
    assert request.call_count == 1


def test_twilio_signatures_bind_exact_public_url_account_and_all_form_values() -> None:
    settings = transport_settings()
    path = PREFIX + "/twilio/incoming"
    values = {"AccountSid": str(settings.recovery_twilio_account_sid), "MessageSid": "SM" + "3" * 32,
        "From": "+12025550123", "To": str(settings.recovery_sms_from_number), "Body": "YES"}
    headers, body = signed_form(settings, path, values)
    assert twilio_form(settings, path, headers, body)["Body"] == "YES"
    for changed_path, changed_body in [(path + "/different", body), (path, body.replace(b"YES", b"STOP"))]:
        with pytest.raises(ApiError) as error:
            twilio_form(settings, changed_path, headers, changed_body)
        assert error.value.status_code == 401


def test_signed_stop_persists_only_sanitized_encrypted_evidence() -> None:
    settings = transport_settings()
    headers, body = signed_form(settings, PREFIX + "/twilio/incoming", {
        "AccountSid": str(settings.recovery_twilio_account_sid), "MessageSid": "SM" + "4" * 32,
        "From": "+12025550123", "To": str(settings.recovery_sms_from_number), "Body": "STOP",
    })
    with patch("insurance_operations.recovery.webhooks.enqueue") as enqueue:
        record_incoming(settings, MagicMock(), headers, body)
    assert enqueue.call_args.kwargs["kind"] == "STOP"
    data = enqueue.call_args.kwargs["data"]
    assert "+12025550123" not in str(data) and "STOP" not in str(data)
    assert decrypt_recipient(settings, settings.recovery_agency_id, data["recipient_ciphertext"]) == "+12025550123"


def test_randomized_encryption_does_not_break_duplicate_event_identity() -> None:
    settings = transport_settings()
    agency = settings.recovery_agency_id
    first = encrypt_recipient(settings, agency, "+12025550123")
    second = encrypt_recipient(settings, agency, "+12025550123")
    assert first != second
    assert event_fingerprint(settings, {"recipient_digest": "same", "recipient_ciphertext": first}) == event_fingerprint(settings, {"recipient_digest": "same", "recipient_ciphertext": second})
    with pytest.raises(ApiError):
        decrypt_recipient(settings, uuid4(), first)


def test_grant_capability_is_bound_to_tenant_channel_expiry_and_database_state() -> None:
    settings = transport_settings()
    grant = RecoveryGrant(id=uuid4(), agency_id=settings.recovery_agency_id, attempt_id=uuid4(), recovery_case_id=uuid4(),
        channel="SMS", status="ACTIVE", expires_at=datetime.now(UTC) + timedelta(minutes=30))
    token = grant_token(settings, grant)
    session = MagicMock()
    session.scalar.return_value = grant
    assert authenticate(session, settings, token) is grant
    grant.channel = "VOICE"
    with pytest.raises(ApiError):
        authenticate(session, settings, token)
    grant.channel, grant.status = "SMS", "REVOKED"
    with pytest.raises(ApiError):
        authenticate(session, settings, token)


def test_confirmation_requires_boolean_and_offset_aware_selection() -> None:
    with pytest.raises(ValidationError):
        Confirmation(expected_row_version=1, nonce=uuid4(), explicit_confirmation="true")
    with pytest.raises(ValidationError):
        SlotSelection(expected_row_version=1, team_key="team-a", starts_at="2026-11-23T10:00:00")


@pytest.mark.parametrize("message,expected", [("Stop calling me.", True), ("Do not call me", True), ("Don't call me", True),
    ("The AC stopped working", False), ("Don't stop calling me", False), ("yes", False)])
def test_signed_voice_fallback_uses_only_explicit_customer_opt_out(message: str, expected: bool) -> None:
    assert explicit_voice_opt_out([{"role": "user", "message": message}]) is expected
    assert not explicit_voice_opt_out([{"role": "agent", "message": message}])


def test_authoritative_sms_lookup_cannot_bind_another_destination_or_old_message() -> None:
    settings = transport_settings()
    now = datetime.now(UTC)
    attempt = RecoveryAttempt(id=uuid4(), agency_id=settings.recovery_agency_id, provider="TWILIO_SMS", started_at=now,
        recipient_digest=destination_digest(settings, settings.recovery_agency_id, "+12025550123"),
        dispatch_configuration={"account_sid": settings.recovery_twilio_account_sid, "from_number": settings.recovery_sms_from_number,
            "business_name": "Synthetic HVAC"})
    result = {"from": settings.recovery_sms_from_number, "to": "+12025550126", "body": sms_message("Synthetic HVAC"),
        "date_created": format_datetime(now), "status": "sent"}
    with patch.object(TwilioRecoverySms, "message", return_value=result):
        with pytest.raises(TransportFailure, match="SMS_RECEIPT_MISMATCH"):
            read_provider_outcome(settings, attempt, "SM" + "6" * 32)
    result.update(to="+12025550123", date_created=format_datetime(now - timedelta(days=1)))
    with patch.object(TwilioRecoverySms, "message", return_value=result):
        with pytest.raises(TransportFailure, match="SMS_RECEIPT_MISMATCH"):
            read_provider_outcome(settings, attempt, "SM" + "6" * 32)


def test_voice_confirmation_requires_the_actual_complete_readback_and_customer_yes() -> None:
    settings = transport_settings()
    grant = RecoveryGrant(id=uuid4(), agency_id=settings.recovery_agency_id, attempt_id=uuid4(), channel="VOICE",
        status="ACTIVE", expires_at=datetime.now(UTC) + timedelta(minutes=5))
    sessions = MagicMock()
    sessions.return_value.__enter__.return_value.scalar.return_value = grant
    voice = RecoveryVoice(sessions, settings)
    token, nonce = grant_token(settings, grant), uuid4()
    readback = "Please confirm your appointment on Monday at ten. May I confirm this appointment?"
    with patch("insurance_operations.recovery.voice.RecoveryContinuation.current_readback", return_value=readback):
        for turns in [[SpokenTurn("USER", "yes")], [SpokenTurn("AGENT", "Monday at ten?"), SpokenTurn("USER", "yes")],
                [SpokenTurn("AGENT", readback), SpokenTurn("USER", "yes but change the address")]]:
            with patch.object(voice, "turns", return_value=turns), pytest.raises(ApiError):
                voice.verify_confirmation(token, "synthetic-conversation", nonce)
        with patch.object(voice, "turns", return_value=[SpokenTurn("AGENT", readback), SpokenTurn("USER", "yes")]):
            voice.verify_confirmation(token, "synthetic-conversation", nonce)


def test_signed_post_call_ingress_drops_transcript_and_secret_dynamic_variables() -> None:
    settings = transport_settings()
    attempt = RecoveryAttempt(id=uuid4(), agency_id=settings.recovery_agency_id, provider="ELEVENLABS_RECOVERY",
        provider_reference="synthetic-conversation", dispatch_configuration={"agent_id": settings.recovery_voice_agent_id})
    sessions = MagicMock()
    sessions.return_value.__enter__.return_value.scalar.return_value = attempt
    payload = {"type": "post_call_transcription", "data": {"conversation_id": "synthetic-conversation",
        "agent_id": settings.recovery_voice_agent_id, "status": "done", "transcript": [{"role": "user", "message": "synthetic private transcript"}],
        "conversation_initiation_client_data": {"dynamic_variables": {"recovery_attempt_id": str(attempt.id), "secret__recovery_context": "synthetic-private-capability"}}}}
    with patch("insurance_operations.recovery.webhooks.ElevenLabsPhoneProvider.verify_post_call_webhook", return_value=payload) as verify, patch("insurance_operations.recovery.webhooks.enqueue") as enqueue:
        record_voice(settings, sessions, {"elevenlabs-signature": "synthetic-signature"}, b"synthetic-original-body")
    verify.assert_called_once_with(headers={"elevenlabs-signature": "synthetic-signature"}, body=b"synthetic-original-body")
    persisted = str(enqueue.call_args.kwargs)
    assert "synthetic-private-capability" not in persisted and "synthetic private transcript" not in persisted
    assert "secret__" not in persisted
