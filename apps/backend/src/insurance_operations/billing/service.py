from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from urllib.parse import urlsplit
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.billing.catalog import CORE_FEATURES, PLANS, PaidPlanKey
from insurance_operations.billing.errors import billing_error
from insurance_operations.billing.gateway import StripeGateway
from insurance_operations.billing.schemas import (
    BillingRead,
    CatalogRead,
    LaborCreate,
    LaborRead,
    PlanRead,
    TopUpRead,
)
from insurance_operations.billing.settings import BillingSettings
from insurance_operations.billing.state import (
    active_plan,
    apply_subscription,
    stripe_datetime,
)
from insurance_operations.database.models.billing import (
    BillingAccount,
    BillingCheckout,
    BillingEvent,
    BillingLabor,
    BillingTopUp,
)
from insurance_operations.database.models.conversation import ConversationSession
from insurance_operations.database.models.customer_account import CustomerAccount
from insurance_operations.database.models.hvac import Appointment, HvacServiceRequest

TERMINAL_SUBSCRIPTIONS = {"canceled", "incomplete_expired"}
SUBSCRIPTION_EVENTS = frozenset(
    {
        "checkout.session.completed",
        "checkout.session.expired",
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
        "customer.subscription.paused",
        "customer.subscription.resumed",
        "invoice.paid",
        "invoice.payment_failed",
        "invoice.payment_action_required",
        "checkout.session.async_payment_succeeded",
        "charge.refunded",
        "charge.dispute.created",
    }
)
REPLAY_WINDOW = timedelta(hours=23)


def stripe_url(value: object, kind: str) -> str:
    host = "checkout.stripe.com" if kind == "checkout" else "billing.stripe.com"
    if not isinstance(value, str) or len(value) > 4096:
        raise billing_error(
            502, "stripe_response_invalid", "Stripe returned an invalid redirect."
        )
    try:
        parsed = urlsplit(value)
        valid_port = parsed.port in {None, 443}
    except ValueError as error:
        raise billing_error(
            502, "stripe_response_invalid", "Stripe returned an invalid redirect."
        ) from error
    if (
        parsed.scheme != "https"
        or parsed.hostname != host
        or parsed.username
        or parsed.password
        or not valid_port
    ):
        raise billing_error(
            502, "stripe_response_invalid", "Stripe returned an invalid redirect."
        )
    return value


def catalog_response(settings: BillingSettings) -> CatalogRead:
    return CatalogRead(
        plans=[
            PlanRead(**asdict(plan), features=list(CORE_FEATURES))
            for plan in PLANS.values()
        ],
        checkout_enabled=StripeGateway(settings).ready,
        draft=not settings.billing_enabled,
    )


class BillingService:
    def __init__(
        self,
        sessions: sessionmaker[Session],
        settings: BillingSettings,
        gateway: StripeGateway | None = None,
    ) -> None:
        self.sessions, self.settings = sessions, settings
        self.gateway = gateway or StripeGateway(settings)

    def _ready(self) -> None:
        if not self.gateway.ready:
            raise billing_error(
                503, "billing_unavailable", "Paid billing is not available yet."
            )

    def _account(self, session: Session, account_id: UUID) -> BillingAccount:
        customer = session.get(CustomerAccount, account_id)
        if customer is None:
            raise billing_error(
                404,
                "billing_account_missing",
                "Billing is not available for this account.",
            )
        session.execute(
            insert(BillingAccount)
            .values(
                account_id=account_id,
                agency_id=customer.agency_id,
                livemode=self.settings.stripe_live_mode,
                plan="none",
                status="none",
                cancel_at_period_end=False,
            )
            .on_conflict_do_nothing(index_elements=["account_id"])
        )
        account = session.scalar(
            select(BillingAccount)
            .where(
                BillingAccount.account_id == account_id,
                BillingAccount.agency_id == customer.agency_id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if account is None:
            raise billing_error(
                503, "billing_unavailable", "Billing account is unavailable."
            )
        if account.livemode != self.settings.stripe_live_mode:
            raise billing_error(
                409,
                "billing_mode_mismatch",
                "This billing account belongs to another Stripe environment.",
            )
        return account

    def _ensure_customer(self, account_id: UUID, email: str) -> None:
        with self.sessions() as session:
            account = self._account(session, account_id)
            if account.customer_id:
                session.commit()
                return
            if account.customer_started_at is None:
                account.customer_started_at = datetime.now(UTC)
            session.commit()
            account = self._account(session, account_id)
            if not account.customer_id:
                if (
                    account.customer_started_at is None
                    or datetime.now(UTC) - account.customer_started_at >= REPLAY_WINDOW
                ):
                    raise billing_error(
                        409,
                        "billing_customer_unconfirmed",
                        "A previous customer creation is unconfirmed. The owner must reconcile it before retrying.",
                    )
                result = self.gateway.create_customer(account_id, email)
                if (
                    not isinstance(result.get("id"), str)
                    or not result["id"].startswith("cus_")
                    or result.get("livemode") is not self.settings.stripe_live_mode
                    or result.get("metadata", {}).get("hvacline_account_id")
                    != str(account_id)
                ):
                    raise billing_error(
                        502,
                        "stripe_response_invalid",
                        "Stripe customer identity could not be confirmed.",
                    )
                account.customer_id = result["id"]
            session.commit()

    def _reconcile(
        self, session: Session, account: BillingAccount
    ) -> list[dict[str, Any]]:
        if not account.customer_id:
            return []
        event_ids = list(
            session.scalars(
                select(BillingEvent.event_id)
                .where(
                    BillingEvent.account_id == account.account_id,
                    BillingEvent.processed_at.is_(None),
                )
                .limit(500)
            )
        )
        subscriptions = self.gateway.subscriptions(account.customer_id)
        current = [
            item
            for item in subscriptions
            if item.get("status") not in TERMINAL_SUBSCRIPTIONS
        ]
        if len(current) > 1:
            account.plan, account.status = "none", "needs_review"
        else:
            selected = (
                current[0]
                if current
                else next(
                    (
                        item
                        for item in subscriptions
                        if item.get("id") == account.subscription_id
                    ),
                    None,
                )
            )
            if selected is not None:
                apply_subscription(account, selected, self.settings)
            else:
                account.plan, account.status = (
                    "none",
                    "none" if not account.subscription_id else "canceled",
                )
                account.period_start, account.period_end, account.paid_through = (
                    None,
                    None,
                    None,
                )
        account.last_synced_at = datetime.now(UTC)
        if event_ids:
            session.execute(
                update(BillingEvent)
                .where(BillingEvent.event_id.in_(event_ids))
                .values(processed_at=account.last_synced_at)
            )
        return subscriptions

    def refresh(self, account_id: UUID) -> BillingRead:
        self._ready()
        with self.sessions() as session:
            account = self._account(session, account_id)
            subscriptions = self._reconcile(session, account)
            attempts = session.scalars(
                select(BillingCheckout)
                .where(
                    BillingCheckout.account_id == account_id,
                    BillingCheckout.session_id.is_not(None),
                    BillingCheckout.status.in_(["creating", "open"]),
                )
                .limit(50)
            )
            for attempt in attempts:
                remote = self._checkout_remote(attempt, account)
                if remote.get("status") == "expired":
                    attempt.status = "expired"
                elif remote.get("status") == "complete" and any(
                    item.get("id") == remote.get("subscription")
                    for item in subscriptions
                ):
                    attempt.status = "complete"
            for topup in session.scalars(
                select(BillingTopUp)
                .where(
                    BillingTopUp.account_id == account_id,
                    BillingTopUp.status.in_(["creating", "open"]),
                    BillingTopUp.session_id.is_not(None),
                )
                .limit(50)
            ):
                self._sync_topup(account, topup)
            session.commit()
        return self.summary(account_id)

    def summary(self, account_id: UUID) -> BillingRead:
        with self.sessions() as session:
            account = session.get(BillingAccount, account_id)
            if account and account.livemode != self.settings.stripe_live_mode:
                raise billing_error(
                    409,
                    "billing_mode_mismatch",
                    "This billing account belongs to another Stripe environment.",
                )
            pending = (
                session.scalar(
                    select(BillingEvent.event_id)
                    .where(
                        BillingEvent.account_id == account_id,
                        BillingEvent.processed_at.is_(None),
                    )
                    .limit(1)
                )
                is not None
            )
            pending_checkout_id = session.scalar(
                select(BillingCheckout.id)
                .where(
                    BillingCheckout.account_id == account_id,
                    BillingCheckout.status.in_(["creating", "open"]),
                )
                .order_by(BillingCheckout.created_at)
                .limit(1)
            )
            checkout_pending = pending_checkout_id is not None
            return BillingRead(
                account_id=account_id,
                plan=active_plan(account),
                subscription_status=account.status if account else "none",
                period_start=account.period_start if account else None,
                period_end=account.period_end if account else None,
                cancel_at_period_end=bool(account and account.cancel_at_period_end),
                last_synced_at=account.last_synced_at if account else None,
                checkout_enabled=self.gateway.ready,
                portal_enabled=bool(
                    self.gateway.ready and account and account.customer_id
                ),
                sync_pending=pending,
                checkout_pending=checkout_pending,
                pending_checkout_id=pending_checkout_id,
                review_required=bool(account and account.review_required),
                **self._balances(session, account),
            )

    def _checkout_remote(
        self, attempt: BillingCheckout, account: BillingAccount
    ) -> dict[str, Any]:
        remote = self.gateway.retrieve_checkout(cast(str, attempt.session_id))
        if (
            remote.get("customer") != account.customer_id
            or remote.get("client_reference_id") != str(account.account_id)
            or remote.get("livemode") is not self.settings.stripe_live_mode
            or remote.get("mode") != "subscription"
            or remote.get("metadata", {}).get("hvacline_account_id")
            != str(account.account_id)
            or remote.get("metadata", {}).get("plan") != attempt.plan
        ):
            raise billing_error(
                409,
                "checkout_identity_invalid",
                "The checkout identity needs owner review.",
            )
        return remote

    def create_checkout(
        self, account_id: UUID, email: str, plan: PaidPlanKey, request_id: UUID
    ) -> str:
        self._ready()
        if plan not in {"essential", "comfort", "complete"}:
            raise billing_error(
                422,
                "invalid_checkout_plan",
                "Choose a maintenance package for checkout.",
            )
        self._ensure_customer(account_id, email)
        with self.sessions() as session:
            account = self._account(session, account_id)
            if account.review_required:
                raise billing_error(
                    409,
                    "billing_review_required",
                    "Billing needs business review before another purchase.",
                )
            subscriptions = self._reconcile(session, account)
            if any(
                item.get("status") not in TERMINAL_SUBSCRIPTIONS
                for item in subscriptions
            ):
                session.commit()
                raise billing_error(
                    409,
                    "subscription_exists",
                    "Manage your existing subscription in the billing portal.",
                )
            existing = session.get(BillingCheckout, request_id)
            if existing and (
                existing.account_id != account_id or existing.plan != plan
            ):
                raise billing_error(
                    409,
                    "checkout_request_conflict",
                    "This checkout request does not match.",
                )
            attempts = list(
                session.scalars(
                    select(BillingCheckout)
                    .where(
                        BillingCheckout.account_id == account_id,
                        BillingCheckout.status.in_(["creating", "open"]),
                    )
                    .order_by(BillingCheckout.created_at)
                    .limit(51)
                )
            )
            if len(attempts) > 50:
                raise billing_error(
                    409,
                    "billing_history_review",
                    "Checkout history needs owner review.",
                )
            chosen = None
            for attempt in attempts:
                if attempt.session_id:
                    remote = self._checkout_remote(attempt, account)
                    status = remote.get("status")
                    if status == "complete":
                        terminal = any(
                            item.get("id") == remote.get("subscription")
                            and item.get("status") in TERMINAL_SUBSCRIPTIONS
                            for item in subscriptions
                        )
                        if not terminal:
                            session.commit()
                            raise billing_error(
                                409,
                                "checkout_pending",
                                "Your payment is being confirmed. Refresh billing before trying again.",
                            )
                        attempt.status = "complete"
                    elif status == "expired":
                        attempt.status = "expired"
                    elif status == "open":
                        if attempt.plan == plan:
                            url = stripe_url(remote.get("url"), "checkout")
                            session.commit()
                            return url
                        self.gateway.expire_checkout(attempt.session_id)
                        attempt.status = "expired"
                    else:
                        raise billing_error(
                            409,
                            "checkout_pending",
                            "Checkout status is unconfirmed. Keep this request and refresh billing.",
                        )
                elif attempt.plan == plan:
                    chosen = attempt
                else:
                    raise billing_error(
                        409,
                        "checkout_pending",
                        "Another checkout is unconfirmed. Keep that request before choosing a different plan.",
                    )
            if chosen is None:
                if existing is not None:
                    session.commit()
                    raise billing_error(
                        409,
                        "checkout_finished",
                        "This request has finished. Start a new checkout deliberately.",
                    )
                chosen = BillingCheckout(
                    id=request_id,
                    account_id=account_id,
                    agency_id=account.agency_id,
                    plan=plan,
                    status="creating",
                    created_at=datetime.now(UTC),
                )
                session.add(chosen)
            chosen_id = chosen.id
            session.commit()
            account = self._account(session, account_id)
            chosen = session.get(BillingCheckout, chosen_id, populate_existing=True)
            if chosen is None or chosen.status not in {"creating", "open"}:
                raise billing_error(
                    409,
                    "checkout_finished",
                    "Refresh your billing status before continuing.",
                )
            if chosen.session_id:
                remote = self._checkout_remote(chosen, account)
                if remote.get("status") != "open":
                    raise billing_error(
                        409,
                        "checkout_pending",
                        "Refresh billing before starting another checkout.",
                    )
                return stripe_url(remote.get("url"), "checkout")
            if datetime.now(UTC) - chosen.created_at >= REPLAY_WINDOW:
                raise billing_error(
                    409,
                    "checkout_unconfirmed",
                    "This checkout is unconfirmed and cannot be recreated. The owner must reconcile it.",
                )
            if any(
                item.get("status") not in TERMINAL_SUBSCRIPTIONS
                for item in self._reconcile(session, account)
            ):
                session.commit()
                raise billing_error(
                    409,
                    "subscription_exists",
                    "Manage your existing subscription in the billing portal.",
                )
            result = self.gateway.checkout(
                cast(str, account.customer_id), plan, chosen.id, account_id
            )
            if not isinstance(result.get("id"), str) or not result["id"].startswith(
                "cs_"
            ):
                raise billing_error(
                    502,
                    "stripe_response_invalid",
                    "Stripe did not provide a checkout reference.",
                )
            chosen.session_id = result["id"]
            remote = self._checkout_remote(chosen, account)
            if remote.get("status") != "open":
                raise billing_error(
                    409,
                    "checkout_pending",
                    "Checkout status is unconfirmed. Refresh billing shortly.",
                )
            chosen.url = stripe_url(remote.get("url"), "checkout")
            chosen.expires_at = stripe_datetime(remote.get("expires_at"))
            chosen.status = "open"
            session.commit()
            return chosen.url

    def portal(self, account_id: UUID) -> str:
        self._ready()
        with self.sessions() as session:
            account = self._account(session, account_id)
            if not account.customer_id:
                raise billing_error(
                    409, "billing_customer_missing", "Choose a paid plan first."
                )
            url = stripe_url(self.gateway.portal(account.customer_id), "portal")
            session.commit()
            return url

    def receive_event(self, event: dict[str, Any]) -> None:
        if event.get("livemode") is not False:
            raise billing_error(
                400,
                "billing_mode_mismatch",
                "Only sandbox webhook events are accepted.",
            )
        event_type = event.get("type")
        if event_type not in SUBSCRIPTION_EVENTS:
            return
        data = event.get("data", {}).get("object", {})
        if event_type == "charge.dispute.created":
            charge = data.get("charge")
            if not isinstance(charge, str) or not charge.startswith("ch_"):
                raise billing_error(
                    400,
                    "stripe_event_invalid",
                    "The dispute charge reference is invalid.",
                )
            with self.gateway.client() as client:
                remote_charge = client.v1.charges.retrieve(charge)
                if remote_charge.livemode is not False:
                    raise billing_error(
                        400,
                        "billing_mode_mismatch",
                        "Only sandbox disputes are accepted.",
                    )
                data = {**data, "customer": remote_charge.customer}
        if (
            event_type in {"charge.refunded", "charge.dispute.created"}
            and data.get("customer") is None
        ):
            return
        references = (event.get("id"), data.get("customer"), data.get("id"))
        if not all(
            isinstance(item, str)
            and 1 <= len(item) <= 128
            and all(c.isascii() and (c.isalnum() or c == "_") for c in item)
            for item in references
        ):
            raise billing_error(
                400, "stripe_event_invalid", "The event references are invalid."
            )
        with self.sessions() as session, session.begin():
            account = session.scalar(
                select(BillingAccount)
                .where(
                    BillingAccount.customer_id == data["customer"],
                    BillingAccount.livemode == self.settings.stripe_live_mode,
                )
                .with_for_update()
            )
            if account is None:
                return
            if event_type in {"charge.refunded", "charge.dispute.created"}:
                account.review_required = True
            if (
                event_type.startswith("checkout.session.")
                and data.get("mode") == "payment"
            ):
                topup = session.scalar(
                    select(BillingTopUp).where(
                        BillingTopUp.session_id == data["id"],
                        BillingTopUp.account_id == account.account_id,
                    )
                )
                if topup is None:
                    raw_id = data.get("metadata", {}).get("hvacline_topup_id")
                    try:
                        candidate = session.get(BillingTopUp, UUID(str(raw_id)))
                    except ValueError:
                        candidate = None
                    if (
                        candidate is not None
                        and candidate.account_id == account.account_id
                        and candidate.session_id is None
                    ):
                        candidate.session_id = data["id"]
                        self._sync_topup(account, candidate)
            account_id = account.account_id
            session.execute(
                insert(BillingEvent)
                .values(
                    event_id=event["id"],
                    account_id=account.account_id,
                    agency_id=account.agency_id,
                    event_type=event_type,
                    customer_id=data["customer"],
                    object_id=data["id"],
                )
                .on_conflict_do_nothing(index_elements=["event_id"])
            )

        self.refresh(account_id)

    def bind_customer(self, account_id: UUID, customer_id: str) -> None:
        with self.sessions() as session:
            account = self._account(session, account_id)
            if account.customer_id and account.customer_id != customer_id:
                raise billing_error(
                    409,
                    "billing_binding_conflict",
                    "This account already has another customer binding.",
                )
            with self.gateway.client() as client:
                customer = client.v1.customers.retrieve(customer_id).to_dict()
            if (
                customer.get("deleted")
                or customer.get("livemode") is not self.settings.stripe_live_mode
                or customer.get("metadata", {}).get("hvacline_account_id")
                != str(account_id)
            ):
                raise billing_error(
                    409,
                    "billing_binding_conflict",
                    "The customer does not belong to this HVACLine account and Stripe mode.",
                )
            account.customer_id = customer_id
            session.commit()

    def bind_checkout(self, request_id: UUID, session_id: str) -> None:
        with self.sessions() as session:
            initial = session.get(BillingCheckout, request_id)
            if initial is None:
                raise billing_error(
                    404,
                    "checkout_missing",
                    "The reserved checkout request was not found.",
                )
            account = self._account(session, initial.account_id)
            attempt = session.get(BillingCheckout, request_id, populate_existing=True)
            if (
                attempt is None
                or attempt.session_id
                and attempt.session_id != session_id
            ):
                raise billing_error(
                    409,
                    "billing_binding_conflict",
                    "This request already has another checkout binding.",
                )
            attempt.session_id = session_id
            remote = self._checkout_remote(attempt, account)
            if remote.get("status") not in {"open", "complete", "expired"}:
                raise billing_error(
                    409,
                    "checkout_pending",
                    "The provider checkout status is unconfirmed.",
                )
            attempt.url = (
                stripe_url(remote.get("url"), "checkout")
                if remote.get("status") == "open"
                else None
            )
            attempt.expires_at = stripe_datetime(remote.get("expires_at"))
            attempt.status = "expired" if remote.get("status") == "expired" else "open"
            session.commit()

    def _balances(
        self, session: Session, account: BillingAccount | None
    ) -> dict[str, Any]:
        plan = active_plan(account)
        package = PLANS[cast(PaidPlanKey, plan)] if plan != "none" else None
        included = package.included_minutes if package else 0
        used_package = 0
        purchased = used_purchased = 0
        if account:
            if package:
                used_package = int(
                    session.scalar(
                        select(
                            func.coalesce(func.sum(BillingLabor.package_minutes), 0)
                        ).where(
                            BillingLabor.account_id == account.account_id,
                            BillingLabor.subscription_id == account.subscription_id,
                            BillingLabor.period_start == account.period_start,
                        )
                    )
                    or 0
                )
            purchased = int(
                session.scalar(
                    select(func.coalesce(func.sum(BillingTopUp.minutes), 0)).where(
                        BillingTopUp.account_id == account.account_id,
                        BillingTopUp.status == "paid",
                    )
                )
                or 0
            )
            used_purchased = int(
                session.scalar(
                    select(
                        func.coalesce(func.sum(BillingLabor.purchased_minutes), 0)
                    ).where(
                        BillingLabor.account_id == account.account_id,
                    )
                )
                or 0
            )
        return {
            "included_minutes": included,
            "used_package_minutes": used_package,
            "remaining_package_minutes": max(0, included - used_package),
            "purchased_minutes": purchased,
            "used_purchased_minutes": used_purchased,
            "remaining_purchased_minutes": max(0, purchased - used_purchased),
            "hourly_amount": package.hourly_amount if package else None,
        }

    def _sync_topup(
        self, account: BillingAccount, topup: BillingTopUp
    ) -> dict[str, Any]:
        if topup.session_id is None:
            raise billing_error(
                409,
                "topup_unconfirmed",
                "Keep the same request; this checkout is unconfirmed.",
            )
        remote = self.gateway.retrieve_checkout(topup.session_id)
        metadata = remote.get("metadata", {})
        if (
            remote.get("livemode") is not False
            or remote.get("customer") != account.customer_id
            or remote.get("mode") != "payment"
            or remote.get("client_reference_id") != str(topup.id)
            or metadata.get("hvacline_topup_id") != str(topup.id)
            or metadata.get("hvacline_account_id") != str(account.account_id)
            or remote.get("amount_total") != topup.amount
            or remote.get("currency") != "usd"
        ):
            raise billing_error(
                409,
                "topup_identity_invalid",
                "The extra-hours checkout needs business review.",
            )
        if (
            remote.get("status") == "complete"
            and remote.get("payment_status") == "paid"
        ):
            topup.status = "paid"
            if topup.credited_at is None:
                topup.credited_at = datetime.now(UTC)
        elif remote.get("status") == "expired" and topup.status != "paid":
            topup.status = "expired"
        elif remote.get("status") == "open" and topup.status != "paid":
            topup.status = "open"
            topup.url = stripe_url(remote.get("url"), "checkout")
        topup.expires_at = stripe_datetime(remote.get("expires_at"))
        return remote

    def create_topup(
        self, account_id: UUID, hours: int, accepted_amount: int, request_id: UUID
    ) -> str:
        self._ready()
        with self.sessions() as session:
            account = self._account(session, account_id)
            self._reconcile(session, account)
            if account.review_required:
                raise billing_error(
                    409,
                    "billing_review_required",
                    "Billing needs business review before another purchase.",
                )
            existing = session.get(BillingTopUp, request_id)
            if existing and (
                existing.account_id != account_id
                or existing.minutes != hours * 60
                or existing.amount != accepted_amount
            ):
                raise billing_error(
                    409,
                    "topup_request_conflict",
                    "This extra-hours request does not match.",
                )
            pending = list(
                session.scalars(
                    select(BillingTopUp)
                    .where(
                        BillingTopUp.account_id == account_id,
                        BillingTopUp.status.in_(["creating", "open"]),
                    )
                    .order_by(BillingTopUp.created_at)
                    .limit(51)
                )
            )
            if len(pending) > 50:
                raise billing_error(
                    409,
                    "billing_history_review",
                    "Checkout history needs business review.",
                )
            chosen = existing
            for attempt in pending:
                if attempt.session_id:
                    remote = self._sync_topup(account, attempt)
                    if attempt.status in {"paid", "expired"}:
                        continue
                    if remote.get("status") != "open":
                        session.commit()
                        raise billing_error(
                            409,
                            "topup_pending",
                            "Your previous payment is still being confirmed. Refresh billing.",
                        )
                if attempt.minutes != hours * 60 or attempt.amount != accepted_amount:
                    session.commit()
                    raise billing_error(
                        409,
                        "topup_pending",
                        "Finish or cancel the pending extra-hours checkout before changing the quantity.",
                    )
                chosen = attempt
                break
            if chosen and chosen.status in {"paid", "expired"}:
                session.commit()
                raise billing_error(
                    409,
                    "topup_finished",
                    "This checkout has finished. Refresh billing before a deliberate new purchase.",
                )
            if chosen and chosen.session_id:
                session.commit()
                return stripe_url(chosen.url, "checkout")
            if chosen is None:
                plan = active_plan(account)
                if plan == "none":
                    session.commit()
                    raise billing_error(
                        409,
                        "package_required",
                        "Buy and activate a maintenance package before adding hours.",
                    )
                package = PLANS[cast(PaidPlanKey, plan)]
                amount = hours * package.hourly_amount
                if accepted_amount != amount:
                    raise billing_error(
                        409,
                        "topup_price_changed",
                        "Refresh billing and review the current extra-hours price.",
                    )
                chosen = BillingTopUp(
                    id=request_id,
                    account_id=account_id,
                    agency_id=account.agency_id,
                    subscription_id=cast(str, account.subscription_id),
                    plan=plan,
                    minutes=hours * 60,
                    hourly_amount=package.hourly_amount,
                    amount=amount,
                    status="creating",
                    created_at=datetime.now(UTC),
                )
                session.add(chosen)
            chosen_id = chosen.id
            session.commit()
            account = self._account(session, account_id)
            chosen = session.get(BillingTopUp, chosen_id, populate_existing=True)
            if chosen is None or chosen.status not in {"creating", "open"}:
                raise billing_error(
                    409,
                    "topup_finished",
                    "Refresh billing before starting another purchase.",
                )
            if chosen.session_id:
                remote = self._sync_topup(account, chosen)
            else:
                if datetime.now(UTC) - chosen.created_at >= REPLAY_WINDOW:
                    raise billing_error(
                        409,
                        "topup_unconfirmed",
                        "This checkout needs business reconciliation; it cannot be recreated.",
                    )
                remote = self.gateway.topup(
                    cast(str, account.customer_id),
                    account_id,
                    chosen.id,
                    cast(PaidPlanKey, chosen.plan),
                    chosen.minutes // 60,
                    chosen.amount,
                )
                reference = remote.get("id")
                if not isinstance(reference, str) or not reference.startswith(
                    "cs_test_"
                ):
                    raise billing_error(
                        502,
                        "stripe_response_invalid",
                        "Stripe did not return a sandbox checkout reference.",
                    )
                chosen.session_id = reference
                remote = self._sync_topup(account, chosen)
            if chosen.status != "open":
                session.commit()
                raise billing_error(
                    409, "topup_pending", "Payment is being confirmed. Refresh billing."
                )
            url = stripe_url(remote.get("url"), "checkout")
            session.commit()
            return url

    def history(self, account_id: UUID) -> dict[str, Any]:
        with self.sessions() as session:
            topups = session.scalars(
                select(BillingTopUp)
                .where(BillingTopUp.account_id == account_id)
                .order_by(BillingTopUp.created_at.desc())
                .limit(50)
            )
            labor = session.scalars(
                select(BillingLabor)
                .where(BillingLabor.account_id == account_id)
                .order_by(BillingLabor.created_at.desc())
                .limit(50)
            )
            return {
                "topups": [TopUpRead.model_validate(item) for item in topups],
                "labor": [LaborRead.model_validate(item) for item in labor],
            }

    def record_labor(self, agency_id: UUID, data: LaborCreate) -> LaborRead:
        self._ready()
        with self.sessions() as session:
            match = session.execute(
                select(Appointment, CustomerAccount)
                .join(
                    HvacServiceRequest,
                    HvacServiceRequest.id == Appointment.service_request_id,
                )
                .join(
                    ConversationSession,
                    ConversationSession.id
                    == HvacServiceRequest.conversation_session_id,
                )
                .join(
                    CustomerAccount,
                    CustomerAccount.app_user_id == ConversationSession.initiated_by,
                )
                .where(
                    Appointment.id == data.appointment_id,
                    Appointment.agency_id == agency_id,
                    HvacServiceRequest.agency_id == agency_id,
                    ConversationSession.agency_id == agency_id,
                    CustomerAccount.agency_id == agency_id,
                )
            ).one_or_none()
            if match is None:
                raise billing_error(
                    404,
                    "billing_booking_missing",
                    "A booking linked to this homeowner account is required.",
                )
            appointment, customer = match
            if (
                appointment.status != "CONFIRMED"
                or appointment.starts_at > datetime.now(UTC)
            ):
                raise billing_error(
                    409,
                    "billing_booking_ineligible",
                    "Record completed labor only for a confirmed visit that has started.",
                )
            account = self._account(session, customer.id)
            self._reconcile(session, account)
            if account.review_required:
                raise billing_error(
                    409,
                    "billing_review_required",
                    "This account needs business review before using hours.",
                )
            existing = session.scalar(
                select(BillingLabor).where(
                    BillingLabor.appointment_id == appointment.id
                )
            )
            by_id = session.get(BillingLabor, data.request_id)
            if existing or by_id:
                row = existing or by_id
                assert row is not None
                if (
                    row.account_id != customer.id
                    or row.appointment_id != appointment.id
                    or row.minutes != data.minutes
                ):
                    raise billing_error(
                        409,
                        "labor_request_conflict",
                        "The saved labor record does not match. Ask the business to review it.",
                    )
                session.commit()
                return LaborRead.model_validate(row)
            balances = self._balances(session, account)
            package_minutes = min(data.minutes, balances["remaining_package_minutes"])
            purchased_minutes = data.minutes - package_minutes
            if purchased_minutes > balances["remaining_purchased_minutes"]:
                raise billing_error(
                    409,
                    "maintenance_hours_insufficient",
                    "The homeowner must purchase enough additional hours before this work can be recorded.",
                )
            row = BillingLabor(
                id=data.request_id,
                account_id=customer.id,
                agency_id=agency_id,
                appointment_id=appointment.id,
                minutes=data.minutes,
                package_minutes=package_minutes,
                purchased_minutes=purchased_minutes,
                subscription_id=account.subscription_id if package_minutes else None,
                period_start=account.period_start if package_minutes else None,
                created_at=datetime.now(UTC),
            )
            session.add(row)
            session.commit()
            return LaborRead.model_validate(row)

    def cancel_topup(self, account_id: UUID, request_id: UUID) -> None:
        self._ready()
        with self.sessions() as session:
            account = self._account(session, account_id)
            topup = session.get(BillingTopUp, request_id)
            if topup is None or topup.account_id != account_id:
                raise billing_error(
                    404, "topup_missing", "That checkout could not be found."
                )
            remote = self._sync_topup(account, topup)
            if topup.status == "paid":
                session.commit()
                raise billing_error(
                    409, "topup_paid", "This payment has completed. Refresh your hours."
                )
            if remote.get("status") == "open":
                self.gateway.expire_checkout(cast(str, topup.session_id))
                self._sync_topup(account, topup)
            if topup.status != "expired":
                raise billing_error(
                    409,
                    "topup_pending",
                    "Payment is being confirmed and cannot be canceled here.",
                )
            session.commit()

    def bind_topup(self, request_id: UUID, session_id: str) -> None:
        self._ready()
        with self.sessions() as session:
            initial = session.get(BillingTopUp, request_id)
            if initial is None:
                raise billing_error(
                    404,
                    "topup_missing",
                    "The reserved extra-hours request was not found.",
                )
            account = self._account(session, initial.account_id)
            topup = session.get(BillingTopUp, request_id, populate_existing=True)
            if topup is None or topup.session_id and topup.session_id != session_id:
                raise billing_error(
                    409,
                    "billing_binding_conflict",
                    "This request already has another checkout binding.",
                )
            topup.session_id = session_id
            self._sync_topup(account, topup)
            session.commit()

    def cancel_package_checkout(self, account_id: UUID, request_id: UUID) -> None:
        self._ready()
        with self.sessions() as session:
            account = self._account(session, account_id)
            attempt = session.get(BillingCheckout, request_id)
            if attempt is None or attempt.account_id != account_id:
                raise billing_error(
                    404, "checkout_missing", "That checkout could not be found."
                )
            if attempt.session_id is None:
                raise billing_error(
                    409,
                    "checkout_unconfirmed",
                    "This checkout needs reconciliation before cancellation.",
                )
            remote = self._checkout_remote(attempt, account)
            if remote.get("status") == "complete":
                self._reconcile(session, account)
                attempt.status = "complete"
                session.commit()
                raise billing_error(
                    409,
                    "checkout_finished",
                    "This checkout has completed. Refresh billing to view the package.",
                )
            if remote.get("status") == "open":
                self.gateway.expire_checkout(attempt.session_id)
                remote = self._checkout_remote(attempt, account)
            if remote.get("status") != "expired":
                raise billing_error(
                    409,
                    "checkout_pending",
                    "Payment is being confirmed and cannot be canceled here.",
                )
            attempt.status = "expired"
            session.commit()
