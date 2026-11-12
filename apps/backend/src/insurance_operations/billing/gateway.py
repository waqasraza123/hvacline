from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any, Literal, cast
from uuid import UUID

import stripe
from stripe.params.checkout import SessionCreateParams

from insurance_operations.billing.catalog import PLANS, PaidPlanKey
from insurance_operations.billing.errors import billing_error
from insurance_operations.billing.settings import BillingSettings

type StripeData = dict[str, Any]


class CardCheckoutParams(SessionCreateParams):
    payment_method_types: list[Literal["card"]]


class StripeGateway:
    def __init__(self, settings: BillingSettings) -> None:
        self.settings = settings

    @property
    def ready(self) -> bool:
        return bool(
            not self.settings.stripe_live_mode
            and self.settings.billing_enabled
            and self.settings.stripe_product_id
            and self.settings.stripe_secret_key
            and self.settings.stripe_webhook_secret
            and self.settings.stripe_essential_price_id
            and self.settings.stripe_comfort_price_id
            and self.settings.stripe_portal_configuration_id
            and self.settings.stripe_complete_price_id
        )

    def price(self, plan: PaidPlanKey) -> str:
        value = {
            "essential": self.settings.stripe_essential_price_id,
            "comfort": self.settings.stripe_comfort_price_id,
            "complete": self.settings.stripe_complete_price_id,
        }.get(plan)
        if value is None or not value.startswith("price_"):
            raise billing_error(
                503,
                "billing_unavailable",
                "Subscription checkout is not available yet.",
            )
        return value

    @contextmanager
    def client(self, *, translate_errors: bool = True) -> Iterator[stripe.StripeClient]:
        key = self.settings.stripe_secret_key
        if key is None:
            raise billing_error(
                503, "billing_unavailable", "Billing is not configured."
            )
        if self.settings.stripe_live_mode or not key.get_secret_value().startswith(
            "sk_test_"
        ):
            raise billing_error(
                503, "billing_mode_mismatch", "Billing configuration is inconsistent."
            )
        transport = stripe.RequestsClient(timeout=10.0)
        try:
            yield stripe.StripeClient(
                key.get_secret_value(),
                http_client=transport,
                max_network_retries=1,
                stripe_version="2026-10-28.endive",
            )
        except stripe.StripeError as error:
            if not translate_errors:
                raise
            raise billing_error(
                502, "stripe_unavailable", "Stripe is unavailable. Please try again."
            ) from error
        finally:
            cast(Callable[[], None], transport.close)()

    def create_customer(self, account_id: UUID, email: str) -> StripeData:
        with self.client() as client:
            result = client.v1.customers.create(
                {"email": email, "metadata": {"hvacline_account_id": str(account_id)}},
                options={"idempotency_key": f"hvacline:customer:{account_id}"},
            )
            return result.to_dict()

    def subscriptions(self, customer_id: str) -> list[StripeData]:
        with self.client() as client:
            result = client.v1.subscriptions.list(
                {
                    "customer": customer_id,
                    "status": "all",
                    "limit": 100,
                    "expand": ["data.latest_invoice"],
                }
            )
            subscriptions: list[StripeData] = []
            for value in result.auto_paging_iter():
                if len(subscriptions) >= 100:
                    raise billing_error(
                        409,
                        "billing_history_review",
                        "Billing history needs support review.",
                    )
                subscriptions.append(value.to_dict())
            return subscriptions

    def checkout(
        self, customer_id: str, plan: PaidPlanKey, request_id: UUID, account_id: UUID
    ) -> StripeData:
        origin = self.settings.web_origin.rstrip("/")
        with self.client() as client:
            price = client.v1.prices.retrieve(self.price(plan))
            if (
                price.livemode is not self.settings.stripe_live_mode
                or not price.active
                or price.product != self.settings.stripe_product_id
                or price.currency != "usd"
                or (
                    price.unit_amount != PLANS[plan].amount
                    or price.recurring is None
                    or price.recurring.interval != "month"
                    or price.recurring.interval_count != 1
                    or price.recurring.usage_type != "licensed"
                    or price.billing_scheme != "per_unit"
                )
            ):
                raise billing_error(
                    503,
                    "billing_price_mismatch",
                    "The configured subscription price needs review.",
                )
            parameters: CardCheckoutParams = {
                "mode": "subscription",
                "customer": customer_id,
                "payment_method_types": ["card"],
                "client_reference_id": str(account_id),
                "line_items": [{"price": self.price(plan), "quantity": 1}],
                "adaptive_pricing": {"enabled": False},
                "subscription_data": {
                    "metadata": {"hvacline_account_id": str(account_id)}
                },
                "metadata": {"hvacline_account_id": str(account_id), "plan": plan},
                "success_url": f"{origin}/billing?checkout=success",
                "cancel_url": f"{origin}/billing?checkout=canceled",
            }
            result = client.v1.checkout.sessions.create(
                parameters,
                options={
                    "idempotency_key": f"hvacline:checkout:{account_id}:{request_id}"
                },
            )
            return result.to_dict()

    def retrieve_checkout(self, session_id: str) -> StripeData:
        with self.client() as client:
            result = client.v1.checkout.sessions.retrieve(session_id)
            return result.to_dict()

    def expire_checkout(self, session_id: str) -> None:
        with self.client() as client:
            client.v1.checkout.sessions.expire(session_id)

    def portal(self, customer_id: str) -> str:
        configuration = self.settings.stripe_portal_configuration_id
        if configuration is None:
            raise billing_error(
                503, "billing_unavailable", "Billing management is unavailable."
            )
        with self.client() as client:
            portal = client.v1.billing_portal.configurations.retrieve(configuration)
            if (
                not portal.active
                or portal.livemode is not self.settings.stripe_live_mode
                or portal.features.subscription_update.enabled
                or not portal.features.subscription_cancel.enabled
                or portal.features.subscription_cancel.mode != "at_period_end"
            ):
                raise billing_error(
                    503,
                    "billing_portal_mismatch",
                    "Billing management settings need business review.",
                )
            result = client.v1.billing_portal.sessions.create(
                {
                    "customer": customer_id,
                    "configuration": configuration,
                    "return_url": f"{self.settings.web_origin.rstrip('/')}/billing",
                }
            )
            if not result.url:
                raise billing_error(
                    502,
                    "stripe_unavailable",
                    "Stripe did not provide a billing portal URL.",
                )
            return result.url

    def verify_event(self, body: bytes, signature: str) -> StripeData:
        secret = self.settings.stripe_webhook_secret
        if secret is None:
            raise billing_error(
                503, "billing_unavailable", "Billing is not configured."
            )
        try:
            event = stripe.Webhook.construct_event(
                body, signature, secret.get_secret_value()
            )
        except (ValueError, stripe.SignatureVerificationError) as error:
            raise billing_error(
                400, "invalid_stripe_signature", "Invalid webhook signature."
            ) from error
        if event.livemode is not False or self.settings.stripe_live_mode:
            raise billing_error(
                400, "billing_mode_mismatch", "Webhook mode does not match."
            )
        return cast(StripeData, event.to_dict())

    def topup(
        self,
        customer_id: str,
        account_id: UUID,
        request_id: UUID,
        plan: PaidPlanKey,
        hours: int,
        amount: int,
    ) -> StripeData:
        origin = self.settings.web_origin.rstrip("/")
        with self.client() as client:
            parameters: CardCheckoutParams = {
                "mode": "payment",
                "customer": customer_id,
                "invoice_creation": {"enabled": True},
                "payment_method_types": ["card"],
                "client_reference_id": str(request_id),
                "adaptive_pricing": {"enabled": False},
                "metadata": {
                    "hvacline_account_id": str(account_id),
                    "hvacline_topup_id": str(request_id),
                },
                "line_items": [
                    {
                        "price_data": {
                            "currency": "usd",
                            "unit_amount": amount,
                            "product_data": {
                                "name": f"{hours} extra HVAC maintenance hours",
                                "description": (
                                    f"Additional technician labor for your "
                                    f"{PLANS[plan].name} "
                                    "package. Parts and materials excluded."
                                ),
                            },
                        },
                        "quantity": 1,
                    }
                ],
                "success_url": f"{origin}/billing?topup=success",
                "cancel_url": f"{origin}/billing?topup=canceled",
            }
            return client.v1.checkout.sessions.create(
                parameters,
                options={
                    "idempotency_key": f"hvacline:topup:{account_id}:{request_id}"
                },
            ).to_dict()
