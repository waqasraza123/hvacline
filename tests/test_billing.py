import hashlib
import hmac
import json
import time
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from insurance_operations.billing.catalog import PLANS
from insurance_operations.billing.gateway import StripeGateway
from insurance_operations.billing.schemas import CheckoutCreate, TopUpCreate
from insurance_operations.billing.service import BillingService, stripe_url
from insurance_operations.billing.settings import BillingSettings
from insurance_operations.billing.state import active_plan, apply_subscription
from insurance_operations.database.models.billing import BillingAccount, BillingTopUp
from insurance_operations.errors import ApiError


def billing_settings(**values: object) -> BillingSettings:
    return BillingSettings(_env_file=None, app_environment="development", **values)


def subscription(account: BillingAccount, *, paid: bool = True) -> dict:
    now = datetime.now(UTC)
    return {
        "id": "sub_synthetic",
        "customer": account.customer_id,
        "livemode": False,
        "status": "active",
        "metadata": {"hvacline_account_id": str(account.account_id)},
        "items": {
            "data": [
                {
                    "quantity": 1,
                    "current_period_start": int((now - timedelta(days=1)).timestamp()),
                    "current_period_end": int((now + timedelta(days=29)).timestamp()),
                    "price": {
                        "id": "price_essential",
                        "product": "prod_synthetic",
                        "currency": "usd",
                        "unit_amount": PLANS["essential"].amount,
                        "billing_scheme": "per_unit",
                        "recurring": {
                            "interval": "month",
                            "interval_count": 1,
                            "usage_type": "licensed",
                        },
                    },
                }
            ]
        },
        "latest_invoice": {
            "status": "paid" if paid else "open",
            "customer": account.customer_id,
        },
    }


def test_configuration_never_accepts_live_billing() -> None:
    assert not StripeGateway(billing_settings()).ready
    for values in (
        {"stripe_live_mode": True},
        {"stripe_secret_key": "sk_live_synthetic"},
        {"billing_enabled": True},
    ):
        with pytest.raises(ValidationError):
            billing_settings(**values)


def test_package_hours_require_a_paid_current_subscription() -> None:
    settings = billing_settings(
        stripe_product_id="prod_synthetic", stripe_essential_price_id="price_essential"
    )
    account = BillingAccount(
        account_id=uuid4(),
        agency_id=uuid4(),
        customer_id="cus_synthetic",
        livemode=False,
        review_required=False,
    )
    apply_subscription(account, subscription(account, paid=False), settings)
    assert active_plan(account) == "none"
    apply_subscription(account, subscription(account), settings)
    assert active_plan(account) == "essential"
    assert PLANS["essential"].included_minutes == 180
    account.review_required = True
    assert active_plan(account) == "none"


@pytest.mark.parametrize(
    "status, payment, expected",
    [
        ("open", "unpaid", "open"),
        ("complete", "unpaid", "open"),
        ("complete", "paid", "paid"),
        ("expired", "unpaid", "expired"),
    ],
)
def test_topup_credit_requires_confirmed_payment(
    status: str, payment: str, expected: str
) -> None:
    account = BillingAccount(
        account_id=uuid4(),
        customer_id="cus_synthetic",
        agency_id=uuid4(),
        livemode=False,
    )
    topup = BillingTopUp(
        id=uuid4(),
        account_id=account.account_id,
        agency_id=account.agency_id,
        subscription_id="sub_synthetic",
        plan="essential",
        minutes=120,
        hourly_amount=8500,
        amount=17000,
        status="open",
        session_id="cs_test_synthetic",
    )
    remote = {
        "livemode": False,
        "customer": account.customer_id,
        "mode": "payment",
        "client_reference_id": str(topup.id),
        "amount_total": 17000,
        "currency": "usd",
        "metadata": {
            "hvacline_topup_id": str(topup.id),
            "hvacline_account_id": str(account.account_id),
        },
        "status": status,
        "payment_status": payment,
        "url": "https://checkout.stripe.com/c/pay/cs_test_synthetic",
    }
    gateway = Mock()
    gateway.retrieve_checkout.return_value = remote
    service = BillingService(Mock(), billing_settings(), gateway)
    service._sync_topup(account, topup)
    assert topup.status == expected
    assert (topup.credited_at is not None) == (expected == "paid")
    credited = topup.credited_at
    service._sync_topup(account, topup)
    assert topup.credited_at == credited
    remote["amount_total"] = 1
    with pytest.raises(ApiError):
        service._sync_topup(account, topup)


def test_signed_live_webhooks_and_modified_payloads_are_rejected() -> None:
    secret = "whsec_synthetic_testing_only"
    gateway = StripeGateway(billing_settings(stripe_webhook_secret=secret))
    timestamp = int(time.time())

    def signed(live: bool) -> tuple[bytes, str]:
        body = json.dumps(
            {
                "id": "evt_synthetic",
                "object": "event",
                "livemode": live,
                "type": "invoice.paid",
                "data": {"object": {}},
            }
        ).encode()
        signature = hmac.new(
            secret.encode(), str(timestamp).encode() + b"." + body, hashlib.sha256
        ).hexdigest()
        return body, f"t={timestamp},v1={signature}"

    body, signature = signed(False)
    assert gateway.verify_event(body, signature)["livemode"] is False
    with pytest.raises(ApiError):
        gateway.verify_event(body + b" ", signature)
    live_body, live_signature = signed(True)
    with pytest.raises(ApiError):
        gateway.verify_event(live_body, live_signature)


@pytest.mark.parametrize(
    "value",
    [
        "https://checkout.stripe.com.evil.test",
        "javascript:alert(1)",
        "http://checkout.stripe.com",
        "https://checkout.stripe.com:444/pay",
        "https://user@checkout.stripe.com/pay",
    ],
)
def test_checkout_redirect_hosts_are_restricted(value: str) -> None:
    with pytest.raises(ApiError):
        stripe_url(value, "checkout")


def test_purchase_inputs_reject_spoofed_prices_and_implicit_consent() -> None:
    for hours in (0, -1, 41, 1.5, True):
        with pytest.raises(ValidationError):
            TopUpCreate(
                hours=hours,
                request_id=uuid4(),
                accepted_amount=100,
                explicit_confirmation=True,
            )
    with pytest.raises(ValidationError):
        CheckoutCreate(
            plan="essential",
            request_id=uuid4(),
            accepted_amount=24900,
            explicit_confirmation=1,
        )
