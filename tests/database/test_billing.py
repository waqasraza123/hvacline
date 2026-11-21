import asyncio
from collections.abc import Iterator
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from insurance_operations.actors import ActorContext
from insurance_operations.billing.catalog import PLANS, PaidPlanKey
from insurance_operations.billing.gateway import StripeGateway
from insurance_operations.billing.routes import create_billing_customer_router
from insurance_operations.billing.service import BillingService
from insurance_operations.billing.settings import BillingSettings
from insurance_operations.database.models.billing import (
    BillingCheckout,
    BillingEvent,
    BillingTopUp,
)
from insurance_operations.database.models.customer_account import CustomerAccount
from insurance_operations.database.models.identity import Agency, AppUser
from insurance_operations.errors import ApiError, api_error_handler


class SandboxStripe(StripeGateway):
    def __init__(self, settings: BillingSettings, account_id: UUID) -> None:
        super().__init__(settings)
        self.account_id = account_id
        self.remote: dict[str, dict[str, Any]] = {}
        self.topup_calls = 0
        self.start = int((datetime.now(UTC) - timedelta(days=1)).timestamp())
        self.end = int((datetime.now(UTC) + timedelta(days=29)).timestamp())

    def subscriptions(self, customer_id: str) -> list[dict[str, Any]]:
        return [
            {
                "id": "sub_synthetic",
                "customer": customer_id,
                "livemode": False,
                "status": "active",
                "metadata": {"hvacline_account_id": str(self.account_id)},
                "items": {
                    "data": [
                        {
                            "quantity": 1,
                            "current_period_start": self.start,
                            "current_period_end": self.end,
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
                "latest_invoice": {"status": "paid", "customer": customer_id},
            }
        ]

    def topup(
        self,
        customer_id: str,
        account_id: UUID,
        request_id: UUID,
        plan: PaidPlanKey,
        hours: int,
        amount: int,
    ) -> dict[str, Any]:
        self.topup_calls += 1
        reference = f"cs_test_{request_id.hex}"
        self.remote.setdefault(
            reference,
            {
                "id": reference,
                "livemode": False,
                "customer": customer_id,
                "client_reference_id": str(request_id),
                "mode": "payment",
                "amount_total": amount,
                "currency": "usd",
                "status": "open",
                "payment_status": "unpaid",
                "metadata": {
                    "hvacline_account_id": str(account_id),
                    "hvacline_topup_id": str(request_id),
                },
                "url": f"https://checkout.stripe.com/c/pay/{reference}",
            },
        )
        return self.remote[reference]

    def retrieve_checkout(self, session_id: str) -> dict[str, Any]:
        return self.remote[session_id]

    def expire_checkout(self, session_id: str) -> None:
        self.remote[session_id]["status"] = "expired"


@pytest.fixture
def billing(
    migrated_database: Engine,
) -> Iterator[tuple[BillingService, SandboxStripe, UUID]]:
    with migrated_database.connect() as connection:
        transaction = connection.begin()
        sessions = sessionmaker(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        with sessions() as session, session.begin():
            agency = Agency(
                name="Fictional Billing HVAC",
                slug=f"billing-{uuid4()}",
                environment_kind="DEVELOPMENT",
            )
            user = AppUser(auth_subject=uuid4(), display_name="Fictional Homeowner")
            session.add_all([agency, user])
            session.flush()
            account = CustomerAccount(
                agency_id=agency.id,
                app_user_id=user.id,
                email=f"{uuid4()}@example.test",
                password_hash="unused-synthetic",
                created_at=datetime.now(UTC),
            )
            session.add(account)
            session.flush()
            account_id = account.id
        settings = BillingSettings(
            _env_file=None,
            app_environment="test",
            billing_enabled=True,
            stripe_secret_key="sk_test_synthetic",
            stripe_webhook_secret="whsec_synthetic",
            stripe_product_id="prod_synthetic",
            stripe_essential_price_id="price_essential",
            stripe_comfort_price_id="price_comfort",
            stripe_complete_price_id="price_complete",
            stripe_portal_configuration_id="bpc_synthetic",
        )
        gateway = SandboxStripe(settings, account_id)
        service = BillingService(sessions, settings, gateway)
        with sessions() as session, session.begin():
            account = service._account(session, account_id)
            account.customer_id = "cus_synthetic"
            service._reconcile(session, account)
        try:
            yield service, gateway, account_id
        finally:
            transaction.rollback()


def test_extra_checkout_is_reused_and_only_paid_hours_are_credited_once(
    billing: tuple[BillingService, SandboxStripe, UUID],
) -> None:
    service, gateway, account_id = billing
    request_id = uuid4()
    assert service.summary(account_id).remaining_package_minutes == 180
    url = service.create_topup(account_id, 2, 17000, request_id)
    assert service.create_topup(account_id, 2, 17000, uuid4()) == url
    assert gateway.topup_calls == 1
    assert service.summary(account_id).purchased_minutes == 0
    reference, remote = next(iter(gateway.remote.items()))
    remote.update(status="complete", payment_status="paid")
    event = {
        "id": "evt_topup_synthetic",
        "livemode": False,
        "type": "checkout.session.completed",
        "data": {"object": remote},
    }
    service.receive_event(event)
    service.receive_event(event)
    assert service.summary(account_id).purchased_minutes == 120
    assert service.refresh(account_id).purchased_minutes == 120
    with service.sessions() as session:
        assert session.scalar(select(func.count()).select_from(BillingEvent)) == 1
        assert session.get(BillingTopUp, request_id).session_id == reference
    with pytest.raises(ApiError):
        service.create_topup(account_id, 2, 17000, request_id)


def test_pending_or_canceled_checkouts_never_add_hours(
    billing: tuple[BillingService, SandboxStripe, UUID],
) -> None:
    service, gateway, account_id = billing
    request_id = uuid4()
    service.create_topup(account_id, 1, 8500, request_id)
    with pytest.raises(ApiError):
        service.create_topup(account_id, 2, 17000, uuid4())
    service.cancel_topup(account_id, request_id)
    assert service.summary(account_id).purchased_minutes == 0
    assert service.history(account_id)["topups"][0].status == "expired"
    service.create_topup(account_id, 2, 17000, uuid4())
    assert gateway.topup_calls == 2


def test_underpayment_is_rejected_before_a_checkout_is_created(
    billing: tuple[BillingService, SandboxStripe, UUID],
) -> None:
    service, gateway, account_id = billing
    with pytest.raises(ApiError):
        service.create_topup(account_id, 3, 1, uuid4())
    assert gateway.topup_calls == 0
    assert not service.history(account_id)["topups"]


def test_package_renewal_does_not_erase_purchased_hours(
    billing: tuple[BillingService, SandboxStripe, UUID],
) -> None:
    service, gateway, account_id = billing
    service.create_topup(account_id, 1, 8500, uuid4())
    next(iter(gateway.remote.values())).update(status="complete", payment_status="paid")
    assert service.refresh(account_id).remaining_purchased_minutes == 60
    gateway.start += 30 * 86400
    gateway.end += 30 * 86400
    assert service.refresh(account_id).remaining_purchased_minutes == 60


def test_canceling_an_unpaid_checkout_does_not_cancel_a_paid_package(
    billing: tuple[BillingService, SandboxStripe, UUID],
) -> None:
    service, gateway, account_id = billing
    request_id = uuid4()
    reference = f"cs_test_{request_id.hex}"
    gateway.remote[reference] = {
        "id": reference,
        "customer": "cus_synthetic",
        "livemode": False,
        "mode": "subscription",
        "client_reference_id": str(account_id),
        "metadata": {"hvacline_account_id": str(account_id), "plan": "essential"},
        "status": "open",
        "payment_status": "unpaid",
    }
    with service.sessions() as session, session.begin():
        account = service._account(session, account_id)
        session.add(
            BillingCheckout(
                id=request_id,
                account_id=account_id,
                agency_id=account.agency_id,
                plan="essential",
                session_id=reference,
                status="open",
                created_at=datetime.now(UTC),
            )
        )
    service.cancel_package_checkout(account_id, request_id)
    assert not service.summary(account_id).checkout_pending
    assert service.summary(account_id).remaining_package_minutes == 180


@pytest.mark.parametrize("other_business", [False, True])
def test_automatic_business_resolution_keeps_customer_billing_isolated(
    billing: tuple[BillingService, SandboxStripe, UUID], other_business: bool
) -> None:
    service, gateway, account_id = billing
    request_id = uuid4()
    service.create_topup(account_id, 1, 8500, request_id)
    with service.sessions() as session, session.begin():
        customer = session.get(CustomerAccount, account_id)
        assert customer is not None
        agency = session.get(Agency, customer.agency_id)
        assert agency is not None
        owner = ActorContext(
            app_user_id=customer.app_user_id,
            display_name="Fictional Homeowner",
            agency_id=agency.id,
            agency_name=agency.name,
            agency_environment=agency.environment_kind,
        )
        if other_business:
            agency = Agency(
                name="Another Fictional HVAC",
                slug=f"billing-isolation-{uuid4()}",
                environment_kind="DEVELOPMENT",
            )
            session.add(agency)
        user = AppUser(auth_subject=uuid4(), display_name="Another Homeowner")
        session.add(user)
        session.flush()
        other_customer = CustomerAccount(
            agency_id=agency.id,
            app_user_id=user.id,
            email=f"{uuid4()}@example.test",
            password_hash="unused-synthetic",
            created_at=datetime.now(UTC),
        )
        session.add(other_customer)
        session.flush()
        other_account_id = other_customer.id
        other_actor = ActorContext(
            app_user_id=user.id,
            display_name=user.display_name,
            agency_id=agency.id,
            agency_name=agency.name,
            agency_environment=agency.environment_kind,
        )
        other_billing = service._account(session, other_account_id)
        assert other_billing.agency_id == other_actor.agency_id

    def actor() -> ActorContext:
        return owner

    application = FastAPI()
    application.add_exception_handler(ApiError, api_error_handler)
    application.include_router(
        create_billing_customer_router(service.settings, service.sessions, actor)
    )

    async def requests() -> None:
        async with AsyncClient(
            transport=ASGITransport(app=application), base_url="http://test"
        ) as client:
            own = await client.get("/billing/status")
            assert own.status_code == 200
            assert own.json()["account_id"] == str(account_id)
            assert own.json()["checkout_enabled"] is True
            assert own.json()["remaining_package_minutes"] == 180

            application.dependency_overrides[actor] = lambda: other_actor
            other = await client.get("/billing/status")
            assert other.status_code == 200
            assert other.json()["account_id"] == str(other_account_id)
            assert other.json()["remaining_package_minutes"] == 0
            history = await client.get("/billing/history")
            assert history.status_code == 200
            assert history.json()["topups"] == []

            cancel = await client.post(f"/billing/topups/{request_id}/cancel")
            assert cancel.status_code == 404
            assert cancel.json()["error"]["code"] == "TOPUP_MISSING"

            mismatched = replace(owner, agency_id=uuid4())
            application.dependency_overrides[actor] = lambda: mismatched
            denied = await client.get("/billing/status")
            assert denied.status_code == 404
            assert denied.json()["error"]["code"] == "billing_unavailable"

    asyncio.run(requests())
    assert service.history(account_id)["topups"][0].status == "open"
    assert gateway.topup_calls == 1
