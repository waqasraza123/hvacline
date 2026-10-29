import base64
import binascii
import re
from enum import StrEnum
from typing import Self
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import EmailStr, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

DEFAULT_CUSTOMER_MAX_ACTIVE_APPOINTMENTS = 1
DEFAULT_CUSTOMER_MAX_BOOKING_CHANGES = 1


class RuntimeEnvironment(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


class DatabaseSslMode(StrEnum):
    DISABLE = "disable"
    REQUIRE = "require"
    VERIFY_CA = "verify-ca"
    VERIFY_FULL = "verify-full"


class ConversationProviderName(StrEnum):
    ELEVENLABS = "elevenlabs"
    LOCAL = "local"


class CommonSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        hide_input_in_errors=True,
    )

    app_environment: RuntimeEnvironment


class DatabaseConnectionSettings(CommonSettings):
    database_url: str
    direct_database_url: str | None = None
    test_database_url: str | None = None
    database_ssl_mode: DatabaseSslMode = DatabaseSslMode.REQUIRE
    database_pool_size: int = Field(default=5, ge=1, le=20)
    database_max_overflow: int = Field(default=2, ge=0, le=20)
    database_pool_timeout_seconds: int = Field(default=10, ge=1, le=60)
    database_pool_recycle_seconds: int = Field(default=300, ge=30, le=3_600)

    @field_validator(
        "database_url",
        "direct_database_url",
        "test_database_url",
    )
    @classmethod
    def validate_postgresql_url(cls, value: str | None) -> str | None:
        if value is None:
            return None

        try:
            parsed_url = make_url(value)
        except ArgumentError as error:
            raise ValueError("database URLs must be valid PostgreSQL URLs") from error
        if parsed_url.drivername not in {"postgresql", "postgresql+psycopg"}:
            raise ValueError("database URLs must use PostgreSQL with psycopg")
        if not parsed_url.database:
            raise ValueError("database URLs must include a database name")
        return value

    @model_validator(mode="after")
    def validate_database_environment(self) -> Self:
        if (
            self.app_environment is RuntimeEnvironment.TEST
            and self.test_database_url is None
        ):
            raise ValueError("TEST_DATABASE_URL is required in the test environment")
        if (
            self.app_environment is RuntimeEnvironment.TEST
            and self.test_database_url is not None
            and any(
                database_target(self.test_database_url) == database_target(url)
                for url in (self.database_url, self.direct_database_url)
                if url is not None
            )
        ):
            raise ValueError(
                "TEST_DATABASE_URL must be isolated from database runtime and "
                "migration URLs"
            )
        if (
            self.app_environment is RuntimeEnvironment.PRODUCTION
            and self.database_ssl_mode is DatabaseSslMode.DISABLE
        ):
            raise ValueError("database SSL cannot be disabled in production")
        return self

    @property
    def runtime_database_url(self) -> str:
        if self.app_environment is RuntimeEnvironment.TEST:
            if self.test_database_url is None:
                raise RuntimeError("test database configuration is unavailable")
            return self.test_database_url
        return self.database_url

    @property
    def migration_database_url(self) -> str:
        if self.app_environment is RuntimeEnvironment.TEST:
            return self.runtime_database_url
        return self.direct_database_url or self.database_url


class DatabaseSettings(DatabaseConnectionSettings):
    customer_max_active_appointments: int = Field(
        default=DEFAULT_CUSTOMER_MAX_ACTIVE_APPOINTMENTS, ge=1, le=20
    )
    customer_max_booking_changes: int = Field(
        default=DEFAULT_CUSTOMER_MAX_BOOKING_CHANGES, ge=0, le=20
    )
    demo_inbound_number_e164: str | None = None
    demo_transfer_destination_e164: str | None = None
    google_calendar_enabled: bool = False
    google_client_id: str | None = None
    google_client_secret: SecretStr | None = None
    google_redirect_uri: str | None = None
    calendar_token_encryption_key: SecretStr | None = None
    booking_email_enabled: bool = False
    resend_api_key: SecretStr | None = None
    resend_webhook_secret: SecretStr | None = None
    booking_email_from: EmailStr | None = None
    booking_reminder_hours: int = Field(default=24, ge=1, le=168)
    worker_poll_seconds: int = Field(default=30, ge=5, le=60)

    @field_validator(
        "demo_inbound_number_e164",
        "demo_transfer_destination_e164",
    )
    @classmethod
    def validate_demo_phone_number(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        normalized = value.strip()
        if re.fullmatch(r"\+[1-9][0-9]{7,14}", normalized) is None:
            raise ValueError("demo phone numbers must use E.164 format")
        return normalized

    @field_validator("booking_email_from", mode="before")
    @classmethod
    def normalize_email_sender(cls, value: object) -> object:
        return None if isinstance(value, str) and not value.strip() else value

    @model_validator(mode="after")
    def validate_booking_integrations(self) -> Self:
        if (self.google_calendar_enabled or self.booking_email_enabled) and (
            self.app_environment is RuntimeEnvironment.PRODUCTION
        ):
            raise ValueError(
                "booking integrations require the development identity gates"
            )
        if self.google_calendar_enabled:
            from cryptography.fernet import Fernet

            if not all(
                (
                    self.google_client_id and self.google_client_id.strip(),
                    self.google_client_secret
                    and self.google_client_secret.get_secret_value().strip(),
                    self.google_redirect_uri,
                    self.calendar_token_encryption_key,
                )
            ):
                raise ValueError(
                    "Google OAuth and calendar encryption configuration are required"
                )
            assert self.calendar_token_encryption_key is not None
            try:
                Fernet(self.calendar_token_encryption_key.get_secret_value().encode())
            except (ValueError, TypeError) as error:
                raise ValueError(
                    "CALENDAR_TOKEN_ENCRYPTION_KEY must be a Fernet key"
                ) from error
            uri = urlsplit(self.google_redirect_uri or "")
            if (
                (
                    uri.scheme != "https"
                    and not (
                        uri.scheme == "http"
                        and uri.hostname in {"localhost", "127.0.0.1"}
                    )
                )
                or not uri.hostname
                or uri.username
                or uri.password
                or uri.query
                or uri.fragment
                or uri.path != "/api/v1/development/hvac/integrations/google/callback"
            ):
                raise ValueError(
                    "GOOGLE_REDIRECT_URI must be an HTTPS callback URL (HTTP loopback is allowed)"
                )
        if self.booking_email_enabled and not (
            self.resend_api_key
            and self.resend_api_key.get_secret_value().strip()
            and self.resend_webhook_secret
            and self.resend_webhook_secret.get_secret_value().startswith("whsec_")
            and self.booking_email_from
            and "@" in self.booking_email_from
            and "\n" not in self.booking_email_from
            and "\r" not in self.booking_email_from
        ):
            raise ValueError(
                "RESEND_API_KEY, RESEND_WEBHOOK_SECRET and BOOKING_EMAIL_FROM are required"
            )
        if self.booking_email_enabled and self.resend_webhook_secret:
            try:
                key = base64.b64decode(
                    self.resend_webhook_secret.get_secret_value()[6:], validate=True
                )
                if len(key) < 16:
                    raise ValueError("signing secret too short")
            except (ValueError, binascii.Error) as error:
                raise ValueError(
                    "RESEND_WEBHOOK_SECRET must be a valid webhook signing secret"
                ) from error
        return self


class ApiSettings(DatabaseSettings):
    homepage_chat_enabled: bool = False
    homepage_chat_daily_limit: int = Field(default=20, ge=1, le=1000)
    homepage_chat_concurrent_limit: int = Field(default=1, ge=1, le=10)
    customer_memory_enabled: bool = False
    customer_memory_retention_days: int = Field(default=90, ge=1, le=365)
    customer_memory_context_characters: int = Field(default=1200, ge=300, le=2000)
    api_host: str = Field(min_length=1)
    api_port: int = Field(ge=1, le=65_535)
    web_origin: str = "http://localhost:3000"
    idempotency_retention_hours: int = Field(default=24, ge=1, le=168)
    conversation_ai_enabled: bool = False
    conversation_provider: ConversationProviderName = (
        ConversationProviderName.ELEVENLABS
    )
    development_actor_user_id: UUID | None = None
    conversation_max_duration_seconds: int = Field(default=180, ge=1, le=180)
    conversation_daily_session_limit: int = Field(default=10, ge=1, le=10)
    conversation_confirmation_window_minutes: int = Field(default=30, ge=5, le=60)
    elevenlabs_api_key: SecretStr | None = None
    elevenlabs_agent_id: str | None = Field(default=None, min_length=1, max_length=200)
    elevenlabs_privacy_confirmed: bool = False
    local_whisper_command: str = Field(default="whisper-cli", min_length=1)
    local_whisper_model_path: str = Field(
        default=".local/models/ggml-base.en.bin",
        min_length=1,
    )
    local_ollama_base_url: str = "http://127.0.0.1:11434"
    local_ollama_model: str = Field(default="llama3.2:3b", min_length=1)
    local_piper_model_path: str = Field(
        default=".local/models/piper/en_US-lessac-medium.onnx",
        min_length=1,
    )
    demo_sandbox_enabled: bool = False
    demo_admin_token: SecretStr | None = None
    demo_result_ttl_minutes: int = Field(default=15, ge=5, le=60)
    customer_portal_enabled: bool = False
    customer_portal_secret: SecretStr | None = None
    customer_mfa_encryption_key: SecretStr | None = None

    @model_validator(mode="after")
    def validate_homepage_chat(self) -> Self:
        if self.homepage_chat_enabled and not self.customer_portal_enabled:
            raise ValueError("Homepage chat requires the configured customer portal")
        return self

    @field_validator("web_origin")
    @classmethod
    def validate_web_origin(cls, value: str) -> str:
        parsed_origin = urlsplit(value)
        if (
            parsed_origin.scheme not in {"http", "https"}
            or parsed_origin.hostname is None
            or parsed_origin.username is not None
            or parsed_origin.password is not None
            or parsed_origin.path not in {"", "/"}
            or parsed_origin.query
            or parsed_origin.fragment
        ):
            raise ValueError("WEB_ORIGIN must be an HTTP or HTTPS origin")
        return value.rstrip("/")

    @field_validator("local_ollama_base_url")
    @classmethod
    def validate_local_ollama_base_url(cls, value: str) -> str:
        parsed_url = urlsplit(value)
        if (
            parsed_url.scheme not in {"http", "https"}
            or parsed_url.hostname not in {"localhost", "127.0.0.1", "::1"}
            or parsed_url.username is not None
            or parsed_url.password is not None
            or parsed_url.query
            or parsed_url.fragment
            or parsed_url.path not in {"", "/"}
        ):
            raise ValueError(
                "LOCAL_OLLAMA_BASE_URL must be a loopback HTTP or HTTPS URL"
            )
        return value.rstrip("/")

    @field_validator("elevenlabs_agent_id")
    @classmethod
    def normalize_agent_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized_value = value.strip()
        if not normalized_value:
            raise ValueError("ELEVENLABS_AGENT_ID cannot be empty")
        return normalized_value

    @field_validator("elevenlabs_api_key")
    @classmethod
    def normalize_api_key(cls, value: SecretStr | None) -> SecretStr | None:
        if value is None:
            return None
        return SecretStr(value.get_secret_value().strip())

    @field_validator("demo_admin_token")
    @classmethod
    def normalize_demo_admin_token(
        cls,
        value: SecretStr | None,
    ) -> SecretStr | None:
        if value is None:
            return None
        return SecretStr(value.get_secret_value().strip())

    @model_validator(mode="after")
    def validate_conversation_configuration(self) -> Self:
        if not self.conversation_ai_enabled:
            return self
        if self.app_environment is not RuntimeEnvironment.DEVELOPMENT:
            raise ValueError("conversation AI can be enabled only in development")
        if self.development_actor_user_id is None:
            raise ValueError(
                "DEVELOPMENT_ACTOR_USER_ID is required when conversation AI is enabled"
            )
        if (
            self.conversation_provider is ConversationProviderName.LOCAL
            and self.customer_portal_enabled
        ):
            raise ValueError(
                "local conversations support the development workspace only; "
                "disable CUSTOMER_PORTAL_ENABLED or select elevenlabs"
            )
        if self.conversation_provider is ConversationProviderName.ELEVENLABS:
            if (
                self.elevenlabs_api_key is None
                or not self.elevenlabs_api_key.get_secret_value().strip()
            ):
                raise ValueError(
                    "ELEVENLABS_API_KEY is required when the ElevenLabs "
                    "conversation provider is enabled"
                )
            if self.elevenlabs_agent_id is None:
                raise ValueError(
                    "ELEVENLABS_AGENT_ID is required when the ElevenLabs "
                    "conversation provider is enabled"
                )
            if not self.elevenlabs_privacy_confirmed:
                raise ValueError(
                    "ElevenLabs audio saving and zero-day retention must be confirmed"
                )
        return self

    @model_validator(mode="after")
    def validate_customer_portal(self) -> Self:
        if self.customer_mfa_encryption_key is not None:
            from cryptography.fernet import Fernet

            try:
                Fernet(self.customer_mfa_encryption_key.get_secret_value().encode())
            except (ValueError, TypeError) as error:
                raise ValueError(
                    "CUSTOMER_MFA_ENCRYPTION_KEY must be a Fernet key"
                ) from error
        if not self.customer_portal_enabled:
            return self
        if self.customer_mfa_encryption_key is None:
            raise ValueError(
                "CUSTOMER_MFA_ENCRYPTION_KEY is required for customer accounts"
            )
        if (
            self.app_environment is not RuntimeEnvironment.DEVELOPMENT
            or not self.demo_sandbox_enabled
            or not self.conversation_ai_enabled
        ):
            raise ValueError(
                "customer portal requires the protected development voice environment"
            )
        if (
            self.customer_portal_secret is None
            or len(self.customer_portal_secret.get_secret_value()) < 32
        ):
            raise ValueError(
                "CUSTOMER_PORTAL_SECRET must contain at least 32 characters"
            )
        return self

    @field_validator("customer_mfa_encryption_key", mode="before")
    @classmethod
    def normalize_mfa_key(cls, value: object) -> object:
        if isinstance(value, SecretStr):
            value = value.get_secret_value()
        if isinstance(value, str):
            return value.strip() or None
        return value

    @model_validator(mode="after")
    def validate_demo_sandbox_configuration(self) -> Self:
        if not self.demo_sandbox_enabled:
            return self
        if self.app_environment is not RuntimeEnvironment.DEVELOPMENT:
            raise ValueError("the demo sandbox can be enabled only in development")
        if self.development_actor_user_id is None:
            raise ValueError(
                "DEVELOPMENT_ACTOR_USER_ID is required for the demo sandbox"
            )
        if (
            self.demo_admin_token is None
            or len(self.demo_admin_token.get_secret_value()) < 32
        ):
            raise ValueError("DEMO_ADMIN_TOKEN must contain at least 32 characters")
        return self


class WorkerSettings(DatabaseSettings):
    worker_name: str = Field(min_length=1, max_length=100)


class JobRunnerSettings(WorkerSettings):
    booking_jobs_secret: SecretStr

    @field_validator("booking_jobs_secret")
    @classmethod
    def validate_booking_jobs_secret(cls, value: SecretStr) -> SecretStr:
        secret = value.get_secret_value()
        if len(secret) < 32 or any(character.isspace() for character in secret):
            raise ValueError(
                "BOOKING_JOBS_SECRET must contain at least 32 characters without whitespace"
            )
        return value


def database_target(value: str) -> tuple[str | None, int, str | None]:
    parsed_url = make_url(value)
    host = parsed_url.host.lower() if parsed_url.host is not None else None
    if host is not None:
        first_label, separator, remaining_labels = host.partition(".")
        host = first_label.removesuffix("-pooler") + separator + remaining_labels
    return (
        host,
        parsed_url.port or 5432,
        parsed_url.database,
    )
