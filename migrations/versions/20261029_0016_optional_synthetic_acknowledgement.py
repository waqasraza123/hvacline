from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261029_0016"
down_revision: str | None = "20261028_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "conversation_sessions", "synthetic_data_acknowledged_at", nullable=True
    )


def downgrade() -> None:
    unacknowledged_sessions = op.get_bind().scalar(
        sa.text(
            "SELECT count(*) FROM conversation_sessions "
            "WHERE synthetic_data_acknowledged_at IS NULL"
        )
    )
    if unacknowledged_sessions:
        raise RuntimeError(
            "Cannot downgrade while sessions without synthetic-data acknowledgement "
            "exist; acknowledgement must not be fabricated. Keep this revision "
            "or use a disposable database."
        )
    op.alter_column(
        "conversation_sessions", "synthetic_data_acknowledged_at", nullable=False
    )
