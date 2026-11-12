from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from insurance_operations.database.models.base import (
    Base,
    TimestampedMixin,
    UuidPrimaryKeyMixin,
    VersionedMixin,
)


class WebsiteAgentBinding(UuidPrimaryKeyMixin, TimestampedMixin, VersionedMixin, Base):
    __tablename__ = "website_agent_bindings"
    __table_args__ = (
        UniqueConstraint("id", "agency_id", name="uq_website_agent_bindings_id_agency"),
        UniqueConstraint(
            "provider_agent_id", name="uq_website_agent_bindings_provider_agent"
        ),
        CheckConstraint("length(btrim(label)) BETWEEN 1 AND 100", name="label_valid"),
        CheckConstraint(
            "length(btrim(provider_agent_id)) BETWEEN 1 AND 200",
            name="provider_agent_valid",
        ),
    )
    agency_id: Mapped[UUID] = mapped_column(
        ForeignKey("agencies.id", ondelete="RESTRICT")
    )
    label: Mapped[str] = mapped_column(Text)
    provider_agent_id: Mapped[str] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    browser_tools_confirmed: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )


class Website(UuidPrimaryKeyMixin, TimestampedMixin, VersionedMixin, Base):
    __tablename__ = "websites"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_websites_slug"),
        UniqueConstraint("id", "agency_id", name="uq_websites_id_agency"),
        ForeignKeyConstraint(
            ["agent_binding_id", "agency_id"],
            ["website_agent_bindings.id", "website_agent_bindings.agency_id"],
            name="fk_websites_owned_agent",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "status IN ('draft', 'published', 'disabled')", name="status_valid"
        ),
        CheckConstraint(
            "slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$' AND length(slug) <= 64",
            name="slug_valid",
        ),
        CheckConstraint(
            "jsonb_typeof(configuration) = 'object'", name="configuration_object"
        ),
        CheckConstraint(
            "jsonb_typeof(knowledge_faq_ids) = 'array'", name="knowledge_array"
        ),
        CheckConstraint("row_version > 0", name="row_version_positive"),
    )
    agency_id: Mapped[UUID] = mapped_column(
        ForeignKey("agencies.id", ondelete="RESTRICT")
    )
    slug: Mapped[str] = mapped_column(Text)
    template_id: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, default="draft", server_default="draft")
    configuration: Mapped[dict[str, object]] = mapped_column(JSONB)
    agent_binding_id: Mapped[UUID | None] = mapped_column(nullable=True)
    knowledge_faq_ids: Mapped[list[str]] = mapped_column(
        JSONB, default=list, server_default=text("'[]'::jsonb")
    )
    voice_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    lead_capture_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
