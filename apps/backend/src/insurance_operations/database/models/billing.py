from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from insurance_operations.database.models.base import Base


class BillingAccount(Base):
    __tablename__ = "billing_accounts"
    __table_args__ = (
        CheckConstraint(
            "plan IN ('none','essential','comfort','complete')", name="plan_valid"
        ),
        CheckConstraint("livemode = false", name="test_mode_only"),
        UniqueConstraint(
            "agency_id", "account_id", name="uq_billing_accounts_agency_account"
        ),
        ForeignKeyConstraint(
            ["agency_id", "account_id"],
            ["customer_accounts.agency_id", "customer_accounts.id"],
            ondelete="RESTRICT",
        ),
    )

    account_id: Mapped[UUID] = mapped_column(
        ForeignKey("customer_accounts.id", ondelete="RESTRICT"), primary_key=True
    )
    agency_id: Mapped[UUID] = mapped_column(
        ForeignKey("agencies.id", ondelete="RESTRICT"), nullable=False
    )
    review_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    customer_id: Mapped[str | None] = mapped_column(Text, unique=True)
    customer_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    livemode: Mapped[bool] = mapped_column(Boolean, nullable=False)
    subscription_id: Mapped[str | None] = mapped_column(Text, unique=True)
    price_id: Mapped[str | None] = mapped_column(Text)
    plan: Mapped[str] = mapped_column(Text, nullable=False, default="none")
    status: Mapped[str] = mapped_column(Text, nullable=False, default="none")
    period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    paid_through: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancel_at_period_end: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class BillingCheckout(Base):
    __tablename__ = "billing_checkouts"
    __table_args__ = (
        ForeignKeyConstraint(
            ["agency_id", "account_id"],
            ["billing_accounts.agency_id", "billing_accounts.account_id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "plan IN ('essential','comfort','complete')", name="plan_valid"
        ),
        CheckConstraint(
            "status IN ('creating','open','complete','expired')", name="status_valid"
        ),
        Index("ix_billing_checkouts_account_created", "account_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    account_id: Mapped[UUID] = mapped_column(
        ForeignKey("customer_accounts.id", ondelete="RESTRICT"), nullable=False
    )
    agency_id: Mapped[UUID] = mapped_column(
        ForeignKey("agencies.id", ondelete="RESTRICT"), nullable=False
    )
    plan: Mapped[str] = mapped_column(Text, nullable=False)
    session_id: Mapped[str | None] = mapped_column(Text, unique=True)
    url: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(Text, nullable=False, default="creating")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class BillingEvent(Base):
    __tablename__ = "billing_events"
    __table_args__ = (
        Index("ix_billing_events_pending", "account_id", "processed_at"),
        ForeignKeyConstraint(
            ["agency_id", "account_id"],
            ["billing_accounts.agency_id", "billing_accounts.account_id"],
            ondelete="RESTRICT",
        ),
    )

    event_id: Mapped[str] = mapped_column(Text, primary_key=True)
    account_id: Mapped[UUID] = mapped_column(
        ForeignKey("customer_accounts.id", ondelete="RESTRICT"), nullable=False
    )
    agency_id: Mapped[UUID] = mapped_column(
        ForeignKey("agencies.id", ondelete="RESTRICT"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    customer_id: Mapped[str] = mapped_column(Text, nullable=False)
    object_id: Mapped[str] = mapped_column(Text, nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class BillingTopUp(Base):
    __tablename__ = "billing_topups"
    __table_args__ = (
        ForeignKeyConstraint(
            ["agency_id", "account_id"],
            ["billing_accounts.agency_id", "billing_accounts.account_id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "plan IN ('essential','comfort','complete')", name="plan_valid"
        ),
        CheckConstraint(
            "minutes BETWEEN 60 AND 2400 AND minutes % 60 = 0", name="minutes_valid"
        ),
        CheckConstraint(
            "hourly_amount > 0 AND amount = minutes / 60 * hourly_amount",
            name="amount_valid",
        ),
        CheckConstraint(
            "status IN ('creating','open','paid','expired')", name="status_valid"
        ),
        CheckConstraint(
            "(status = 'paid') = (credited_at IS NOT NULL)", name="credit_consistent"
        ),
        Index("ix_billing_topups_account_created", "account_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    account_id: Mapped[UUID] = mapped_column(
        ForeignKey("customer_accounts.id", ondelete="RESTRICT"), nullable=False
    )
    agency_id: Mapped[UUID] = mapped_column(
        ForeignKey("agencies.id", ondelete="RESTRICT"), nullable=False
    )
    subscription_id: Mapped[str] = mapped_column(Text, nullable=False)
    plan: Mapped[str] = mapped_column(Text, nullable=False)
    minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    hourly_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    session_id: Mapped[str | None] = mapped_column(Text, unique=True)
    url: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    credited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class BillingLabor(Base):
    __tablename__ = "billing_labor"
    __table_args__ = (
        ForeignKeyConstraint(
            ["agency_id", "account_id"],
            ["billing_accounts.agency_id", "billing_accounts.account_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["agency_id", "appointment_id"],
            ["hvac_appointments.agency_id", "hvac_appointments.id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            (
                "minutes BETWEEN 1 AND 1440 AND package_minutes >= "
                "0 AND purchased_minutes >= 0 AND minutes = "
                "package_minutes + purchased_minutes"
            ),
            name="minutes_valid",
        ),
        CheckConstraint(
            "package_minutes = 0 OR period_start IS NOT NULL", name="period_required"
        ),
        Index("ix_billing_labor_account_period", "account_id", "period_start"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    account_id: Mapped[UUID] = mapped_column(
        ForeignKey("customer_accounts.id", ondelete="RESTRICT"), nullable=False
    )
    agency_id: Mapped[UUID] = mapped_column(
        ForeignKey("agencies.id", ondelete="RESTRICT"), nullable=False
    )
    appointment_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), unique=True, nullable=False
    )
    minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    package_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    purchased_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    subscription_id: Mapped[str | None] = mapped_column(Text)
    period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
