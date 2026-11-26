from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Integer, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from insurance_operations.database.models.base import Base, TimestampedMixin, UuidPrimaryKeyMixin, VersionedMixin


class WorkspaceBusiness(Base):
    __tablename__ = "workspace_businesses"
    agency_id: Mapped[UUID] = mapped_column(ForeignKey("agencies.id", ondelete="RESTRICT"), primary_key=True)
    creation_key: Mapped[UUID] = mapped_column(unique=True, nullable=False)
    fingerprint: Mapped[str] = mapped_column(Text, nullable=False)
    owner_email: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class WorkspaceCredential(Base):
    __tablename__ = "workspace_credentials"
    __table_args__ = (CheckConstraint("last_totp_counter >= 0", name="counter_valid"),)
    app_user_id: Mapped[UUID] = mapped_column(ForeignKey("app_users.id", ondelete="RESTRICT"), primary_key=True)
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    secret_ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    last_totp_counter: Mapped[int] = mapped_column(BigInteger, nullable=False)


class WorkspaceSession(Base):
    __tablename__ = "workspace_sessions"
    token_digest: Mapped[str] = mapped_column(Text, primary_key=True)
    app_user_id: Mapped[UUID] = mapped_column(ForeignKey("app_users.id", ondelete="RESTRICT"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class WorkspaceInvitation(UuidPrimaryKeyMixin, TimestampedMixin, VersionedMixin, Base):
    __tablename__ = "workspace_invitations"
    __table_args__ = (
        CheckConstraint("role IN ('OWNER', 'ADMIN', 'STAFF')", name="role_valid"),
        CheckConstraint("failed_attempts BETWEEN 0 AND 5", name="attempts_valid"),
        CheckConstraint("row_version > 0", name="version_positive"),
        UniqueConstraint("agency_id", "id", name="uq_workspace_invitations_owned"),
        ForeignKeyConstraint(["agency_id", "created_by"], ["agency_memberships.agency_id", "agency_memberships.app_user_id"], ondelete="RESTRICT"),
    )
    agency_id: Mapped[UUID] = mapped_column(ForeignKey("agencies.id", ondelete="RESTRICT"), nullable=False, index=True)
    email: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[UUID | None] = mapped_column(nullable=True)
    token_digest: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pending_name: Mapped[str | None] = mapped_column(Text)
    pending_password_hash: Mapped[str | None] = mapped_column(Text)
    pending_secret_ciphertext: Mapped[str | None] = mapped_column(Text)
    failed_attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")


class WorkspaceLoginLimit(Base):
    __tablename__ = "workspace_login_limits"
    __table_args__ = (CheckConstraint("attempts >= 0", name="attempts_valid"),)
    key: Mapped[str] = mapped_column(Text, primary_key=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
