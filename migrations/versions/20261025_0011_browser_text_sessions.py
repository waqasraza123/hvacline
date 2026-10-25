from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261025_0011"
down_revision: str | None = "20261025_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "conversation_sessions",
        sa.Column("input_mode", sa.Text(), nullable=False, server_default="VOICE"),
    )
    op.alter_column("conversation_sessions", "microphone_consent_at", nullable=True)
    op.create_check_constraint(
        op.f("ck_conversation_sessions_input_mode_valid"),
        "conversation_sessions",
        "input_mode IN ('VOICE', 'TEXT')",
    )
    op.create_check_constraint(
        op.f("ck_conversation_sessions_input_mode_consent_consistent"),
        "conversation_sessions",
        "(input_mode = 'VOICE' AND microphone_consent_at IS NOT NULL) OR "
        "(input_mode = 'TEXT' AND channel = 'BROWSER' "
        "AND microphone_consent_at IS NULL)",
    )


def downgrade() -> None:
    text_sessions = op.get_bind().scalar(
        sa.text("SELECT count(*) FROM conversation_sessions WHERE input_mode = 'TEXT'")
    )
    if text_sessions:
        raise RuntimeError(
            "Cannot downgrade while text sessions exist; microphone consent "
            "must not be fabricated. Keep this revision or use a disposable database."
        )
    op.drop_constraint(
        op.f("ck_conversation_sessions_input_mode_consent_consistent"),
        "conversation_sessions",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_conversation_sessions_input_mode_valid"),
        "conversation_sessions",
        type_="check",
    )
    op.alter_column("conversation_sessions", "microphone_consent_at", nullable=False)
    op.drop_column("conversation_sessions", "input_mode")
