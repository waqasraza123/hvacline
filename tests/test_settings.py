import pytest
from pydantic import ValidationError

from insurance_operations.settings import (
    ApiSettings,
    DatabaseConnectionSettings,
    DatabaseSettings,
    DatabaseSslMode,
    RuntimeEnvironment,
    WorkerSettings,
)


@pytest.mark.parametrize(
    ("name", "value", "attribute"),
    [
        ("CUSTOMER_MAX_ACTIVE_APPOINTMENTS", "2", "customer_max_active_appointments"),
        ("CUSTOMER_MAX_BOOKING_CHANGES", "0", "customer_max_booking_changes"),
    ],
)
def test_customer_booking_limits_read_backend_environment(
    monkeypatch: pytest.MonkeyPatch, name: str, value: str, attribute: str
) -> None:
    monkeypatch.setenv(name, value)
    settings = DatabaseSettings(
        _env_file=None,
        app_environment=RuntimeEnvironment.DEVELOPMENT,
        database_url="postgresql://synthetic:synthetic@localhost/development",
        google_calendar_enabled=False,
        booking_email_enabled=False,
        booking_email_from=None,
    )
    assert getattr(settings, attribute) == int(value)


@pytest.mark.parametrize(
    "overrides",
    [
        {"customer_max_active_appointments": 0},
        {"customer_max_active_appointments": 21},
        {"customer_max_booking_changes": -1},
        {"customer_max_booking_changes": 21},
    ],
)
def test_customer_booking_limits_reject_invalid_configuration(
    overrides: dict[str, int],
) -> None:
    with pytest.raises(ValidationError):
        DatabaseSettings.model_validate(
            {
                "app_environment": RuntimeEnvironment.DEVELOPMENT,
                "database_url": "postgresql://synthetic:synthetic@localhost/development",
                "google_calendar_enabled": False,
                "booking_email_enabled": False,
                **overrides,
            }
        )


@pytest.mark.parametrize(
    "integration_environment",
    [
        {
            "GOOGLE_CALENDAR_ENABLED": "true",
            "GOOGLE_CLIENT_ID": "",
            "GOOGLE_CLIENT_SECRET": "",
            "GOOGLE_REDIRECT_URI": "",
            "CALENDAR_TOKEN_ENCRYPTION_KEY": "",
        },
        {
            "BOOKING_EMAIL_ENABLED": "true",
            "RESEND_API_KEY": "",
            "RESEND_WEBHOOK_SECRET": "",
            "BOOKING_EMAIL_FROM": "invalid-sender",
        },
    ],
)
def test_migration_settings_ignore_incomplete_runtime_integrations(
    monkeypatch: pytest.MonkeyPatch,
    integration_environment: dict[str, str],
) -> None:
    for name, value in integration_environment.items():
        monkeypatch.setenv(name, value)

    settings = DatabaseConnectionSettings(
        _env_file=None,
        app_environment=RuntimeEnvironment.DEVELOPMENT,
        database_url="postgresql://user:password@pooled.example/development",
        direct_database_url="postgresql://user:password@direct.example/development",
        test_database_url=None,
    )

    assert settings.migration_database_url == (
        "postgresql://user:password@direct.example/development"
    )


@pytest.mark.parametrize("settings_class", [ApiSettings, WorkerSettings])
@pytest.mark.parametrize(
    ("integration_environment", "message"),
    [
        (
            {
                "GOOGLE_CALENDAR_ENABLED": "true",
                "BOOKING_EMAIL_ENABLED": "false",
                "GOOGLE_CLIENT_ID": "",
                "GOOGLE_CLIENT_SECRET": "",
                "GOOGLE_REDIRECT_URI": "",
                "CALENDAR_TOKEN_ENCRYPTION_KEY": "",
            },
            "Google OAuth and calendar encryption configuration are required",
        ),
        (
            {
                "GOOGLE_CALENDAR_ENABLED": "false",
                "BOOKING_EMAIL_ENABLED": "true",
                "RESEND_API_KEY": "",
                "RESEND_WEBHOOK_SECRET": "",
                "BOOKING_EMAIL_FROM": "",
            },
            "RESEND_API_KEY, RESEND_WEBHOOK_SECRET and BOOKING_EMAIL_FROM are required",
        ),
    ],
)
def test_runtime_settings_require_enabled_integration_credentials(
    monkeypatch: pytest.MonkeyPatch,
    settings_class: type[ApiSettings] | type[WorkerSettings],
    integration_environment: dict[str, str],
    message: str,
) -> None:
    for name, value in integration_environment.items():
        monkeypatch.setenv(name, value)

    values: dict[str, object] = {
        "app_environment": RuntimeEnvironment.DEVELOPMENT,
        "database_url": "postgresql://user:password@localhost/development",
        "test_database_url": None,
        "api_host": "127.0.0.1",
        "api_port": 8000,
        "worker_name": "synthetic-worker",
        "conversation_ai_enabled": False,
        "demo_sandbox_enabled": False,
        "customer_portal_enabled": False,
    }
    with pytest.raises(ValidationError, match=message):
        settings_class(_env_file=None, **values)


def test_api_settings_reject_invalid_port() -> None:
    with pytest.raises(ValidationError, match="less than or equal to 65535"):
        ApiSettings(
            app_environment=RuntimeEnvironment.TEST,
            api_host="127.0.0.1",
            api_port=70_000,
            web_origin="http://localhost:3000",
            database_url="postgresql://user:password@localhost/development",
            test_database_url="postgresql://user:password@localhost/test",
            database_ssl_mode=DatabaseSslMode.DISABLE,
            conversation_ai_enabled=False,
        )


def test_worker_settings_reject_empty_name() -> None:
    with pytest.raises(ValidationError, match="at least 1 character"):
        WorkerSettings(
            app_environment=RuntimeEnvironment.TEST,
            worker_name="",
            database_url="postgresql://user:password@localhost/development",
            test_database_url="postgresql://user:password@localhost/test",
            database_ssl_mode=DatabaseSslMode.DISABLE,
        )


def test_api_settings_reject_web_origin_with_a_path() -> None:
    with pytest.raises(
        ValidationError,
        match="WEB_ORIGIN must be an HTTP or HTTPS origin",
    ):
        ApiSettings(
            app_environment=RuntimeEnvironment.TEST,
            api_host="127.0.0.1",
            api_port=8000,
            web_origin="https://example.test/application",
            database_url="postgresql://user:password@localhost/development",
            test_database_url="postgresql://user:password@localhost/test",
            database_ssl_mode=DatabaseSslMode.DISABLE,
            conversation_ai_enabled=False,
        )


def test_conversation_ai_cannot_be_enabled_outside_development() -> None:
    with pytest.raises(
        ValidationError,
        match="conversation AI can be enabled only in development",
    ):
        ApiSettings(
            app_environment=RuntimeEnvironment.TEST,
            api_host="127.0.0.1",
            api_port=8000,
            database_url="postgresql://user:password@localhost/development",
            test_database_url="postgresql://user:password@localhost/test",
            database_ssl_mode=DatabaseSslMode.DISABLE,
            conversation_ai_enabled=True,
        )


def test_enabled_conversation_ai_requires_privacy_attestation() -> None:
    with pytest.raises(
        ValidationError,
        match="audio saving and zero-day retention must be confirmed",
    ):
        ApiSettings(
            app_environment=RuntimeEnvironment.DEVELOPMENT,
            api_host="127.0.0.1",
            api_port=8000,
            database_url="postgresql://user:password@localhost/development",
            database_ssl_mode=DatabaseSslMode.DISABLE,
            conversation_ai_enabled=True,
            development_actor_user_id="00000000-0000-4000-8000-000000000002",
            elevenlabs_api_key="test-secret",
            elevenlabs_agent_id="agent_test",
            elevenlabs_privacy_confirmed=False,
        )


def test_enabled_conversation_ai_accepts_complete_configuration() -> None:
    settings = ApiSettings(
        app_environment=RuntimeEnvironment.DEVELOPMENT,
        api_host="127.0.0.1",
        api_port=8000,
        database_url="postgresql://user:password@localhost/development",
        database_ssl_mode=DatabaseSslMode.DISABLE,
        conversation_ai_enabled=True,
        development_actor_user_id="00000000-0000-4000-8000-000000000002",
        elevenlabs_api_key="test-secret",
        elevenlabs_agent_id="agent_test",
        elevenlabs_privacy_confirmed=True,
    )

    assert settings.conversation_max_duration_seconds == 180
    assert settings.conversation_daily_session_limit == 10


def test_demo_sandbox_requires_a_strong_admin_token() -> None:
    with pytest.raises(
        ValidationError,
        match="DEMO_ADMIN_TOKEN must contain at least 32 characters",
    ):
        ApiSettings(
            app_environment=RuntimeEnvironment.DEVELOPMENT,
            api_host="127.0.0.1",
            api_port=8000,
            database_url="postgresql://user:password@localhost/development",
            database_ssl_mode=DatabaseSslMode.DISABLE,
            development_actor_user_id="00000000-0000-4000-8000-000000000002",
            demo_sandbox_enabled=True,
            demo_admin_token="too-short",
            demo_inbound_number_e164="+15550100100",
            demo_transfer_destination_e164="+15550100200",
        )


def test_demo_sandbox_accepts_complete_development_configuration() -> None:
    settings = ApiSettings(
        app_environment=RuntimeEnvironment.DEVELOPMENT,
        api_host="127.0.0.1",
        api_port=8000,
        database_url="postgresql://user:password@localhost/development",
        database_ssl_mode=DatabaseSslMode.DISABLE,
        development_actor_user_id="00000000-0000-4000-8000-000000000002",
        demo_sandbox_enabled=True,
        demo_admin_token="synthetic-demo-admin-token-32-chars",
        demo_inbound_number_e164="+15550100100",
        demo_transfer_destination_e164="+15550100200",
    )

    assert settings.demo_sandbox_enabled is True
    assert settings.demo_result_ttl_minutes == 15


@pytest.mark.parametrize("number", [None, "", "   "])
def test_browser_sandbox_does_not_require_phone_numbers(number: str | None) -> None:
    settings = ApiSettings(
        app_environment=RuntimeEnvironment.DEVELOPMENT,
        api_host="127.0.0.1",
        api_port=8000,
        database_url="postgresql://user:password@localhost/development",
        development_actor_user_id="00000000-0000-4000-8000-000000000002",
        demo_sandbox_enabled=True,
        demo_admin_token="synthetic-demo-admin-token-32-chars",
        demo_inbound_number_e164=number,
        demo_transfer_destination_e164=number,
    )
    assert settings.demo_inbound_number_e164 is None
    assert settings.demo_transfer_destination_e164 is None


def test_invalid_configured_phone_number_is_rejected() -> None:
    with pytest.raises(ValidationError, match="E.164"):
        ApiSettings(
            app_environment=RuntimeEnvironment.DEVELOPMENT,
            api_host="127.0.0.1",
            api_port=8000,
            database_url="postgresql://user:password@localhost/development",
            demo_inbound_number_e164="not-a-number",
        )
