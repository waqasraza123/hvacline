"""Owner-created businesses, invited staff and independent MFA sessions."""

from alembic import op
import sqlalchemy as sa

revision = "20261126_0030"
down_revision = "20261126_0029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("agency_memberships", sa.Column("role", sa.Text(), nullable=False, server_default="STAFF"))
    op.create_check_constraint(op.f("ck_agency_memberships_role_valid"), "agency_memberships", "role IN ('OWNER', 'ADMIN', 'STAFF')")
    op.create_table("workspace_businesses",
        sa.Column("agency_id", sa.Uuid(), sa.ForeignKey("agencies.id", ondelete="RESTRICT"), primary_key=True),
        sa.Column("creation_key", sa.Uuid(), nullable=False, unique=True),
        sa.Column("fingerprint", sa.Text(), nullable=False),
        sa.Column("owner_email", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_table("workspace_credentials",
        sa.Column("app_user_id", sa.Uuid(), sa.ForeignKey("app_users.id", ondelete="RESTRICT"), primary_key=True),
        sa.Column("email", sa.Text(), nullable=False, unique=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("secret_ciphertext", sa.Text(), nullable=False),
        sa.Column("last_totp_counter", sa.BigInteger(), nullable=False),
        sa.CheckConstraint("last_totp_counter >= 0", name="counter_valid"))
    op.create_table("workspace_sessions",
        sa.Column("token_digest", sa.Text(), primary_key=True),
        sa.Column("app_user_id", sa.Uuid(), sa.ForeignKey("app_users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)))
    op.create_index("ix_workspace_sessions_app_user_id", "workspace_sessions", ["app_user_id"])
    op.create_table("workspace_invitations",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("agency_id", sa.Uuid(), sa.ForeignKey("agencies.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("email", sa.Text(), nullable=False), sa.Column("role", sa.Text(), nullable=False),
        sa.Column("created_by", sa.Uuid()),
        sa.Column("token_digest", sa.Text(), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True)), sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("pending_name", sa.Text()), sa.Column("pending_password_hash", sa.Text()), sa.Column("pending_secret_ciphertext", sa.Text()),
        sa.Column("failed_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("row_version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.CheckConstraint("role IN ('OWNER', 'ADMIN', 'STAFF')", name="role_valid"),
        sa.CheckConstraint("failed_attempts BETWEEN 0 AND 5", name="attempts_valid"),
        sa.CheckConstraint("row_version > 0", name="version_positive"),
        sa.ForeignKeyConstraint(["agency_id", "created_by"], ["agency_memberships.agency_id", "agency_memberships.app_user_id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("agency_id", "id", name="uq_workspace_invitations_owned"))
    op.create_index("ix_workspace_invitations_agency_id", "workspace_invitations", ["agency_id"])
    op.execute("CREATE TRIGGER workspace_invitations_version BEFORE UPDATE ON workspace_invitations FOR EACH ROW EXECUTE FUNCTION set_mutable_record_metadata()")
    op.create_table("workspace_login_limits", sa.Column("key", sa.Text(), primary_key=True),
        sa.Column("attempts", sa.Integer(), nullable=False), sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("attempts >= 0", name="attempts_valid"))


def downgrade() -> None:
    op.execute("DO $$ BEGIN IF EXISTS (SELECT 1 FROM workspace_businesses) OR EXISTS (SELECT 1 FROM workspace_credentials) OR EXISTS (SELECT 1 FROM workspace_invitations) THEN RAISE EXCEPTION 'Retain business onboarding and staff identity history'; END IF; END $$")
    for table in ("workspace_login_limits", "workspace_sessions", "workspace_invitations", "workspace_credentials", "workspace_businesses"):
        op.drop_table(table)
    op.drop_constraint(op.f("ck_agency_memberships_role_valid"), "agency_memberships", type_="check")
    op.drop_column("agency_memberships", "role")
