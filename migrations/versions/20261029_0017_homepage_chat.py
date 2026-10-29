from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261029_0017"
down_revision: str | None = "20261029_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "homepage_chat_visitors",
        sa.Column(
            "agency_id",
            sa.Uuid(),
            sa.ForeignKey("agencies.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column("token_hash", sa.Text(), primary_key=True),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column("request_id", sa.Uuid()),
        sa.Column("request_hash", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "state IN ('READY', 'PROCESSING', 'USED')", name="state_valid"
        ),
    )
    op.create_index(
        "ix_homepage_chat_visitors_expiry", "homepage_chat_visitors", ["expires_at"]
    )
    op.create_table(
        "homepage_chat_daily_usage",
        sa.Column(
            "agency_id",
            sa.Uuid(),
            sa.ForeignKey("agencies.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column("day", sa.Date(), primary_key=True),
        sa.Column("generations", sa.Integer(), nullable=False),
        sa.CheckConstraint("generations >= 0", name="generations_valid"),
    )


def downgrade() -> None:
    op.drop_table("homepage_chat_daily_usage")
    op.drop_index(
        "ix_homepage_chat_visitors_expiry", table_name="homepage_chat_visitors"
    )
    op.drop_table("homepage_chat_visitors")
