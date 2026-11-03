from typing import Literal, Self

from pydantic import Field, SecretStr, field_validator, model_validator

from insurance_operations.settings import CommonSettings, RuntimeEnvironment
from insurance_operations.telephony.outbound.destinations import E164


class OutboundDemoSettings(CommonSettings):
    outbound_demo_enabled: bool = False
    outbound_demo_website_enabled: bool = False
    outbound_demo_live_verified: bool = False
    outbound_demo_transfer_enabled: bool = False
    outbound_demo_transfer_verified: bool = False
    outbound_demo_carrier_limit_confirmed: bool = False
    outbound_demo_agent_id: str | None = Field(
        default=None, min_length=1, max_length=200
    )
    outbound_demo_phone_number_id: str | None = Field(
        default=None, min_length=1, max_length=200
    )
    outbound_demo_number_policy: Literal["allowlist", "consented_us"] = "allowlist"
    outbound_demo_allowed_numbers: SecretStr = SecretStr("")
    outbound_demo_human_number: SecretStr = SecretStr("")
    outbound_demo_secret: SecretStr | None = Field(default=None, min_length=32)
    outbound_demo_webhook_secret: SecretStr | None = Field(default=None, min_length=32)
    outbound_demo_daily_limit: int = Field(default=5, ge=1, le=10)
    outbound_demo_number_daily_limit: int = Field(default=1, ge=1, le=2)
    outbound_demo_cooldown_seconds: int = Field(default=300, ge=180, le=86400)
    outbound_demo_max_duration_seconds: int = Field(default=180, ge=30, le=180)
    outbound_demo_ringing_seconds: int = Field(default=25, ge=10, le=30)
    elevenlabs_api_key: SecretStr | None = None
    elevenlabs_phone_agent_id: str | None = None
    elevenlabs_agent_id: str | None = None

    @field_validator(
        "outbound_demo_agent_id",
        "outbound_demo_phone_number_id",
        "outbound_demo_secret",
        "outbound_demo_webhook_secret",
        "elevenlabs_api_key",
        "elevenlabs_phone_agent_id",
        "elevenlabs_agent_id",
        mode="before",
    )
    @classmethod
    def normalize_optional(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip() or None
        return value

    @property
    def allowed_numbers(self) -> frozenset[str]:
        return frozenset(
            value.strip()
            for value in self.outbound_demo_allowed_numbers.get_secret_value().split(
                ","
            )
            if value.strip()
        )

    @model_validator(mode="after")
    def validate_configuration(self) -> Self:
        if any(E164.fullmatch(number) is None for number in self.allowed_numbers):
            raise ValueError("OUTBOUND_DEMO_ALLOWED_NUMBERS must contain E.164 numbers")
        human = self.outbound_demo_human_number.get_secret_value()
        if human and E164.fullmatch(human) is None:
            raise ValueError("OUTBOUND_DEMO_HUMAN_NUMBER must use E.164")
        if self.outbound_demo_number_policy == "consented_us" and (
            self.outbound_demo_website_enabled or self.outbound_demo_transfer_enabled
        ):
            raise ValueError(
                "Consented US calling requires website calling and transfer disabled"
            )
        if self.outbound_demo_website_enabled and not (
            self.outbound_demo_enabled
            and self.outbound_demo_live_verified
            and self.outbound_demo_transfer_enabled
            and self.outbound_demo_transfer_verified
        ):
            raise ValueError(
                "Website calling requires real outbound and transfer acceptance"
            )
        if not self.outbound_demo_enabled:
            return self
        if self.app_environment is not RuntimeEnvironment.DEVELOPMENT:
            raise ValueError(
                "Outbound demonstration requires the development environment"
            )
        if self.outbound_demo_number_policy == "allowlist" and not self.allowed_numbers:
            raise ValueError("Outbound demo allowlist is required in allowlist mode")
        if not all(
            (
                self.outbound_demo_agent_id,
                self.outbound_demo_phone_number_id,
                self.elevenlabs_api_key
                and self.elevenlabs_api_key.get_secret_value().strip(),
                self.outbound_demo_secret
                and len(self.outbound_demo_secret.get_secret_value()) >= 32,
                self.outbound_demo_webhook_secret
                and len(self.outbound_demo_webhook_secret.get_secret_value()) >= 32,
            )
        ):
            raise ValueError("Outbound demo agent, SIP number and secrets are required")
        if self.outbound_demo_agent_id in {
            self.elevenlabs_agent_id,
            self.elevenlabs_phone_agent_id,
        }:
            raise ValueError("Outbound demo must use a dedicated ElevenLabs agent")
        if self.outbound_demo_secret == self.outbound_demo_webhook_secret:
            raise ValueError("Outbound demo webhook must use a separate secret")
        if self.outbound_demo_transfer_enabled and not (
            human and self.outbound_demo_carrier_limit_confirmed
        ):
            raise ValueError(
                "Transfer requires an authorized human and carrier duration control"
            )
        if self.outbound_demo_transfer_enabled and human in self.allowed_numbers:
            raise ValueError(
                "The human transfer number must differ from demo recipients"
            )
        return self
