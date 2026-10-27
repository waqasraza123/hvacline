from typing import Self
from uuid import UUID

from pydantic import Field, SecretStr, field_validator, model_validator

from insurance_operations.settings import CommonSettings, RuntimeEnvironment


class WhatsAppSettings(CommonSettings):
    whatsapp_enabled: bool = False
    whatsapp_agency_id: UUID | None = None
    whatsapp_actor_user_id: UUID | None = None
    elevenlabs_whatsapp_agent_id: str | None = Field(default=None, max_length=200)
    elevenlabs_whatsapp_phone_number_id: str | None = Field(
        default=None, max_length=200
    )
    elevenlabs_whatsapp_init_secret: SecretStr | None = None
    elevenlabs_whatsapp_tool_secret: SecretStr | None = None
    elevenlabs_whatsapp_session_secret: SecretStr | None = None
    elevenlabs_whatsapp_post_call_secret: SecretStr | None = None
    elevenlabs_whatsapp_privacy_confirmed: bool = False

    @field_validator(
        "elevenlabs_whatsapp_agent_id",
        "elevenlabs_whatsapp_phone_number_id",
        "elevenlabs_whatsapp_init_secret",
        "elevenlabs_whatsapp_tool_secret",
        "elevenlabs_whatsapp_session_secret",
        "elevenlabs_whatsapp_post_call_secret",
        mode="before",
    )
    @classmethod
    def normalize_optional(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip() or None
        return value

    @model_validator(mode="after")
    def enabled_configuration(self) -> Self:
        if not self.whatsapp_enabled:
            return self
        if self.app_environment is not RuntimeEnvironment.DEVELOPMENT:
            raise ValueError(
                "WhatsApp requires the development synthetic-data environment"
            )
        required = (
            self.whatsapp_agency_id,
            self.whatsapp_actor_user_id,
            self.elevenlabs_whatsapp_agent_id,
            self.elevenlabs_whatsapp_phone_number_id,
        )
        secrets = (
            self.elevenlabs_whatsapp_init_secret,
            self.elevenlabs_whatsapp_tool_secret,
            self.elevenlabs_whatsapp_session_secret,
            self.elevenlabs_whatsapp_post_call_secret,
        )
        if not all(required) or not self.elevenlabs_whatsapp_privacy_confirmed:
            raise ValueError(
                "WhatsApp agency, actor, agent, number and privacy approval are required"
            )
        if any(
            secret is None or len(secret.get_secret_value()) < 32 for secret in secrets
        ):
            raise ValueError("WhatsApp requires four secrets of at least 32 characters")
        if len({secret.get_secret_value() for secret in secrets if secret}) != 4:
            raise ValueError("WhatsApp secrets must be distinct")
        return self
