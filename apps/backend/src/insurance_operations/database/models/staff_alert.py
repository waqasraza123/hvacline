from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Integer, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from insurance_operations.database.models.base import Base, TimestampedMixin, UuidPrimaryKeyMixin, VersionedMixin


class StaffAlertPolicy(TimestampedMixin, VersionedMixin, Base):
    __tablename__ = "staff_alert_policies"
    __table_args__ = (
        CheckConstraint("row_version > 0", name="version_positive"),
        CheckConstraint("jsonb_typeof(recipients) = 'array' AND jsonb_array_length(recipients) <= 5", name="recipients_valid"),
        CheckConstraint("NOT enabled OR (sender IS NOT NULL AND jsonb_array_length(recipients) > 0)", name="enabled_valid"),
    )
    agency_id: Mapped[UUID] = mapped_column(ForeignKey("agencies.id", ondelete="RESTRICT"), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    recipients: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default="[]")
    sender: Mapped[str | None] = mapped_column(Text)


class StaffAlert(UuidPrimaryKeyMixin, Base):
    __tablename__ = "staff_alerts"
    __table_args__ = (
        UniqueConstraint("agency_id", "event_type", "source_id", "recipient", name="uq_staff_alert_source_recipient"),
        CheckConstraint("event_type IN ('HANDOFF', 'URGENT_SERVICE')", name="event_type_valid"),
        CheckConstraint("status IN ('PENDING', 'ACCEPTED', 'SKIPPED', 'FAILED', 'UNKNOWN')", name="status_valid"),
        CheckConstraint("attempts >= 0", name="attempts_valid"),
        CheckConstraint("policy_version > 0", name="policy_version_positive"),
    )
    agency_id: Mapped[UUID] = mapped_column(ForeignKey("agencies.id", ondelete="RESTRICT"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    source_id: Mapped[UUID] = mapped_column(nullable=False)
    recipient: Mapped[str] = mapped_column(Text, nullable=False)
    policy_version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="PENDING")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True, server_default=func.now())
    first_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    provider_reference: Mapped[str | None] = mapped_column(Text)
    last_error: Mapped[str | None] = mapped_column(Text)
    delivery_status: Mapped[str | None] = mapped_column(Text)
