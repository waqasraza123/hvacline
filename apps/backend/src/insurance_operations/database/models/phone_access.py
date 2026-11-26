from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from insurance_operations.database.models.base import Base, UuidPrimaryKeyMixin


class CustomerPhoneAccess(UuidPrimaryKeyMixin, Base):
    __tablename__ = "customer_phone_access"
    __table_args__ = (
        ForeignKeyConstraint(
            ["agency_id", "conversation_session_id"],
            ["conversation_sessions.agency_id", "conversation_sessions.id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["agency_id", "account_id"],
            ["customer_accounts.agency_id", "customer_accounts.id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["account_id", "login_session_id"],
            ["customer_login_sessions.account_id", "customer_login_sessions.id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("conversation_session_id", name="uq_customer_phone_access_call"),
        UniqueConstraint("code_digest", name="uq_customer_phone_access_code"),
        CheckConstraint(
            "(approved_at IS NULL AND account_id IS NULL AND login_session_id IS NULL "
            "AND code_digest IS NOT NULL AND share_memory = false "
            "AND memory_revision IS NULL) OR "
            "(approved_at IS NOT NULL AND account_id IS NOT NULL "
            "AND login_session_id IS NOT NULL AND code_digest IS NULL)",
            name="approval_consistent",
        ),
        CheckConstraint(
            "(share_memory = false AND memory_revision IS NULL) OR "
            "(share_memory = true AND memory_revision >= 0 "
            "AND memory_revision IS NOT NULL)",
            name="memory_consistent",
        ),
        CheckConstraint(
            "code_digest IS NULL OR length(code_digest) = 64", name="digest_valid"
        ),
        CheckConstraint("expires_at > created_at", name="expiry_valid"),
        Index("ix_customer_phone_access_account", "agency_id", "account_id"),
    )

    agency_id: Mapped[UUID] = mapped_column(nullable=False)
    conversation_session_id: Mapped[UUID] = mapped_column(nullable=False)
    account_id: Mapped[UUID | None] = mapped_column()
    login_session_id: Mapped[UUID | None] = mapped_column()
    code_digest: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    share_memory: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false", default=False
    )
    memory_revision: Mapped[int | None] = mapped_column(Integer)
