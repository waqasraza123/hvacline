from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column

from insurance_operations.database.models.base import Base, UuidPrimaryKeyMixin


class WhatsAppConversation(UuidPrimaryKeyMixin, Base):
    __tablename__ = "whatsapp_conversations"
    __table_args__ = (
        CheckConstraint("length(caller_digest) = 64", name="caller_digest_valid"),
        CheckConstraint("expires_at > initialized_at", name="expiry_valid"),
        Index(
            "ix_whatsapp_conversations_agency_initialized",
            "agency_id",
            "initialized_at",
        ),
    )

    agency_id: Mapped[UUID] = mapped_column(
        ForeignKey("agencies.id", ondelete="RESTRICT"), nullable=False
    )
    conversation_id: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    phone_number_id: Mapped[str] = mapped_column(Text, nullable=False)
    caller_digest: Mapped[str] = mapped_column(Text, nullable=False)
    session_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("conversation_sessions.id", ondelete="RESTRICT"), unique=True
    )
    initialized_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    customer_account_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("customer_accounts.id", ondelete="RESTRICT")
    )
