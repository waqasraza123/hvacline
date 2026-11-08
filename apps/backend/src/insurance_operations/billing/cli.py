import argparse
import hashlib
import json
from uuid import UUID

from sqlalchemy.orm import sessionmaker

from insurance_operations.billing.catalog import PLANS
from insurance_operations.billing.gateway import StripeGateway
from insurance_operations.billing.service import BillingService
from insurance_operations.billing.settings import BillingSettings
from insurance_operations.database.connection import create_database_engine
from insurance_operations.settings import DatabaseSettings


def main() -> None:
    parser = argparse.ArgumentParser(
        description="HVACLine sandbox billing setup and reconciliation"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("setup-catalog")
    customer = sub.add_parser("bind-customer")
    customer.add_argument("account_id", type=UUID)
    customer.add_argument("customer_id")
    checkout = sub.add_parser("bind-checkout")
    checkout.add_argument("request_id", type=UUID)
    checkout.add_argument("session_id")
    topup = sub.add_parser("bind-topup")
    topup.add_argument("request_id", type=UUID)
    topup.add_argument("session_id")
    refresh = sub.add_parser("refresh")
    refresh.add_argument("account_id", type=UUID)
    arguments = parser.parse_args()
    settings = BillingSettings(
        billing_enabled=False if arguments.command == "setup-catalog" else True
    )
    gateway = StripeGateway(settings)
    if arguments.command == "setup-catalog":
        fingerprint = hashlib.sha256(
            json.dumps(
                {key: vars(value) for key, value in PLANS.items()}, sort_keys=True
            ).encode()
        ).hexdigest()[:16]
        with gateway.client() as client:
            if settings.stripe_product_id:
                product = client.v1.products.retrieve(settings.stripe_product_id)
                if product.livemode is not False or not product.active:
                    parser.error("A sandbox product is required")
            else:
                product = client.v1.products.create(
                    {
                        "name": "HVACLine home maintenance packages",
                        "description": "Prepaid technician maintenance hours with optional separately purchased extra hours.",
                        "metadata": {"hvacline_catalog": "maintenance_v1"},
                    },
                    options={
                        "idempotency_key": "hvacline:sandbox:maintenance-product:v1"
                    },
                )
            print(f"STRIPE_PRODUCT_ID={product.id}")
            for key, plan in PLANS.items():
                lookup = f"hvacline_{key}_{fingerprint}"
                prices = client.v1.prices.list({"lookup_keys": [lookup], "limit": 2})
                if prices.data:
                    price = prices.data[0]
                    if (
                        price.product != product.id
                        or price.livemode is not False
                        or price.unit_amount != plan.amount
                    ):
                        parser.error("Existing catalog price needs review")
                else:
                    price = client.v1.prices.create(
                        {
                            "product": product.id,
                            "currency": "usd",
                            "unit_amount": plan.amount,
                            "recurring": {"interval": "month"},
                            "lookup_key": lookup,
                            "nickname": f"{plan.name} · {plan.included_hours} maintenance hours/month",
                            "metadata": {
                                "hvacline_plan": key,
                                "included_hours": str(plan.included_hours),
                                "extra_hour_cents": str(plan.hourly_amount),
                            },
                        },
                        options={
                            "idempotency_key": f"hvacline:sandbox:price:{key}:{fingerprint}"
                        },
                    )
                print(f"STRIPE_{key.upper()}_PRICE_ID={price.id}")
            portal = client.v1.billing_portal.configurations.create(
                {
                    "business_profile": {
                        "headline": "Manage your HVACLine maintenance package"
                    },
                    "default_return_url": f"{settings.web_origin.rstrip('/')}/billing",
                    "features": {
                        "invoice_history": {"enabled": True},
                        "payment_method_update": {"enabled": True},
                        "customer_update": {
                            "enabled": True,
                            "allowed_updates": ["email", "name", "address"],
                        },
                        "subscription_cancel": {
                            "enabled": True,
                            "mode": "at_period_end",
                        },
                        "subscription_update": {"enabled": False},
                    },
                },
                options={"idempotency_key": f"hvacline:sandbox:portal:{product.id}:v1"},
            )
            print(f"STRIPE_PORTAL_CONFIGURATION_ID={portal.id}")
        return
    database = DatabaseSettings()
    engine = create_database_engine(database, service_name="billing-maintenance")
    try:
        service = BillingService(
            sessionmaker(bind=engine, expire_on_commit=False), settings
        )
        if arguments.command == "bind-customer":
            service.bind_customer(arguments.account_id, arguments.customer_id)
        elif arguments.command == "bind-checkout":
            service.bind_checkout(arguments.request_id, arguments.session_id)
        elif arguments.command == "bind-topup":
            service.bind_topup(arguments.request_id, arguments.session_id)
        else:
            service.refresh(arguments.account_id)
        print("Sandbox billing reconciliation completed")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
