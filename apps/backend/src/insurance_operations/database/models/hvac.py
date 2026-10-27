from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from insurance_operations.database.models.base import Base, UuidPrimaryKeyMixin


class BusinessSchedule(Base):
    __tablename__ = "business_schedules"

    agency_id: Mapped[UUID] = mapped_column(
        ForeignKey("agencies.id", ondelete="RESTRICT"), primary_key=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    configuration: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)


class HvacServiceRequest(UuidPrimaryKeyMixin, Base):
    __tablename__ = "hvac_service_requests"
    __table_args__ = (
        UniqueConstraint("agency_id", "id", name="uq_hvac_requests_agency_id"),
        UniqueConstraint("inbound_call_id", name="uq_hvac_requests_call"),
        UniqueConstraint(
            "conversation_session_id", name="uq_hvac_requests_conversation"
        ),
        CheckConstraint(
            "status IN ('OPEN', 'BOOKED', 'CALLBACK_REQUESTED', "
            "'HANDOFF_REQUESTED', 'CLOSED')",
            name="status_valid",
        ),
    )

    agency_id: Mapped[UUID] = mapped_column(
        ForeignKey("agencies.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    inbound_call_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("inbound_calls.id", ondelete="RESTRICT")
    )
    customer_details: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    conversation_session_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "conversation_sessions.id",
            name="fk_hvac_requests_browser_session",
            ondelete="RESTRICT",
        )
    )
    service_details: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="OPEN")
    fingerprint: Mapped[str] = mapped_column(Text, nullable=False)
    confirmed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class Appointment(UuidPrimaryKeyMixin, Base):
    __tablename__ = "hvac_appointments"
    __table_args__ = (
        UniqueConstraint("agency_id", "id", name="uq_hvac_appointments_agency_id"),
        ForeignKeyConstraint(
            ["agency_id", "service_request_id"],
            ["hvac_service_requests.agency_id", "hvac_service_requests.id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "agency_id", "idempotency_key", name="uq_hvac_appointments_idempotency"
        ),
        CheckConstraint("ends_at > starts_at", name="time_order_valid"),
        CheckConstraint(
            "status IN ('HELD', 'CONFIRMED', 'CANCELLED', 'EXPIRED')",
            name="status_valid",
        ),
    )

    agency_id: Mapped[UUID] = mapped_column(
        ForeignKey("agencies.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    service_request_id: Mapped[UUID] = mapped_column(nullable=False)
    team_key: Mapped[str] = mapped_column(Text, nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    hold_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    idempotency_key: Mapped[str] = mapped_column(Text, nullable=False)
    fingerprint: Mapped[str] = mapped_column(Text, nullable=False)
