import pytest
from cryptography.fernet import Fernet
from pydantic import ValidationError

from insurance_operations.settings import ApiSettings


def settings(**overrides: object) -> ApiSettings:
    return ApiSettings(
        _env_file=None, app_environment="development", api_host="127.0.0.1", api_port=8000,
        database_url="postgresql://synthetic:synthetic@localhost/development",
        **overrides,
    )


def test_customer_portal_fails_closed_without_mfa_encryption_key() -> None:
    with pytest.raises(ValidationError, match="CUSTOMER_MFA_ENCRYPTION_KEY is required"):
        settings(customer_portal_enabled=True, customer_mfa_encryption_key=None)


def test_invalid_key_is_rejected_and_blank_disabled_configuration_is_supported() -> None:
    with pytest.raises(ValidationError, match="CUSTOMER_MFA_ENCRYPTION_KEY must be a Fernet key"):
        settings(customer_mfa_encryption_key="invalid-key")
    assert settings(customer_portal_enabled=False, customer_mfa_encryption_key=" ").customer_mfa_encryption_key is None
    configured = settings(customer_mfa_encryption_key=Fernet.generate_key().decode())
    assert configured.customer_mfa_encryption_key is not None
