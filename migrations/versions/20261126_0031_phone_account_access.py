"""Customer approval for a single active telephone conversation."""

from alembic import op
import sqlalchemy as sa

revision = "20261126_0031"
down_revision = "20261126_0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_conversation_sessions_owned", "conversation_sessions", ["agency_id", "id"]
    )
    op.create_unique_constraint(
        "uq_customer_login_sessions_account", "customer_login_sessions", ["account_id", "id"]
    )
    op.create_table(
        "customer_phone_access",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("agency_id", sa.Uuid(), nullable=False),
        sa.Column("conversation_session_id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid()),
        sa.Column("login_session_id", sa.Uuid()),
        sa.Column("code_digest", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("share_memory", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("memory_revision", sa.Integer()),
        sa.ForeignKeyConstraint(
            ["agency_id", "conversation_session_id"],
            ["conversation_sessions.agency_id", "conversation_sessions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["agency_id", "account_id"], ["customer_accounts.agency_id", "customer_accounts.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["account_id", "login_session_id"], ["customer_login_sessions.account_id", "customer_login_sessions.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("conversation_session_id", name="uq_customer_phone_access_call"),
        sa.UniqueConstraint("code_digest", name="uq_customer_phone_access_code"),
        sa.CheckConstraint(
            "(approved_at IS NULL AND account_id IS NULL AND login_session_id IS NULL "
            "AND code_digest IS NOT NULL AND share_memory = false "
            "AND memory_revision IS NULL) OR "
            "(approved_at IS NOT NULL AND account_id IS NOT NULL "
            "AND login_session_id IS NOT NULL AND code_digest IS NULL)",
            name="approval_consistent",
        ),
        sa.CheckConstraint(
            "(share_memory = false AND memory_revision IS NULL) OR "
            "(share_memory = true AND memory_revision >= 0 AND memory_revision IS NOT NULL)",
            name="memory_consistent",
        ),
        sa.CheckConstraint("code_digest IS NULL OR length(code_digest) = 64", name="digest_valid"),
        sa.CheckConstraint("expires_at > created_at", name="expiry_valid"),
    )
    op.create_index("ix_customer_phone_access_account", "customer_phone_access", ["agency_id", "account_id"])


def downgrade() -> None:
    op.execute(
        "DO $$ BEGIN IF EXISTS (SELECT 1 FROM customer_phone_access) THEN "
        "RAISE EXCEPTION 'Retain telephone account approval history'; END IF; END $$"
    )
    op.drop_table("customer_phone_access")
    op.drop_constraint("uq_customer_login_sessions_account", "customer_login_sessions", type_="unique")
    op.drop_constraint("uq_conversation_sessions_owned", "conversation_sessions", type_="unique")
