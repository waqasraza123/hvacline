"""Approved alternate question phrasings for the existing knowledge base."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "20261109_0021"
down_revision = "20261108_0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agency_approved_faqs",
        sa.Column(
            "question_variations",
            JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.create_check_constraint(
        "question_variations_valid",
        "agency_approved_faqs",
        "jsonb_typeof(question_variations) = 'array' "
        "AND jsonb_array_length(question_variations) <= 8",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck_agency_approved_faqs_question_variations_valid"),
        "agency_approved_faqs",
        type_="check",
    )
    op.drop_column("agency_approved_faqs", "question_variations")
