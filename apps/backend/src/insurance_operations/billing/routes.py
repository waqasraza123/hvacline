import secrets
from collections.abc import Callable
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from starlette.concurrency import run_in_threadpool

from insurance_operations.actors import ActorContext
from insurance_operations.billing.catalog import PLANS
from insurance_operations.billing.errors import billing_error
from insurance_operations.billing.gateway import StripeGateway
from insurance_operations.billing.schemas import (
    BillingRead,
    CatalogRead,
    CheckoutCreate,
    LaborCreate,
    LaborRead,
    RedirectRead,
    TopUpCreate,
)
from insurance_operations.billing.service import BillingService, catalog_response
from insurance_operations.billing.settings import BillingSettings
from insurance_operations.database.models.customer_account import CustomerAccount
from insurance_operations.settings import ApiSettings


def create_billing_public_router(
    settings: BillingSettings, sessions: sessionmaker[Session]
) -> APIRouter:
    router = APIRouter(prefix="/api/v1/billing")
    service = BillingService(sessions, settings)

    @router.get("/plans", response_model=CatalogRead)
    def plans(response: Response) -> CatalogRead:
        response.headers["Cache-Control"] = "no-store"
        return catalog_response(settings)

    @router.post("/webhook")
    async def webhook(request: Request) -> dict[str, bool]:
        service._ready()
        body = bytearray()
        async for chunk in request.stream():
            if len(body) + len(chunk) > 1_048_576:
                raise billing_error(
                    413, "stripe_event_too_large", "Webhook body is too large."
                )
            body.extend(chunk)
        event = StripeGateway(settings).verify_event(
            bytes(body), request.headers.get("stripe-signature", "")
        )
        await run_in_threadpool(service.receive_event, event)
        return {"received": True}

    return router


def create_billing_customer_router(
    settings: BillingSettings,
    sessions: sessionmaker[Session],
    actor_dependency: Callable[..., ActorContext],
) -> APIRouter:
    router = APIRouter(prefix="/billing")
    service = BillingService(sessions, settings)

    def account(
        actor: Annotated[ActorContext, Depends(actor_dependency)], response: Response
    ) -> CustomerAccount:
        response.headers["Cache-Control"] = "no-store"
        with sessions() as session:
            row = session.scalar(
                select(CustomerAccount).where(
                    CustomerAccount.app_user_id == actor.app_user_id,
                    CustomerAccount.agency_id == actor.agency_id,
                )
            )
            if row is None:
                raise billing_error(
                    404,
                    "billing_unavailable",
                    "Billing is not available for this business.",
                )
            return row

    Account = Annotated[CustomerAccount, Depends(account)]

    @router.get("/status", response_model=BillingRead)
    def summary(customer: Account) -> BillingRead:
        return service.summary(customer.id)

    @router.get("/history")
    def history(customer: Account) -> dict[str, Any]:
        return service.history(customer.id)

    @router.post("/checkout", response_model=RedirectRead)
    def checkout(data: CheckoutCreate, customer: Account) -> RedirectRead:
        if data.accepted_amount != PLANS[data.plan].amount:
            raise billing_error(
                409,
                "package_price_changed",
                "Refresh and review the current package price.",
            )
        return RedirectRead(
            url=service.create_checkout(
                customer.id, customer.email, data.plan, data.request_id
            )
        )

    @router.post("/topup", response_model=RedirectRead)
    def topup(data: TopUpCreate, customer: Account) -> RedirectRead:
        return RedirectRead(
            url=service.create_topup(
                customer.id, data.hours, data.accepted_amount, data.request_id
            )
        )

    @router.post("/topups/{request_id}/cancel")
    def cancel_topup(request_id: UUID, customer: Account) -> dict[str, bool]:
        service.cancel_topup(customer.id, request_id)
        return {"canceled": True}

    @router.post("/checkouts/{request_id}/cancel")
    def cancel_package(request_id: UUID, customer: Account) -> dict[str, bool]:
        service.cancel_package_checkout(customer.id, request_id)
        return {"canceled": True}

    @router.post("/portal", response_model=RedirectRead)
    def portal(customer: Account) -> RedirectRead:
        return RedirectRead(url=service.portal(customer.id))

    @router.post("/refresh", response_model=BillingRead)
    def refresh(customer: Account) -> BillingRead:
        return service.refresh(customer.id)

    return router


def create_billing_admin_router(
    api: ApiSettings,
    settings: BillingSettings,
    sessions: sessionmaker[Session],
    actor_dependency: Callable[..., ActorContext],
) -> APIRouter:
    router = APIRouter(prefix="/api/v1/development/billing")
    service = BillingService(sessions, settings)

    def admin(
        actor: Annotated[ActorContext, Depends(actor_dependency)],
        token: Annotated[str | None, Header(alias="X-Demo-Admin-Token")] = None,
    ) -> ActorContext:
        expected = api.demo_admin_token
        if (
            expected is None
            or len(expected.get_secret_value()) < 32
            or token is None
            or not secrets.compare_digest(
                token.encode(), expected.get_secret_value().encode()
            )
        ):
            raise billing_error(
                401,
                "billing_admin_required",
                "Business administrator authentication is required.",
            )
        return actor

    Admin = Annotated[ActorContext, Depends(admin)]

    @router.post("/labor", response_model=LaborRead)
    def record_labor(data: LaborCreate, actor: Admin) -> LaborRead:
        return service.record_labor(actor.agency_id, data)

    return router
