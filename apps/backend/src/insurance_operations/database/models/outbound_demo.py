from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from insurance_operations.database.models.base import Base, UuidPrimaryKeyMixin


class OutboundDemoCall(UuidPrimaryKeyMixin, Base):
    __tablename__ = "outbound_demo_calls"
    __table_args__ = (
        UniqueConstraint("agency_id", "request_id"),
        CheckConstraint(
            "status IN ('reserved','dialing','in_progress','processing','unknown',"
            "'failed','rejected','unanswered','completed','disconnected')",
            name="status_valid",
        ),
        CheckConstraint(
            (
                "transfer_status IN "
                "('not_requested','refer_accepted','failed','unconf"
                "irmed')"
            ),
            name="transfer_status_valid",
        ),
        Index("ix_outbound_demo_calls_agency_created", "agency_id", "created_at"),
    )

    agency_id: Mapped[UUID] = mapped_column(
        ForeignKey("agencies.id", ondelete="RESTRICT"), nullable=False
    )
    request_id: Mapped[UUID]
    owner_hash: Mapped[str] = mapped_column(Text)
    destination_hash: Mapped[str] = mapped_column(Text)
    request_hash: Mapped[str] = mapped_column(Text)
    scenario: Mapped[str] = mapped_column(Text)
    consent_version: Mapped[str] = mapped_column(Text)
    consent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(Text)
    transfer_status: Mapped[str] = mapped_column(Text, default="not_requested")
    conversation_id: Mapped[str | None] = mapped_column(Text, unique=True)
    sip_call_id: Mapped[str | None] = mapped_column(Text, unique=True)
    last_event_hash: Mapped[str | None] = mapped_column(Text)
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
