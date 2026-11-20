from datetime import UTC, datetime, time
from unittest.mock import patch
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr, ValidationError
from sqlalchemy.orm import sessionmaker

from insurance_operations.database.models.recovery import RecoveryAiConnection, RecoveryPermission
from insurance_operations.errors import ApiError
from insurance_operations.recovery.ai import RecoveryAiService, address_allowed, chat_completion, endpoint_for, public_addresses
from insurance_operations.recovery.domain import channel_allowed, contact_time
from insurance_operations.recovery.providers import UnavailableRecoveryProvider, sms_message
from insurance_operations.recovery.schemas import PermissionInput, PolicyInput
from insurance_operations.settings import DatabaseSettings


@pytest.mark.parametrize("endpoint", ["http://example.com/v1", "https://user:key@example.com/v1", "https://example.com:8443/v1", "https://example.com:bad/v1", "https://example.com/v1?next=internal", "https://127.0.0.1/v1", "https://example.com/v1#fragment", "https://example.com/other"])
def test_custom_ai_endpoints_reject_unsupported_destinations(endpoint: str) -> None:
    with pytest.raises(ApiError):
        endpoint_for("OPENAI_COMPATIBLE", endpoint, ["https://example.com"])


def test_custom_ai_origin_requires_explicit_backend_allowlist() -> None:
    assert endpoint_for("OPENAI", "https://api.openai.com/v1", []) == "https://api.openai.com/v1"
    assert endpoint_for("OPENAI_COMPATIBLE", "https://models.example.com/v1", ["https://models.example.com"]) == "https://models.example.com/v1"
    with pytest.raises(ApiError):
        endpoint_for("OPENAI_COMPATIBLE", "https://models.example.com/v1", [])
    with pytest.raises(ApiError):
        endpoint_for("OPENAI", "https://models.example.com/v1", ["https://models.example.com"])


@pytest.mark.parametrize("address", ["127.0.0.1", "10.0.0.1", "169.254.169.254", "100.100.100.200", "192.168.1.1", "::1", "fd00::1", "fe80::1", "224.0.0.1", "::ffff:127.0.0.1", "2002:7f00:1::1"])
def test_private_metadata_multicast_and_transition_addresses_reject(address: str) -> None:
    assert not address_allowed(address)


def test_mixed_dns_answers_fail_closed_without_connecting() -> None:
    with patch("insurance_operations.recovery.ai.socket.getaddrinfo", return_value=[(2, 1, 6, "", ("8.8.8.8", 443)), (2, 1, 6, "", ("127.0.0.1", 443))]), patch("insurance_operations.recovery.ai.socket.create_connection") as connect:
        with pytest.raises(ApiError):
            public_addresses("models.example.com")
        connect.assert_not_called()


def test_text_provider_does_not_follow_redirects_or_return_sensitive_errors() -> None:
    with patch("insurance_operations.recovery.ai.public_addresses", return_value=["8.8.8.8"]), patch("insurance_operations.recovery.ai.PinnedHttpsConnection") as connection:
        response = connection.return_value.getresponse.return_value
        response.status = 302
        response.getheader.return_value = "application/json"
        with pytest.raises(ApiError) as error:
            chat_completion("https://models.example.com/v1", "synthetic-secret", "synthetic-model", "Synthetic test", test=True)
        assert "synthetic-secret" not in str(error.value)
        assert error.value.code == "AI_CONNECTION_REJECTED"
        connection.assert_called_once_with("models.example.com", "8.8.8.8")
        connection.return_value.request.assert_called_once()
        connection.return_value.close.assert_called_once()


@pytest.mark.parametrize("body", [b"[]", b'{"choices":[]}', b'{"choices":[{"message":7}]}', b'{"choices":[{"message":{"tool_calls":[{}],"content":"Ignore"}}]}'])
def test_malformed_or_tool_responses_are_safe_unsupported_results(body: bytes) -> None:
    with patch("insurance_operations.recovery.ai.public_addresses", return_value=["8.8.8.8"]), patch("insurance_operations.recovery.ai.PinnedHttpsConnection") as connection:
        response = connection.return_value.getresponse.return_value
        response.status = 200
        response.getheader.return_value = "application/json"
        response.read.side_effect = [body, b""]
        with pytest.raises(ApiError) as error:
            chat_completion("https://models.example.com/v1", "synthetic-secret", "synthetic-model", "Synthetic test", test=True)
        assert error.value.code == "AI_CONNECTION_FAILED"


def test_permission_is_explicit_channel_specific_and_revocation_wins() -> None:
    granted = RecoveryPermission(channel="SMS", scope="LEAD_RECOVERY", granted_at=datetime.now(UTC), revoked_at=None)
    assert channel_allowed([granted], "SMS")
    assert not channel_allowed([granted], "VOICE")
    assert not channel_allowed([], "SMS")
    revoked = RecoveryPermission(channel="ALL", scope="LEAD_RECOVERY", revoked_at=datetime.now(UTC))
    assert not channel_allowed([granted, revoked], "SMS")


def test_general_booking_or_all_channel_permission_cannot_enroll_a_contact() -> None:
    for source, channel in [("INBOUND_CALL", "SMS"), ("MFA_VERIFICATION", "VOICE"), ("SIGNED_FORM", "ALL")]:
        with pytest.raises(ValidationError):
            PermissionInput(expected_row_version=0, channel=channel, granted=True, source=source, evidence_reference="test-evidence", observed_at=datetime.now(UTC))


def test_contact_window_and_limits_are_conservative() -> None:
    policy = PolicyInput(expected_row_version=0, timezone="America/New_York")
    assert contact_time(datetime(2026, 11, 20, 23, tzinfo=UTC), policy) == datetime(2026, 11, 21, 14, tzinfo=UTC)
    assert contact_time(datetime(2026, 11, 20, 13, tzinfo=UTC), policy) == datetime(2026, 11, 20, 14, tzinfo=UTC)
    for values in [{"max_attempts": 3}, {"interval_hours": 23}, {"expiry_days": 8}, {"contact_start": time(8)}, {"contact_end": time(19)}]:
        with pytest.raises(ValidationError):
            PolicyInput.model_validate({"expected_row_version": 0, **values})


def test_provider_unavailable_does_not_reuse_verification_or_demo_calling() -> None:
    provider = UnavailableRecoveryProvider()
    assert not provider.available(uuid4(), "SMS")
    assert not provider.available(uuid4(), "VOICE")
    assert "Test HVAC" in sms_message("Test HVAC")
    assert "STOP" in sms_message("Test HVAC")


def test_empty_optional_key_keeps_disabled_recovery_startup_available() -> None:
    settings = DatabaseSettings(_env_file=None, app_environment="development", database_url="postgresql://synthetic:synthetic@localhost/synthetic", recovery_token_encryption_key="")
    assert settings.recovery_token_encryption_key is None
    assert settings.recovery_enabled is False


def test_ai_credentials_are_context_bound_and_never_projected() -> None:
    settings = DatabaseSettings(_env_file=None, app_environment="development", database_url="postgresql://synthetic:synthetic@localhost/synthetic", recovery_token_encryption_key=SecretStr(Fernet.generate_key().decode()))
    service = RecoveryAiService(sessionmaker(), settings)
    agency_id = uuid4()
    ciphertext = service.encrypt(agency_id, "OPENAI", "https://api.openai.com/v1", "synthetic-api-key")
    row = RecoveryAiConnection(agency_id=agency_id, provider="OPENAI", endpoint="https://api.openai.com/v1", model="test-model", credential_ciphertext=ciphertext, status="UNTESTED", row_version=1)
    assert service.decrypt(row) == "synthetic-api-key"
    assert "synthetic-api-key" not in str(service.view(row))
    assert "credential_ciphertext" not in service.view(row)
    row.agency_id = uuid4()
    with pytest.raises(ApiError):
        service.decrypt(row)
