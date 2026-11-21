"""Add business-scoped voice language intent. Provider evidence stays server-only."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261121_0028"
down_revision = "20261120_0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("agency_receptionist_settings", sa.Column(
        "voice_languages", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")))
    op.create_check_constraint(op.f("ck_agency_receptionist_settings_voice_languages_object"),
        "agency_receptionist_settings", "jsonb_typeof(voice_languages) = 'object'")


def downgrade() -> None:
    configured = op.get_bind().execute(sa.text(
        "SELECT EXISTS (SELECT 1 FROM agency_receptionist_settings "
        "WHERE voice_languages <> '{}'::jsonb AND voice_languages <> "
        "'{\"default_language\":\"en\",\"enabled_languages\":[\"en\"],"
        "\"automatic_switching\":false,\"presets\":{}}'::jsonb)"
    )).scalar_one()
    if configured:
        raise RuntimeError("Restore English-only settings before removing voice language configuration")
    op.drop_constraint(op.f("ck_agency_receptionist_settings_voice_languages_object"), "agency_receptionist_settings", type_="check")
    op.drop_column("agency_receptionist_settings", "voice_languages")
