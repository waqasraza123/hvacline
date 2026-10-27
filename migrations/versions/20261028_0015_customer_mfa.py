from collections.abc import Sequence
from uuid import UUID

import sqlalchemy as sa
from alembic import op

revision: str = "20261028_0015"
down_revision: str | None = "20261028_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def account(*, primary: bool = False) -> sa.Column[UUID]:
    return sa.Column("account_id", sa.Uuid(), sa.ForeignKey(
        "customer_accounts.id", ondelete="RESTRICT"
    ), nullable=False, primary_key=primary)


def agency() -> sa.Column[UUID]:
    return sa.Column("agency_id", sa.Uuid(), sa.ForeignKey(
        "agencies.id", ondelete="RESTRICT"
    ), nullable=False)


def identity() -> sa.Column[UUID]:
    return sa.Column("id", sa.Uuid(), primary_key=True,
                     server_default=sa.text("gen_random_uuid()"))


def upgrade() -> None:
    op.create_table(
        "customer_mfa_factors", account(primary=True), agency(),
        sa.Column("secret_ciphertext", sa.Text()),
        sa.Column("enabled_at", sa.DateTime(timezone=True)),
        sa.Column("last_counter", sa.BigInteger()),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("failed_attempts", sa.Integer(), nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True)),
        sa.CheckConstraint("version > 0", name="version_valid"),
        sa.CheckConstraint("last_counter IS NULL OR last_counter >= 0", name="counter_valid"),
        sa.CheckConstraint("failed_attempts BETWEEN 0 AND 5", name="attempts_valid"),
        sa.CheckConstraint(
            "(enabled_at IS NULL AND secret_ciphertext IS NULL AND last_counter IS NULL) OR "
            "(enabled_at IS NOT NULL AND secret_ciphertext IS NOT NULL AND last_counter IS NOT NULL)",
            name="enrollment_consistent",
        ),
    )
    op.create_table(
        "customer_mfa_challenges", identity(), account(), agency(),
        sa.Column("token_hash", sa.Text(), nullable=False, unique=True),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("secret_ciphertext", sa.Text()),
        sa.Column("factor_version", sa.Integer(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("purpose IN ('ENROLL', 'VERIFY', 'REPLACE')", name="purpose_valid"),
        sa.CheckConstraint("attempts BETWEEN 0 AND 5", name="attempts_valid"),
        sa.CheckConstraint("factor_version > 0", name="version_valid"),
        sa.CheckConstraint(
            "(purpose = 'VERIFY' AND secret_ciphertext IS NULL) OR "
            "(purpose IN ('ENROLL', 'REPLACE') AND "
            "(secret_ciphertext IS NOT NULL OR consumed_at IS NOT NULL))",
            name="secret_consistent",
        ),
    )
    op.create_index("ix_mfa_challenges_account_expiry", "customer_mfa_challenges", ["account_id", "expires_at"])
    op.create_table(
        "customer_mfa_recovery_codes", identity(), account(), agency(),
        sa.Column("code_hash", sa.Text(), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_mfa_recovery_account", "customer_mfa_recovery_codes", ["account_id"])
    op.add_column("customer_login_sessions", sa.Column("mfa_verified_at", sa.DateTime(timezone=True)))
    op.add_column("customer_login_sessions", sa.Column("mfa_version", sa.Integer()))
    op.create_check_constraint(
        "mfa_consistent", "customer_login_sessions",
        "(mfa_verified_at IS NULL AND mfa_version IS NULL) OR "
        "(mfa_verified_at IS NOT NULL AND mfa_version IS NOT NULL AND mfa_version > 0)",
    )
    op.execute(sa.text("UPDATE customer_login_sessions SET revoked_at = now() WHERE revoked_at IS NULL"))
    op.add_column("customer_whatsapp_identities", sa.Column(
        "mfa_version", sa.Integer(), nullable=False, server_default="0"
    ))


def downgrade() -> None:
    tables = ("customer_mfa_recovery_codes", "customer_mfa_challenges", "customer_mfa_factors")
    if any(op.get_bind().scalar(sa.text(f"SELECT count(*) FROM {table}")) for table in tables):
        raise RuntimeError("Customer MFA is forward-only when security records exist")
    if op.get_bind().scalar(sa.text(
        "SELECT count(*) FROM customer_login_sessions WHERE mfa_verified_at IS NOT NULL"
    )) or op.get_bind().scalar(sa.text(
        "SELECT count(*) FROM customer_whatsapp_identities WHERE mfa_version > 0"
    )):
        raise RuntimeError("MFA verification evidence must not be discarded")
    op.drop_column("customer_whatsapp_identities", "mfa_version")
    op.drop_constraint(op.f("ck_customer_login_sessions_mfa_consistent"), "customer_login_sessions", type_="check")
    op.drop_column("customer_login_sessions", "mfa_version")
    op.drop_column("customer_login_sessions", "mfa_verified_at")
    for table in tables:
        op.drop_table(table)
