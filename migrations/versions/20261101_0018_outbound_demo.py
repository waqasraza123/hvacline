from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261101_0018"
down_revision: str | None = "20261029_0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "outbound_demo_calls",
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
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("owner_hash", sa.Text(), nullable=False),
        sa.Column("destination_hash", sa.Text(), nullable=False),
        sa.Column("request_hash", sa.Text(), nullable=False),
        sa.Column("scenario", sa.Text(), nullable=False),
        sa.Column("consent_version", sa.Text(), nullable=False),
        sa.Column("consent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("transfer_status", sa.Text(), nullable=False),
        sa.Column("conversation_id", sa.Text(), unique=True),
        sa.Column("sip_call_id", sa.Text(), unique=True),
        sa.Column("last_event_hash", sa.Text()),
        sa.Column("finalized_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("agency_id", "request_id"),
        sa.CheckConstraint(
            "status IN ('reserved','dialing','in_progress','processing','unknown',"
            "'failed','rejected','unanswered','completed','disconnected')",
            name="status_valid",
        ),
        sa.CheckConstraint(
            "transfer_status IN ('not_requested','refer_accepted','failed','unconfirmed')",
            name="transfer_status_valid",
        ),
    )
    op.create_index(
        "ix_outbound_demo_calls_agency_created",
        "outbound_demo_calls",
        ["agency_id", "created_at"],
    )


def downgrade() -> None:
    if op.get_bind().scalar(sa.text("SELECT count(*) FROM outbound_demo_calls")):
        raise RuntimeError("Outbound consent and dialing evidence must be retained")
    op.drop_table("outbound_demo_calls")
