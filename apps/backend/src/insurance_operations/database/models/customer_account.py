from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from insurance_operations.database.models.base import Base, UuidPrimaryKeyMixin


class CustomerAccount(UuidPrimaryKeyMixin, Base):
    __tablename__ = "customer_accounts"
    __table_args__ = (UniqueConstraint("agency_id", "email", name="uq_customer_accounts_email"),)

    agency_id: Mapped[UUID] = mapped_column(ForeignKey("agencies.id", ondelete="RESTRICT"), nullable=False)
    app_user_id: Mapped[UUID] = mapped_column(ForeignKey("app_users.id", ondelete="RESTRICT"), nullable=False, unique=True)
    email: Mapped[str] = mapped_column(Text, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CustomerLoginSession(UuidPrimaryKeyMixin, Base):
    __tablename__ = "customer_login_sessions"
    __table_args__ = (CheckConstraint(
        "(mfa_verified_at IS NULL AND mfa_version IS NULL) OR "
        "(mfa_verified_at IS NOT NULL AND mfa_version IS NOT NULL AND mfa_version > 0)",
        name="mfa_consistent",
    ),)

    account_id: Mapped[UUID] = mapped_column(ForeignKey("customer_accounts.id", ondelete="RESTRICT"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    mfa_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    mfa_version: Mapped[int | None] = mapped_column(Integer)


class CustomerAuthLimit(Base):
    __tablename__ = "customer_auth_limits"

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    window_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
