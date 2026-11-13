from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from insurance_operations.database.models.base import Base, UuidPrimaryKeyMixin


class GhlConnection(UuidPrimaryKeyMixin, Base):
    __tablename__ = "ghl_connections"
    __table_args__ = (
        UniqueConstraint("agency_id", "id", name="uq_ghl_connections_agency_id"),
        Index(
            "uq_ghl_connections_active_agency",
            "agency_id",
            unique=True,
            postgresql_where=text("status <> 'DISCONNECTED'"),
        ),
        Index(
            "uq_ghl_connections_active_location",
            "location_id",
            unique=True,
            postgresql_where=text("status <> 'DISCONNECTED'"),
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'PAUSED', 'ERROR', 'DISCONNECTED')",
            name="status_valid",
        ),
        CheckConstraint(
            "(status = 'DISCONNECTED' AND token_ciphertext IS NULL) OR "
            "(status <> 'DISCONNECTED' AND token_ciphertext IS NOT NULL)",
            name="token_state_valid",
        ),
    )

    agency_id: Mapped[UUID] = mapped_column(
        ForeignKey("agencies.id", ondelete="RESTRICT"), nullable=False
    )
    location_id: Mapped[str] = mapped_column(Text, nullable=False)
    pipeline_id: Mapped[str] = mapped_column(Text, nullable=False)
    stages: Mapped[dict[str, str]] = mapped_column(JSONB, nullable=False)
    fields: Mapped[dict[str, str]] = mapped_column(JSONB, nullable=False)
    token_ciphertext: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    activated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    blocked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)


class GhlDelivery(UuidPrimaryKeyMixin, Base):
    __tablename__ = "ghl_deliveries"
    __table_args__ = (
        ForeignKeyConstraint(
            ["agency_id", "connection_id"],
            ["ghl_connections.agency_id", "ghl_connections.id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["agency_id", "lead_id"],
            ["agency_leads.agency_id", "agency_leads.id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("connection_id", "lead_id", name="uq_ghl_deliveries_lead"),
        UniqueConstraint(
            "connection_id", "opportunity_id", name="uq_ghl_deliveries_opportunity"
        ),
        CheckConstraint(
            "status IN ('PENDING', 'PROCESSING', 'SYNCED', 'RETRYING', 'NEEDS_REVIEW')",
            name="status_valid",
        ),
        CheckConstraint(
            "desired_version > 0 AND delivered_version >= 0 "
            "AND delivered_version <= desired_version AND attempts >= 0",
            name="progress_valid",
        ),
        Index("ix_ghl_deliveries_due", "status", "next_attempt_at"),
        Index("ix_ghl_deliveries_agency_created", "agency_id", "created_at"),
    )

    agency_id: Mapped[UUID] = mapped_column(
        ForeignKey("agencies.id", ondelete="RESTRICT"), nullable=False
    )
    connection_id: Mapped[UUID] = mapped_column(nullable=False)
    lead_id: Mapped[UUID] = mapped_column(nullable=False)
    desired_version: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default="1"
    )
    delivered_version: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default="0"
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="PENDING")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    contact_id: Mapped[str | None] = mapped_column(Text)
    opportunity_id: Mapped[str | None] = mapped_column(Text)
    contact_unknown: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    opportunity_unknown: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    last_stage_id: Mapped[str | None] = mapped_column(Text)
    pending_stage_id: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("clock_timestamp()"),
    )
    next_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("clock_timestamp()"),
    )
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
