"""Immutable website publications with independent drafts."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "20261113_0023"
down_revision = "20261112_0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "website_versions",
        sa.Column(
            "id",
            sa.Uuid(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("website_id", sa.Uuid(), nullable=False),
        sa.Column(
            "agency_id",
            sa.Uuid(),
            sa.ForeignKey("agencies.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("configuration", JSONB(), nullable=False),
        sa.Column("agent_binding_id", sa.Uuid(), nullable=True),
        sa.Column("knowledge_faq_ids", JSONB(), nullable=False),
        sa.Column("voice_enabled", sa.Boolean(), nullable=False),
        sa.Column("lead_capture_enabled", sa.Boolean(), nullable=False),
        sa.Column(
            "created_by",
            sa.Uuid(),
            sa.ForeignKey("app_users.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["website_id", "agency_id"],
            ["websites.id", "websites.agency_id"],
            name="fk_website_versions_owned_website",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["agent_binding_id", "agency_id"],
            ["website_agent_bindings.id", "website_agent_bindings.agency_id"],
            name="fk_website_versions_owned_agent",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "id", "website_id", "agency_id", name="uq_website_versions_owned_id"
        ),
        sa.UniqueConstraint("website_id", "number", name="uq_website_versions_number"),
        sa.CheckConstraint("number > 0", name="number_positive"),
        sa.CheckConstraint(
            "jsonb_typeof(configuration) = 'object'", name="configuration_object"
        ),
        sa.CheckConstraint(
            "jsonb_typeof(knowledge_faq_ids) = 'array'", name="knowledge_array"
        ),
    )
    op.add_column(
        "websites", sa.Column("published_version_id", sa.Uuid(), nullable=True)
    )
    op.add_column(
        "conversation_sessions",
        sa.Column("website_version_id", sa.Uuid(), nullable=True),
    )
    op.execute("""
        INSERT INTO website_versions
          (website_id, agency_id, number, configuration, agent_binding_id,
           knowledge_faq_ids, voice_enabled, lead_capture_enabled)
        SELECT id, agency_id, 1, configuration, agent_binding_id,
               knowledge_faq_ids, voice_enabled, lead_capture_enabled FROM websites
    """)
    op.execute("""
        UPDATE websites w SET published_version_id = v.id
        FROM website_versions v WHERE v.website_id = w.id AND w.status = 'published'
    """)
    op.execute("""
        UPDATE conversation_sessions c SET website_version_id = v.id
        FROM website_versions v WHERE v.website_id = c.website_id
    """)
    op.create_foreign_key(
        "fk_websites_published_version",
        "websites",
        "website_versions",
        ["published_version_id", "id", "agency_id"],
        ["id", "website_id", "agency_id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_conversation_sessions_owned_website_version",
        "conversation_sessions",
        "website_versions",
        ["website_version_id", "website_id", "agency_id"],
        ["id", "website_id", "agency_id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint(
        op.f("ck_conversation_sessions_website_binding_consistent"),
        "conversation_sessions",
        type_="check",
    )
    op.create_check_constraint(
        "website_binding_consistent",
        "conversation_sessions",
        (
            "(website_id IS NULL AND website_agent_binding_id "
            "IS NULL AND website_version_id IS NULL) OR "
            "(website_id IS NOT NULL AND "
            "website_agent_binding_id IS NOT NULL AND "
            "website_version_id IS NOT NULL)"
        ),
    )
    op.execute("""
        CREATE FUNCTION protect_website_version() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN RAISE EXCEPTION 'Published website versions are immutable'; END;
        $$
    """)
    op.execute("""
        CREATE TRIGGER website_versions_immutable BEFORE UPDATE OR DELETE
        ON website_versions FOR EACH ROW EXECUTE FUNCTION protect_website_version()
    """)


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck_conversation_sessions_website_binding_consistent"),
        "conversation_sessions",
        type_="check",
    )
    op.create_check_constraint(
        "website_binding_consistent",
        "conversation_sessions",
        (
            "(website_id IS NULL AND website_agent_binding_id "
            "IS NULL) OR (website_id IS NOT NULL AND "
            "website_agent_binding_id IS NOT NULL)"
        ),
    )
    op.drop_constraint(
        "fk_conversation_sessions_owned_website_version",
        "conversation_sessions",
        type_="foreignkey",
    )
    op.drop_constraint("fk_websites_published_version", "websites", type_="foreignkey")
    op.drop_column("conversation_sessions", "website_version_id")
    op.drop_column("websites", "published_version_id")
    op.drop_table("website_versions")
    op.execute("DROP FUNCTION protect_website_version()")
