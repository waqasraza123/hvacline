from datetime import UTC, datetime
from typing import Any, cast

from insurance_operations.billing.catalog import PLANS, PaidPlanKey, PlanKey
from insurance_operations.billing.settings import BillingSettings
from insurance_operations.database.models.billing import BillingAccount


def stripe_datetime(value: object) -> datetime | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            return datetime.fromtimestamp(value, UTC)
        except (ValueError, OverflowError, OSError):
            return None
    return None


def active_plan(account: BillingAccount | None) -> PlanKey:
    now = datetime.now(UTC)
    if (
        account
        and not account.review_required
        and account.status == "active"
        and account.plan in {"essential", "comfort", "complete"}
        and account.period_start
        and account.period_end
        and account.paid_through
        and account.period_start <= now < min(account.period_end, account.paid_through)
    ):
        return cast(PlanKey, account.plan)
    return "none"


def apply_subscription(
    account: BillingAccount, data: dict[str, Any], settings: BillingSettings
) -> None:
    account.plan, account.price_id = "none", None
    account.period_start, account.period_end, account.paid_through = None, None, None
    account.subscription_id = (
        data.get("id") if isinstance(data.get("id"), str) else None
    )
    account.status = str(data.get("status", "unknown"))
    account.cancel_at_period_end = data.get("cancel_at_period_end") is True
    cancel_at = stripe_datetime(data.get("cancel_at"))
    if (
        data.get("customer") != account.customer_id
        or data.get("livemode") is not settings.stripe_live_mode
        or data.get("metadata", {}).get("hvacline_account_id")
        != str(account.account_id)
    ):
        account.status = "needs_review"
        return
    items = data.get("items", {}).get("data", [])
    if not isinstance(items, list) or len(items) != 1 or items[0].get("quantity") != 1:
        account.status = "needs_review"
        return
    item = items[0]
    price = item.get("price", {})
    plan = next(
        (
            key
            for key, value in {
                "essential": settings.stripe_essential_price_id,
                "comfort": settings.stripe_comfort_price_id,
                "complete": settings.stripe_complete_price_id,
            }.items()
            if value and value == price.get("id")
        ),
        None,
    )
    if (
        plan is None
        or price.get("product") != settings.stripe_product_id
        or price.get("currency") != "usd"
        or price.get("unit_amount") != PLANS[cast(PaidPlanKey, plan)].amount
        or price.get("recurring", {}).get("interval") != "month"
        or price.get("recurring", {}).get("interval_count") != 1
        or price.get("recurring", {}).get("usage_type") != "licensed"
        or price.get("billing_scheme") != "per_unit"
    ):
        account.status = "needs_review"
        return
    invoice = data.get("latest_invoice")
    if (
        account.status != "active"
        or not isinstance(invoice, dict)
        or invoice.get("status") != "paid"
        or invoice.get("customer") != account.customer_id
    ):
        return
    start = stripe_datetime(
        item.get("current_period_start", data.get("current_period_start"))
    )
    end = stripe_datetime(
        item.get("current_period_end", data.get("current_period_end"))
    )
    if start is None or end is None or end <= start:
        account.status = "needs_review"
        return
    if cancel_at is not None and start < cancel_at <= end:
        end = cancel_at
        account.cancel_at_period_end = True
    account.plan, account.price_id = plan, str(price["id"])
    account.period_start, account.period_end, account.paid_through = start, end, end
