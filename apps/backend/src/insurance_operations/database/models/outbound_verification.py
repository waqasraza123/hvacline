from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column

from insurance_operations.database.models.base import Base, UuidPrimaryKeyMixin


class OutboundPhoneVerification(UuidPrimaryKeyMixin, Base):
    __tablename__ = "outbound_phone_verifications"
    __table_args__ = (
        CheckConstraint("attempts BETWEEN 0 AND 5", name="attempts_valid"),
        Index("ix_outbound_phone_verifications_created", "agency_id", "created_at"),
    )

    agency_id: Mapped[UUID] = mapped_column(
        ForeignKey("agencies.id", ondelete="RESTRICT"), nullable=False
    )
    owner_hash: Mapped[str] = mapped_column(Text)
    destination_hash: Mapped[str] = mapped_column(Text)
    consent_version: Mapped[str] = mapped_column(Text)
    provider_verification_id: Mapped[str | None] = mapped_column(Text, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(default=0)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consumed_by_request_id: Mapped[UUID | None]
