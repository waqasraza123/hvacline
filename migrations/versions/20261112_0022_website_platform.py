"""Agency-owned websites and immutable conversation routing context."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "20261112_0022"
down_revision = "20261109_0021"
branch_labels = None
depends_on = None


def base_columns() -> list[sa.Column]:
    return [
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
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("row_version", sa.BigInteger(), nullable=False, server_default="1"),
    ]


def upgrade() -> None:
    op.create_table(
        "website_agent_bindings",
        *base_columns(),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("provider_agent_id", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "browser_tools_confirmed",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.UniqueConstraint(
            "id", "agency_id", name="uq_website_agent_bindings_id_agency"
        ),
        sa.UniqueConstraint(
            "provider_agent_id", name="uq_website_agent_bindings_provider_agent"
        ),
        sa.CheckConstraint(
            "length(btrim(label)) BETWEEN 1 AND 100", name="label_valid"
        ),
        sa.CheckConstraint(
            "length(btrim(provider_agent_id)) BETWEEN 1 AND 200",
            name="provider_agent_valid",
        ),
    )
    op.create_table(
        "websites",
        *base_columns(),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("template_id", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="draft"),
        sa.Column("configuration", JSONB(), nullable=False),
        sa.Column("agent_binding_id", sa.Uuid(), nullable=True),
        sa.Column(
            "knowledge_faq_ids",
            JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "voice_enabled", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column(
            "lead_capture_enabled", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.UniqueConstraint("slug", name="uq_websites_slug"),
        sa.UniqueConstraint("id", "agency_id", name="uq_websites_id_agency"),
        sa.ForeignKeyConstraint(
            ["agent_binding_id", "agency_id"],
            ["website_agent_bindings.id", "website_agent_bindings.agency_id"],
            name="fk_websites_owned_agent",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'published', 'disabled')", name="status_valid"
        ),
        sa.CheckConstraint(
            "slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$' AND length(slug) <= 64",
            name="slug_valid",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(configuration) = 'object'", name="configuration_object"
        ),
        sa.CheckConstraint(
            "jsonb_typeof(knowledge_faq_ids) = 'array'", name="knowledge_array"
        ),
        sa.CheckConstraint("row_version > 0", name="row_version_positive"),
    )
    op.add_column(
        "conversation_sessions", sa.Column("website_id", sa.Uuid(), nullable=True)
    )
    op.add_column(
        "conversation_sessions",
        sa.Column("website_agent_binding_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "conversation_sessions",
        sa.Column(
            "website_capabilities",
            JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.create_foreign_key(
        "fk_conversation_sessions_owned_website",
        "conversation_sessions",
        "websites",
        ["website_id", "agency_id"],
        ["id", "agency_id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_conversation_sessions_owned_website_agent",
        "conversation_sessions",
        "website_agent_bindings",
        ["website_agent_binding_id", "agency_id"],
        ["id", "agency_id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "website_binding_consistent",
        "conversation_sessions",
        "(website_id IS NULL AND website_agent_binding_id IS NULL) OR "
        "(website_id IS NOT NULL AND website_agent_binding_id IS NOT NULL)",
    )
    op.create_check_constraint(
        "website_capabilities_object",
        "conversation_sessions",
        "jsonb_typeof(website_capabilities) = 'object'",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck_conversation_sessions_website_capabilities_object"),
        "conversation_sessions",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_conversation_sessions_website_binding_consistent"),
        "conversation_sessions",
        type_="check",
    )
    op.drop_constraint(
        "fk_conversation_sessions_owned_website_agent",
        "conversation_sessions",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_conversation_sessions_owned_website",
        "conversation_sessions",
        type_="foreignkey",
    )
    for name in ("website_capabilities", "website_agent_binding_id", "website_id"):
        op.drop_column("conversation_sessions", name)
    op.drop_table("websites")
    op.drop_table("website_agent_bindings")
