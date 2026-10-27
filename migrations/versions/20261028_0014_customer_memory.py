from collections.abc import Sequence
from uuid import UUID

import sqlalchemy as sa
from alembic import op

revision: str = "20261028_0014"
down_revision: str | None = "20261028_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def agency() -> sa.Column[UUID]:
    return sa.Column("agency_id", sa.Uuid(), sa.ForeignKey(
        "agencies.id", ondelete="RESTRICT"
    ), nullable=False)


def account(*, primary: bool = False) -> sa.Column[UUID]:
    return sa.Column("account_id", sa.Uuid(), sa.ForeignKey(
        "customer_accounts.id", ondelete="RESTRICT"
    ), nullable=False, primary_key=primary)


def identity() -> sa.Column[UUID]:
    return sa.Column("id", sa.Uuid(), primary_key=True,
                     server_default=sa.text("gen_random_uuid()"))


def upgrade() -> None:
    op.create_table(
        "customer_memory_policies", account(primary=True), agency(),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("retention_days", sa.Integer(), nullable=False),
        sa.Column("history_after", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_request_id", sa.Uuid()),
        sa.Column("last_fingerprint", sa.Text()),
        sa.CheckConstraint("revision >= 0", name="revision_valid"),
        sa.CheckConstraint("retention_days BETWEEN 1 AND 365", name="retention_valid"),
    )
    fact_values = (
        "(key = 'appointment_time' AND value IN ('MORNING', 'AFTERNOON')) OR "
        "(key = 'appointment_days' AND value IN ('WEEKDAYS', 'WEEKENDS')) OR "
        "(key = 'contact_preference' AND value IN ('PHONE', 'EMAIL')) OR "
        "(key = 'equipment_type' AND value IN "
        "('CENTRAL_AC', 'HEAT_PUMP', 'FURNACE', 'BOILER', 'MINI_SPLIT')) OR "
        "(key = 'equipment_brand' AND value IN ('CARRIER', 'TRANE', 'LENNOX', "
        "'GOODMAN', 'DAIKIN', 'RHEEM', 'MITSUBISHI', 'YORK', 'BRYANT', 'AMANA')) OR "
        "(key = 'equipment_fuel' AND value IN ('ELECTRIC', 'GAS', 'OIL')) OR "
        "(key = 'arrival_preference' AND value = 'CALL_FIRST') OR "
        "(key = 'site_access' AND value IN ('GATE', 'PETS'))"
    )
    op.create_table(
        "customer_memory_facts", identity(), agency(), account(),
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("source_intake_id", sa.Uuid(), sa.ForeignKey(
            "conversation_intakes.id", ondelete="RESTRICT"
        )),
        sa.Column("source_kind", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("account_id", "key", name="uq_memory_fact_account_key"),
        sa.CheckConstraint("expires_at > updated_at", name="expiry_valid"),
        sa.CheckConstraint(fact_values, name="value_valid"),
        sa.CheckConstraint(
            "(source_kind = 'CONVERSATION' AND source_intake_id IS NOT NULL) OR "
            "(source_kind = 'CUSTOMER_CONTROL' AND source_intake_id IS NULL)",
            name="source_valid",
        ),
    )
    op.create_index("ix_customer_memory_facts_expires", "customer_memory_facts", ["expires_at"])
    op.create_table(
        "customer_memory_summaries", agency(), account(),
        sa.Column("intake_id", sa.Uuid(), sa.ForeignKey(
            "conversation_intakes.id", ondelete="RESTRICT"
        ), primary_key=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("length(summary) BETWEEN 1 AND 240", name="summary_valid"),
    )
    op.create_index("ix_customer_memory_summaries_expires", "customer_memory_summaries", ["expires_at"])
    op.create_index("ix_memory_summaries_account_created", "customer_memory_summaries", ["account_id", "created_at"])
    op.create_table(
        "customer_whatsapp_identities", identity(), agency(), account(),
        sa.Column("phone_number_id", sa.Text(), nullable=False),
        sa.Column("caller_digest", sa.Text(), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("agency_id", "phone_number_id", "caller_digest",
                            name="uq_customer_whatsapp_identity"),
        sa.CheckConstraint("length(caller_digest) = 64", name="digest_valid"),
    )
    op.create_table(
        "customer_memory_pairings", identity(), agency(),
        sa.Column("binding_id", sa.Uuid(), sa.ForeignKey(
            "whatsapp_conversations.id", ondelete="RESTRICT"
        ), nullable=False, unique=True),
        sa.Column("code_digest", sa.Text(), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("length(code_digest) = 64", name="digest_valid"),
    )
    op.create_index("ix_customer_whatsapp_identities_expires", "customer_whatsapp_identities", ["expires_at"])
    op.create_index("ix_customer_whatsapp_identities_account", "customer_whatsapp_identities", ["account_id"])
    op.create_index("ix_customer_memory_pairings_expires", "customer_memory_pairings", ["expires_at"])
    op.add_column("whatsapp_conversations", sa.Column("customer_account_id", sa.Uuid()))
    op.create_foreign_key(
        "fk_whatsapp_conversations_customer_account_id_customer_accounts",
        "whatsapp_conversations", "customer_accounts", ["customer_account_id"],
        ["id"], ondelete="RESTRICT",
    )


def downgrade() -> None:
    tables = (
        "customer_memory_pairings", "customer_whatsapp_identities",
        "customer_memory_summaries", "customer_memory_facts", "customer_memory_policies",
    )
    if any(op.get_bind().scalar(sa.text(f"SELECT count(*) FROM {table}")) for table in tables):
        raise RuntimeError("Memory migration is forward-only when records exist")
    if op.get_bind().scalar(sa.text(
        "SELECT count(*) FROM whatsapp_conversations WHERE customer_account_id IS NOT NULL"
    )):
        raise RuntimeError("Verified conversation ownership must not be discarded")
    op.drop_constraint(
        "fk_whatsapp_conversations_customer_account_id_customer_accounts",
        "whatsapp_conversations", type_="foreignkey",
    )
    op.drop_column("whatsapp_conversations", "customer_account_id")
    for table in tables:
        op.drop_table(table)
