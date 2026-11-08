from typing import Self
from urllib.parse import urlsplit

from pydantic import SecretStr, field_validator, model_validator

from insurance_operations.settings import CommonSettings


class BillingSettings(CommonSettings):
    billing_enabled: bool = False
    stripe_live_mode: bool = False
    stripe_secret_key: SecretStr | None = None
    stripe_webhook_secret: SecretStr | None = None
    stripe_product_id: str | None = None
    stripe_essential_price_id: str | None = None
    stripe_comfort_price_id: str | None = None
    stripe_complete_price_id: str | None = None
    stripe_portal_configuration_id: str | None = None
    web_origin: str = "http://localhost:3000"

    @field_validator("*", mode="before")
    @classmethod
    def normalize_optional(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip() or None
        return value

    @model_validator(mode="after")
    def validate_billing(self) -> Self:
        origin = urlsplit(self.web_origin)
        if (
            origin.scheme not in {"http", "https"}
            or not origin.hostname
            or origin.username
            or origin.password
            or origin.path not in {"", "/"}
            or origin.query
            or origin.fragment
        ):
            raise ValueError("WEB_ORIGIN must be an HTTP or HTTPS origin")
        if self.stripe_live_mode:
            raise ValueError("HVACLine billing only supports Stripe test mode")
        if (
            self.stripe_secret_key
            and not self.stripe_secret_key.get_secret_value().startswith("sk_test_")
        ):
            raise ValueError("Only Stripe sandbox/test secret keys are accepted")
        if not self.billing_enabled:
            return self
        required = {
            "STRIPE_SECRET_KEY": self.stripe_secret_key,
            "STRIPE_WEBHOOK_SECRET": self.stripe_webhook_secret,
            "STRIPE_PRODUCT_ID": self.stripe_product_id,
            "STRIPE_PORTAL_CONFIGURATION_ID": self.stripe_portal_configuration_id,
            **{
                f"STRIPE_{key.upper()}_PRICE_ID": getattr(
                    self, f"stripe_{key}_price_id"
                )
                for key in ("essential", "comfort", "complete")
            },
        }
        if missing := [name for name, value in required.items() if value is None]:
            raise ValueError("Billing requires " + ", ".join(missing))
        assert self.stripe_secret_key is not None
        key = self.stripe_secret_key.get_secret_value()
        if not key.startswith("sk_test_"):
            raise ValueError("STRIPE_SECRET_KEY must match STRIPE_LIVE_MODE")
        assert self.stripe_webhook_secret is not None
        if not self.stripe_webhook_secret.get_secret_value().startswith("whsec_"):
            raise ValueError("STRIPE_WEBHOOK_SECRET must be a webhook signing secret")
        for name, value in required.items():
            if name.endswith("PRICE_ID") and (
                not isinstance(value, str) or not value.startswith("price_")
            ):
                raise ValueError(f"{name} must be a Stripe Price ID")
        if not (self.stripe_product_id or "").startswith("prod_") or not (
            self.stripe_portal_configuration_id or ""
        ).startswith("bpc_"):
            raise ValueError("Stripe product and portal identifiers are invalid")
        ids = [value for name, value in required.items() if name.endswith("PRICE_ID")]
        if len(set(ids)) != len(ids):
            raise ValueError("Each billing plan requires a separate subscription price")
        return self
