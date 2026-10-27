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


class CalendarConnection(UuidPrimaryKeyMixin, Base):
    __tablename__ = "calendar_connections"
    __table_args__ = (
        UniqueConstraint("agency_id", "id", name="uq_calendar_connections_agency_id"),
        UniqueConstraint("agency_id", "team_key", name="uq_calendar_connections_team"),
        UniqueConstraint(
            "agency_id", "calendar_id", name="uq_calendar_connections_calendar"
        ),
        CheckConstraint(
            "status IN ('CONNECTED', 'REAUTH_REQUIRED', 'DISCONNECTED')",
            name="status_valid",
        ),
    )

    agency_id: Mapped[UUID] = mapped_column(
        ForeignKey("agencies.id", ondelete="RESTRICT"), nullable=False
    )
    team_key: Mapped[str] = mapped_column(Text, nullable=False)
    calendar_id: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token_ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)


class CalendarAuthorization(UuidPrimaryKeyMixin, Base):
    __tablename__ = "calendar_authorizations"

    agency_id: Mapped[UUID] = mapped_column(
        ForeignKey("agencies.id", ondelete="RESTRICT"), nullable=False
    )
    actor_id: Mapped[UUID] = mapped_column(
        ForeignKey("app_users.id", ondelete="RESTRICT"), nullable=False
    )
    state_digest: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    browser_digest: Mapped[str] = mapped_column(Text, nullable=False)
    verifier_ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    team_key: Mapped[str] = mapped_column(Text, nullable=False)
    calendar_id: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class CalendarBooking(Base):
    __tablename__ = "calendar_bookings"
    __table_args__ = (
        ForeignKeyConstraint(
            ["agency_id", "appointment_id"],
            ["hvac_appointments.agency_id", "hvac_appointments.id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["agency_id", "connection_id"],
            ["calendar_connections.agency_id", "calendar_connections.id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "status IN ('PENDING', 'SYNCED', 'ATTENTION', 'CANCELLED', 'COMPLETED')",
            name="status_valid",
        ),
    )

    appointment_id: Mapped[UUID] = mapped_column(primary_key=True)
    agency_id: Mapped[UUID] = mapped_column(
        ForeignKey("agencies.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    connection_id: Mapped[UUID] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    next_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    last_error: Mapped[str | None] = mapped_column(Text)


class BookingNotification(UuidPrimaryKeyMixin, Base):
    __tablename__ = "booking_notifications"
    __table_args__ = (
        ForeignKeyConstraint(
            ["agency_id", "appointment_id"],
            ["hvac_appointments.agency_id", "hvac_appointments.id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "appointment_id", "kind", name="uq_booking_notifications_kind"
        ),
        CheckConstraint(
            "kind IN ('CONFIRMATION', 'REMINDER', 'CANCELLATION', 'RESCHEDULED')",
            name="kind_valid",
        ),
        CheckConstraint(
            "status IN ('PENDING', 'ACCEPTED', 'SKIPPED', 'FAILED', 'UNKNOWN')",
            name="status_valid",
        ),
        CheckConstraint("attempts >= 0", name="attempts_valid"),
    )

    agency_id: Mapped[UUID] = mapped_column(
        ForeignKey("agencies.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    appointment_id: Mapped[UUID] = mapped_column(nullable=False)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    due_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    first_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    provider_reference: Mapped[str | None] = mapped_column(Text)
    last_error: Mapped[str | None] = mapped_column(Text)
    delivery_status: Mapped[str | None] = mapped_column(Text)


class BookingEmailEvent(Base):
    __tablename__ = "booking_email_events"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    provider_reference: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
