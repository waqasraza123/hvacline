from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261028_0013"
down_revision: str | None = "20261027_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        op.f("ck_conversation_sessions_channel_valid"),
        "conversation_sessions",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_conversation_sessions_channel_valid"),
        "conversation_sessions",
        "channel IN ('BROWSER', 'PHONE', 'WHATSAPP')",
    )
    op.drop_constraint(
        op.f("ck_conversation_sessions_channel_call_consistent"),
        "conversation_sessions",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_conversation_sessions_channel_call_consistent"),
        "conversation_sessions",
        "(channel IN ('BROWSER', 'WHATSAPP') AND inbound_call_id IS NULL) OR "
        "(channel = 'PHONE' AND inbound_call_id IS NOT NULL)",
    )
    op.create_table(
        "whatsapp_conversations",
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
        sa.Column("conversation_id", sa.Text(), nullable=False, unique=True),
        sa.Column("phone_number_id", sa.Text(), nullable=False),
        sa.Column("caller_digest", sa.Text(), nullable=False),
        sa.Column(
            "session_id",
            sa.Uuid(),
            sa.ForeignKey("conversation_sessions.id", ondelete="RESTRICT"),
            unique=True,
        ),
        sa.Column("initialized_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finalized_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("length(caller_digest) = 64", name="caller_digest_valid"),
        sa.CheckConstraint("expires_at > initialized_at", name="expiry_valid"),
    )
    op.create_index(
        "ix_whatsapp_conversations_agency_initialized",
        "whatsapp_conversations",
        ["agency_id", "initialized_at"],
    )


def downgrade() -> None:
    count = op.get_bind().scalar(sa.text("SELECT count(*) FROM whatsapp_conversations"))
    sessions = op.get_bind().scalar(
        sa.text("SELECT count(*) FROM conversation_sessions WHERE channel = 'WHATSAPP'")
    )
    if count or sessions:
        raise RuntimeError(
            "Cannot downgrade while WhatsApp records exist; "
            "retain this migration or use a disposable database"
        )
    op.drop_table("whatsapp_conversations")
    op.drop_constraint(
        op.f("ck_conversation_sessions_channel_call_consistent"),
        "conversation_sessions",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_conversation_sessions_channel_call_consistent"),
        "conversation_sessions",
        "(channel = 'BROWSER' AND inbound_call_id IS NULL) OR "
        "(channel = 'PHONE' AND inbound_call_id IS NOT NULL)",
    )
    op.drop_constraint(
        op.f("ck_conversation_sessions_channel_valid"),
        "conversation_sessions",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_conversation_sessions_channel_valid"),
        "conversation_sessions",
        "channel IN ('BROWSER', 'PHONE')",
    )
