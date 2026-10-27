from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from insurance_operations.database.models.base import Base, UuidPrimaryKeyMixin


class CustomerMfaFactor(Base):
    __tablename__ = "customer_mfa_factors"
    __table_args__ = (
        CheckConstraint("version > 0", name="version_valid"),
        CheckConstraint("last_counter IS NULL OR last_counter >= 0", name="counter_valid"),
        CheckConstraint("failed_attempts BETWEEN 0 AND 5", name="attempts_valid"),
        CheckConstraint(
            "(enabled_at IS NULL AND secret_ciphertext IS NULL AND last_counter IS NULL) OR "
            "(enabled_at IS NOT NULL AND secret_ciphertext IS NOT NULL AND last_counter IS NOT NULL)",
            name="enrollment_consistent",
        ),
    )

    account_id: Mapped[UUID] = mapped_column(
        ForeignKey("customer_accounts.id", ondelete="RESTRICT"), primary_key=True
    )
    agency_id: Mapped[UUID] = mapped_column(
        ForeignKey("agencies.id", ondelete="RESTRICT"), nullable=False
    )
    secret_ciphertext: Mapped[str | None] = mapped_column(Text)
    enabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_counter: Mapped[int | None] = mapped_column(BigInteger)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    failed_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CustomerMfaChallenge(UuidPrimaryKeyMixin, Base):
    __tablename__ = "customer_mfa_challenges"
    __table_args__ = (
        CheckConstraint("purpose IN ('ENROLL', 'VERIFY', 'REPLACE')", name="purpose_valid"),
        CheckConstraint("attempts BETWEEN 0 AND 5", name="attempts_valid"),
        CheckConstraint("factor_version > 0", name="version_valid"),
        CheckConstraint(
            "(purpose = 'VERIFY' AND secret_ciphertext IS NULL) OR "
            "(purpose IN ('ENROLL', 'REPLACE') AND "
            "(secret_ciphertext IS NOT NULL OR consumed_at IS NOT NULL))",
            name="secret_consistent",
        ),
        Index("ix_mfa_challenges_account_expiry", "account_id", "expires_at"),
    )

    account_id: Mapped[UUID] = mapped_column(
        ForeignKey("customer_accounts.id", ondelete="RESTRICT"), nullable=False
    )
    agency_id: Mapped[UUID] = mapped_column(
        ForeignKey("agencies.id", ondelete="RESTRICT"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    secret_ciphertext: Mapped[str | None] = mapped_column(Text)
    factor_version: Mapped[int] = mapped_column(Integer, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CustomerMfaRecoveryCode(UuidPrimaryKeyMixin, Base):
    __tablename__ = "customer_mfa_recovery_codes"
    __table_args__ = (Index("ix_mfa_recovery_account", "account_id"),)

    account_id: Mapped[UUID] = mapped_column(
        ForeignKey("customer_accounts.id", ondelete="RESTRICT"), nullable=False
    )
    agency_id: Mapped[UUID] = mapped_column(
        ForeignKey("agencies.id", ondelete="RESTRICT"), nullable=False
    )
    code_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
