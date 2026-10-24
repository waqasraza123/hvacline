from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261025_0010"
down_revision: str | None = "20261024_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "customer_accounts",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("agency_id", sa.Uuid(), sa.ForeignKey("agencies.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("app_user_id", sa.Uuid(), sa.ForeignKey("app_users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("agency_id", "email", name="uq_customer_accounts_email"),
        sa.UniqueConstraint("app_user_id"),
    )
    op.create_table(
        "customer_login_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("account_id", sa.Uuid(), sa.ForeignKey("customer_accounts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_customer_login_sessions_account_id", "customer_login_sessions", ["account_id"])
    op.create_table(
        "customer_auth_limits",
        sa.Column("key", sa.Text(), primary_key=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.add_column("hvac_service_requests", sa.Column("conversation_session_id", sa.Uuid()))
    op.create_foreign_key("fk_hvac_requests_browser_session", "hvac_service_requests", "conversation_sessions", ["conversation_session_id"], ["id"], ondelete="RESTRICT")
    op.create_unique_constraint("uq_hvac_requests_conversation", "hvac_service_requests", ["conversation_session_id"])


def downgrade() -> None:
    op.drop_constraint("uq_hvac_requests_conversation", "hvac_service_requests", type_="unique")
    op.drop_constraint("fk_hvac_requests_browser_session", "hvac_service_requests", type_="foreignkey")
    op.drop_column("hvac_service_requests", "conversation_session_id")
    op.drop_table("customer_auth_limits")
    op.drop_table("customer_login_sessions")
    op.drop_table("customer_accounts")
