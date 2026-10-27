from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from insurance_operations.database.models.base import Base, UuidPrimaryKeyMixin

FACT_VALUE_CHECK = (
    "(key = 'appointment_time' AND value IN ('MORNING', 'AFTERNOON')) OR "
    "(key = 'appointment_days' AND value IN ('WEEKDAYS', 'WEEKENDS')) OR "
    "(key = 'contact_preference' AND value IN ('PHONE', 'EMAIL')) OR "
    "(key = 'equipment_type' AND value IN "
    "('CENTRAL_AC', 'HEAT_PUMP', 'FURNACE', 'BOILER', 'MINI_SPLIT')) OR "
    "(key = 'equipment_brand' AND value IN ('CARRIER', 'TRANE', 'LENNOX', "
    "'GOODMAN', 'DAIKIN', 'RHEEM', 'MITSUBISHI', 'YORK', 'BRYANT', 'AMANA')) OR "
    "(key = 'equipment_fuel' AND value IN ('ELECTRIC', 'GAS', 'OIL')) OR "
    "(key = 'arrival_preference' AND value = 'CALL_FIRST') OR "
    "(key = 'site_access' AND value IN ('GATE', 'PETS'))"
)


class CustomerMemoryPolicy(Base):
    __tablename__ = "customer_memory_policies"
    __table_args__ = (
        CheckConstraint("revision >= 0", name="revision_valid"),
        CheckConstraint("retention_days BETWEEN 1 AND 365", name="retention_valid"),
    )

    account_id: Mapped[UUID] = mapped_column(
        ForeignKey("customer_accounts.id", ondelete="RESTRICT"), primary_key=True
    )
    agency_id: Mapped[UUID] = mapped_column(
        ForeignKey("agencies.id", ondelete="RESTRICT"), nullable=False
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    retention_days: Mapped[int] = mapped_column(Integer, nullable=False)
    history_after: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_request_id: Mapped[UUID | None]
    last_fingerprint: Mapped[str | None] = mapped_column(Text)


class CustomerMemoryFact(UuidPrimaryKeyMixin, Base):
    __tablename__ = "customer_memory_facts"
    __table_args__ = (
        UniqueConstraint("account_id", "key", name="uq_memory_fact_account_key"),
        CheckConstraint("expires_at > updated_at", name="expiry_valid"),
        CheckConstraint(FACT_VALUE_CHECK, name="value_valid"),
        CheckConstraint(
            "(source_kind = 'CONVERSATION' AND source_intake_id IS NOT NULL) OR "
            "(source_kind = 'CUSTOMER_CONTROL' AND source_intake_id IS NULL)",
            name="source_valid",
        ),
        Index("ix_customer_memory_facts_expires", "expires_at"),
    )

    agency_id: Mapped[UUID] = mapped_column(
        ForeignKey("agencies.id", ondelete="RESTRICT"), nullable=False
    )
    account_id: Mapped[UUID] = mapped_column(
        ForeignKey("customer_accounts.id", ondelete="RESTRICT"), nullable=False
    )
    key: Mapped[str] = mapped_column(Text, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    source_intake_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("conversation_intakes.id", ondelete="RESTRICT")
    )
    source_kind: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CustomerMemorySummary(Base):
    __tablename__ = "customer_memory_summaries"
    __table_args__ = (
        Index("ix_customer_memory_summaries_expires", "expires_at"),
        Index("ix_memory_summaries_account_created", "account_id", "created_at"),
        CheckConstraint("length(summary) BETWEEN 1 AND 240", name="summary_valid"),
    )

    intake_id: Mapped[UUID] = mapped_column(
        ForeignKey("conversation_intakes.id", ondelete="RESTRICT"), primary_key=True
    )
    agency_id: Mapped[UUID] = mapped_column(
        ForeignKey("agencies.id", ondelete="RESTRICT"), nullable=False
    )
    account_id: Mapped[UUID] = mapped_column(
        ForeignKey("customer_accounts.id", ondelete="RESTRICT"), nullable=False
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CustomerWhatsAppIdentity(UuidPrimaryKeyMixin, Base):
    __tablename__ = "customer_whatsapp_identities"
    __table_args__ = (
        UniqueConstraint(
            "agency_id", "phone_number_id", "caller_digest",
            name="uq_customer_whatsapp_identity",
        ),
        CheckConstraint("length(caller_digest) = 64", name="digest_valid"),
        Index("ix_customer_whatsapp_identities_expires", "expires_at"),
        Index("ix_customer_whatsapp_identities_account", "account_id"),
    )

    agency_id: Mapped[UUID] = mapped_column(
        ForeignKey("agencies.id", ondelete="RESTRICT"), nullable=False
    )
    account_id: Mapped[UUID] = mapped_column(
        ForeignKey("customer_accounts.id", ondelete="RESTRICT"), nullable=False
    )
    phone_number_id: Mapped[str] = mapped_column(Text, nullable=False)
    caller_digest: Mapped[str] = mapped_column(Text, nullable=False)
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    mfa_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")


class CustomerMemoryPairing(UuidPrimaryKeyMixin, Base):
    __tablename__ = "customer_memory_pairings"
    __table_args__ = (
        CheckConstraint("length(code_digest) = 64", name="digest_valid"),
        Index("ix_customer_memory_pairings_expires", "expires_at"),
    )

    agency_id: Mapped[UUID] = mapped_column(
        ForeignKey("agencies.id", ondelete="RESTRICT"), nullable=False
    )
    binding_id: Mapped[UUID] = mapped_column(
        ForeignKey("whatsapp_conversations.id", ondelete="RESTRICT"), nullable=False,
        unique=True,
    )
    code_digest: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
