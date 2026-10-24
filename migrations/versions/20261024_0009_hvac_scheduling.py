from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261024_0009"
down_revision: str | None = "20260819_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "business_schedules",
        sa.Column(
            "agency_id",
            sa.Uuid(),
            sa.ForeignKey("agencies.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("configuration", postgresql.JSONB(), nullable=False),
    )
    op.create_table(
        "hvac_service_requests",
        sa.Column(
            "id",
            sa.Uuid(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "agency_id",
            sa.Uuid(),
            sa.ForeignKey("agencies.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "inbound_call_id",
            sa.Uuid(),
            sa.ForeignKey("inbound_calls.id", ondelete="RESTRICT"),
        ),
        sa.Column("customer_details", postgresql.JSONB(), nullable=False),
        sa.Column("service_details", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("fingerprint", sa.Text(), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("agency_id", "id", name="uq_hvac_requests_agency_id"),
        sa.UniqueConstraint("inbound_call_id", name="uq_hvac_requests_call"),
        sa.CheckConstraint(
            "status IN ('OPEN', 'BOOKED', 'CALLBACK_REQUESTED', "
            "'HANDOFF_REQUESTED', 'CLOSED')",
            name="status_valid",
        ),
    )
    op.create_index(
        "ix_hvac_service_requests_agency_id", "hvac_service_requests", ["agency_id"]
    )
    op.create_table(
        "hvac_appointments",
        sa.Column(
            "id",
            sa.Uuid(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "agency_id",
            sa.Uuid(),
            sa.ForeignKey("agencies.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("service_request_id", sa.Uuid(), nullable=False),
        sa.Column("team_key", sa.Text(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("hold_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("idempotency_key", sa.Text(), nullable=False),
        sa.Column("fingerprint", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["agency_id", "service_request_id"],
            ["hvac_service_requests.agency_id", "hvac_service_requests.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "agency_id", "idempotency_key", name="uq_hvac_appointments_idempotency"
        ),
        sa.CheckConstraint("ends_at > starts_at", name="time_order_valid"),
        sa.CheckConstraint(
            "status IN ('HELD', 'CONFIRMED', 'CANCELLED', 'EXPIRED')",
            name="status_valid",
        ),
    )
    op.create_index(
        "ix_hvac_appointments_agency_id", "hvac_appointments", ["agency_id"]
    )


def downgrade() -> None:
    op.drop_table("hvac_appointments")
    op.drop_table("hvac_service_requests")
    op.drop_table("business_schedules")
