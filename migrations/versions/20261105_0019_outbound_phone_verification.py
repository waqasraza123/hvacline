from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261105_0019"
down_revision: str | None = "20261101_0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "outbound_phone_verifications",
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
        sa.Column("owner_hash", sa.Text(), nullable=False),
        sa.Column("destination_hash", sa.Text(), nullable=False),
        sa.Column("consent_version", sa.Text(), nullable=False),
        sa.Column("provider_verification_id", sa.Text(), unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True)),
        sa.Column("consumed_by_request_id", sa.Uuid()),
        sa.CheckConstraint("attempts BETWEEN 0 AND 5", name="attempts_valid"),
    )
    op.create_index(
        "ix_outbound_phone_verifications_created",
        "outbound_phone_verifications",
        ["agency_id", "created_at"],
    )


def downgrade() -> None:
    count = op.get_bind().scalar(
        sa.text("SELECT count(*) FROM outbound_phone_verifications")
    )
    if count:
        raise RuntimeError(
            "Retain phone verification evidence; roll back application only"
        )
    op.drop_table("outbound_phone_verifications")
