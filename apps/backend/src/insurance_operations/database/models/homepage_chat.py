from datetime import date, datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from insurance_operations.database.models.base import Base


class HomepageChatVisitor(Base):
    __tablename__ = "homepage_chat_visitors"
    __table_args__ = (
        CheckConstraint("state IN ('READY', 'PROCESSING', 'USED')", name="state_valid"),
        Index("ix_homepage_chat_visitors_expiry", "expires_at"),
    )

    agency_id: Mapped[UUID] = mapped_column(
        ForeignKey("agencies.id", ondelete="RESTRICT"), primary_key=True
    )
    token_hash: Mapped[str] = mapped_column(Text, primary_key=True)
    state: Mapped[str] = mapped_column(Text, nullable=False)
    request_id: Mapped[UUID | None]
    request_hash: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class HomepageChatDailyUsage(Base):
    __tablename__ = "homepage_chat_daily_usage"
    __table_args__ = (CheckConstraint("generations >= 0", name="generations_valid"),)

    agency_id: Mapped[UUID] = mapped_column(
        ForeignKey("agencies.id", ondelete="RESTRICT"), primary_key=True
    )
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    generations: Mapped[int] = mapped_column(Integer, nullable=False)
