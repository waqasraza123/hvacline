"""HVACLine homeowner subscriptions, checkout reservations and Stripe receipts."""

from uuid import UUID

import sqlalchemy as sa
from alembic import op

revision = "20261108_0020"
down_revision = "20261105_0019"
branch_labels = None
depends_on = None


def account(*, primary: bool = False) -> sa.Column[UUID]:
    return sa.Column(
        "account_id",
        sa.Uuid(),
        sa.ForeignKey("customer_accounts.id", ondelete="RESTRICT"),
        nullable=False,
        primary_key=primary,
    )


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_customer_accounts_agency_id", "customer_accounts", ["agency_id", "id"]
    )
    op.create_table(
        "billing_accounts",
        account(primary=True),
        sa.Column(
            "agency_id",
            sa.Uuid(),
            sa.ForeignKey("agencies.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "review_required", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.UniqueConstraint(
            "agency_id", "account_id", name="uq_billing_accounts_agency_account"
        ),
        sa.ForeignKeyConstraint(
            ["agency_id", "account_id"],
            ["customer_accounts.agency_id", "customer_accounts.id"],
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint("livemode = false", name="test_mode_only"),
        sa.Column("customer_id", sa.Text(), unique=True),
        sa.Column("customer_started_at", sa.DateTime(timezone=True)),
        sa.Column("livemode", sa.Boolean(), nullable=False),
        sa.Column("subscription_id", sa.Text(), unique=True),
        sa.Column("price_id", sa.Text()),
        sa.Column("plan", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True)),
        sa.Column("period_end", sa.DateTime(timezone=True)),
        sa.Column("paid_through", sa.DateTime(timezone=True)),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "plan IN ('none','essential','comfort','complete')", name="plan_valid"
        ),
    )
    op.create_table(
        "billing_checkouts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        account(),
        sa.Column(
            "agency_id",
            sa.Uuid(),
            sa.ForeignKey("agencies.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["agency_id", "account_id"],
            ["billing_accounts.agency_id", "billing_accounts.account_id"],
            ondelete="RESTRICT",
        ),
        sa.Column("plan", sa.Text(), nullable=False),
        sa.Column("session_id", sa.Text(), unique=True),
        sa.Column("url", sa.Text()),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "plan IN ('essential','comfort','complete')", name="plan_valid"
        ),
        sa.CheckConstraint(
            "status IN ('creating','open','complete','expired')", name="status_valid"
        ),
    )
    op.create_index(
        "ix_billing_checkouts_account_created",
        "billing_checkouts",
        ["account_id", "created_at"],
    )
    op.create_table(
        "billing_events",
        sa.Column("event_id", sa.Text(), primary_key=True),
        account(),
        sa.Column(
            "agency_id",
            sa.Uuid(),
            sa.ForeignKey("agencies.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["agency_id", "account_id"],
            ["billing_accounts.agency_id", "billing_accounts.account_id"],
            ondelete="RESTRICT",
        ),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("customer_id", sa.Text(), nullable=False),
        sa.Column("object_id", sa.Text(), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_billing_events_pending", "billing_events", ["account_id", "processed_at"]
    )

    op.create_table(
        "billing_topups",
        sa.Column("id", sa.Uuid(), primary_key=True),
        account(),
        sa.Column(
            "agency_id",
            sa.Uuid(),
            sa.ForeignKey("agencies.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["agency_id", "account_id"],
            ["billing_accounts.agency_id", "billing_accounts.account_id"],
            ondelete="RESTRICT",
        ),
        sa.Column("subscription_id", sa.Text(), nullable=False),
        sa.Column("plan", sa.Text(), nullable=False),
        sa.Column("minutes", sa.Integer(), nullable=False),
        sa.Column("hourly_amount", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Text(), unique=True),
        sa.Column("url", sa.Text()),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("credited_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "plan IN ('essential','comfort','complete')", name="plan_valid"
        ),
        sa.CheckConstraint(
            "minutes BETWEEN 60 AND 2400 AND minutes % 60 = 0", name="minutes_valid"
        ),
        sa.CheckConstraint(
            "hourly_amount > 0 AND amount = minutes / 60 * hourly_amount",
            name="amount_valid",
        ),
        sa.CheckConstraint(
            "status IN ('creating','open','paid','expired')", name="status_valid"
        ),
        sa.CheckConstraint(
            "(status = 'paid') = (credited_at IS NOT NULL)", name="credit_consistent"
        ),
    )
    op.create_index(
        "ix_billing_topups_account_created",
        "billing_topups",
        ["account_id", "created_at"],
    )
    op.create_table(
        "billing_labor",
        sa.Column("id", sa.Uuid(), primary_key=True),
        account(),
        sa.Column(
            "agency_id",
            sa.Uuid(),
            sa.ForeignKey("agencies.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["agency_id", "account_id"],
            ["billing_accounts.agency_id", "billing_accounts.account_id"],
            ondelete="RESTRICT",
        ),
        sa.Column("appointment_id", sa.Uuid(), unique=True, nullable=False),
        sa.ForeignKeyConstraint(
            ["agency_id", "appointment_id"],
            ["hvac_appointments.agency_id", "hvac_appointments.id"],
            ondelete="RESTRICT",
        ),
        sa.Column("minutes", sa.Integer(), nullable=False),
        sa.Column("package_minutes", sa.Integer(), nullable=False),
        sa.Column("purchased_minutes", sa.Integer(), nullable=False),
        sa.Column("subscription_id", sa.Text()),
        sa.Column("period_start", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            (
                "minutes BETWEEN 1 AND 1440 AND package_minutes >= "
                "0 AND purchased_minutes >= 0 AND minutes = "
                "package_minutes + purchased_minutes"
            ),
            name="minutes_valid",
        ),
        sa.CheckConstraint(
            "package_minutes = 0 OR period_start IS NOT NULL", name="period_required"
        ),
    )
    op.create_index(
        "ix_billing_labor_account_period",
        "billing_labor",
        ["account_id", "period_start"],
    )


def downgrade() -> None:
    tables = (
        "billing_labor",
        "billing_topups",
        "billing_events",
        "billing_checkouts",
        "billing_accounts",
    )
    for table in tables:
        if op.get_bind().scalar(sa.text(f"SELECT EXISTS (SELECT 1 FROM {table})")):
            raise RuntimeError(
                "Retain billing customer bindings, checkout "
                "reservations and Stripe receipts; roll back "
                "application only"
            )
    for table in tables:
        op.drop_table(table)
    op.drop_constraint(
        "uq_customer_accounts_agency_id", "customer_accounts", type_="unique"
    )
