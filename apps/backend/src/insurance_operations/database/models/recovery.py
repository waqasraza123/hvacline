from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Index, Integer, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from insurance_operations.database.models.base import Base, TimestampedMixin, UuidPrimaryKeyMixin, VersionedMixin


class RecoveryPolicy(TimestampedMixin, VersionedMixin, Base):
    __tablename__ = "lead_recovery_policies"
    __table_args__ = (CheckConstraint("row_version > 0", name="version_positive"),)
    agency_id: Mapped[UUID] = mapped_column(ForeignKey("agencies.id", ondelete="RESTRICT"), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    configuration: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    capture_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class RecoveryCase(UuidPrimaryKeyMixin, TimestampedMixin, VersionedMixin, Base):
    __tablename__ = "lead_recovery_cases"
    __table_args__ = (
        UniqueConstraint("agency_id", "id", name="uq_recovery_cases_owned"),
        UniqueConstraint("agency_id", "service_request_id", name="uq_recovery_cases_request"),
        UniqueConstraint("agency_id", "source_type", "source_reference", name="uq_recovery_cases_source"),
        ForeignKeyConstraint(["agency_id", "service_request_id"], ["hvac_service_requests.agency_id", "hvac_service_requests.id"], ondelete="RESTRICT"),
        ForeignKeyConstraint(["agency_id", "lead_id"], ["agency_leads.agency_id", "agency_leads.id"], ondelete="RESTRICT"),
        ForeignKeyConstraint(["agency_id", "recovered_appointment_id"], ["hvac_appointments.agency_id", "hvac_appointments.id"], ondelete="RESTRICT"),
        ForeignKeyConstraint(["agency_id", "assigned_to"], ["agency_memberships.agency_id", "agency_memberships.app_user_id"], ondelete="RESTRICT"),
        CheckConstraint("status IN ('PENDING','READY','SCHEDULED','IN_PROGRESS','AWAITING_RESPONSE','RECOVERED','NEEDS_REVIEW','SUPPRESSED','CLOSED')", name="status_valid"),
        CheckConstraint("source_type IN ('MISSED_CALL','ABANDONED_CONVERSATION','UNCONFIRMED_BOOKING')", name="source_valid"),
        CheckConstraint("status <> 'RECOVERED' OR recovered_appointment_id IS NOT NULL", name="recovered_valid"),
        CheckConstraint("row_version > 0", name="version_positive"),
        Index("ix_recovery_cases_due", "status", "eligible_at"),
        Index("ix_recovery_cases_agency_activity", "agency_id", "last_activity_at"),
    )
    agency_id: Mapped[UUID] = mapped_column(ForeignKey("agencies.id", ondelete="RESTRICT"), nullable=False)
    service_request_id: Mapped[UUID] = mapped_column(nullable=False)
    lead_id: Mapped[UUID | None] = mapped_column(nullable=True)
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    source_reference: Mapped[UUID] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="PENDING", server_default="PENDING")
    eligible_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recovered_appointment_id: Mapped[UUID | None] = mapped_column(nullable=True)
    paused: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    assigned_to: Mapped[UUID | None] = mapped_column(ForeignKey("app_users.id", ondelete="RESTRICT"))
    reason: Mapped[str | None] = mapped_column(Text)


class RecoveryAttempt(UuidPrimaryKeyMixin, TimestampedMixin, Base):
    __tablename__ = "lead_recovery_attempts"
    __table_args__ = (
        UniqueConstraint("agency_id", "id", name="uq_recovery_attempt_owned"),
        ForeignKeyConstraint(["agency_id", "recovery_case_id"], ["lead_recovery_cases.agency_id", "lead_recovery_cases.id"], ondelete="RESTRICT"),
        UniqueConstraint("recovery_case_id", "attempt_number", name="uq_recovery_attempt_number"),
        UniqueConstraint("idempotency_key", name="uq_recovery_attempt_key"),
        UniqueConstraint("agency_id", "provider_reference", name="uq_recovery_attempt_provider"),
        CheckConstraint("channel IN ('SMS','VOICE')", name="channel_valid"),
        CheckConstraint("attempt_number BETWEEN 1 AND 2", name="number_valid"),
        CheckConstraint("status IN ('SCHEDULED','STARTED','QUEUED','SENT','DELIVERED','FAILED','UNKNOWN','CANCELLED')", name="status_valid"),
        Index("ix_recovery_attempts_due", "status", "scheduled_at"),
        Index("ix_recovery_attempt_recipient", "agency_id", "recipient_digest", "started_at"),
        Index("ix_recovery_attempt_channel", "agency_id", "channel", "provider_terminal_at"),
    )
    agency_id: Mapped[UUID] = mapped_column(ForeignKey("agencies.id", ondelete="RESTRICT"), nullable=False)
    recovery_case_id: Mapped[UUID] = mapped_column(nullable=False)
    channel: Mapped[str] = mapped_column(Text, nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    provider_reference: Mapped[str | None] = mapped_column(Text)
    failure_code: Mapped[str | None] = mapped_column(Text)
    idempotency_key: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str | None] = mapped_column(Text)
    recipient_digest: Mapped[str | None] = mapped_column(Text)
    dispatch_configuration: Mapped[dict[str, object] | None] = mapped_column(JSONB)
    provider_terminal_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_reconciled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RecoveryGrant(UuidPrimaryKeyMixin, TimestampedMixin, VersionedMixin, Base):
    __tablename__ = "lead_recovery_grants"
    __table_args__ = (
        UniqueConstraint("agency_id", "id", name="uq_recovery_grant_owned"),
        UniqueConstraint("attempt_id", name="uq_recovery_grant_attempt"),
        UniqueConstraint("appointment_id", name="uq_recovery_grant_appointment"),
        ForeignKeyConstraint(["agency_id", "attempt_id"], ["lead_recovery_attempts.agency_id", "lead_recovery_attempts.id"], ondelete="RESTRICT"),
        ForeignKeyConstraint(["agency_id", "recovery_case_id"], ["lead_recovery_cases.agency_id", "lead_recovery_cases.id"], ondelete="RESTRICT"),
        ForeignKeyConstraint(["agency_id", "appointment_id"], ["hvac_appointments.agency_id", "hvac_appointments.id"], ondelete="RESTRICT"),
        CheckConstraint("status IN ('WAITING','ACTIVE','CONSUMED','REVOKED','EXPIRED')", name="status_valid"),
        CheckConstraint("channel IN ('SMS','VOICE')", name="channel_valid"),
        CheckConstraint("reply_status IS NULL OR reply_status IN ('PENDING','STARTED','QUEUED','SENT','DELIVERED','FAILED','UNKNOWN','CANCELLED')", name="reply_status_valid"),
        CheckConstraint("status <> 'CONSUMED' OR (appointment_id IS NOT NULL AND approved_at IS NOT NULL)", name="consumed_valid"),
        CheckConstraint("approved_at IS NULL OR (appointment_id IS NOT NULL AND readback_nonce IS NOT NULL AND readback_fingerprint IS NOT NULL)", name="approval_valid"),
        CheckConstraint("reply_status IS NULL OR channel = 'SMS'", name="reply_channel_valid"),
        CheckConstraint("row_version > 0", name="version_positive"),
        Index("ix_recovery_grant_reply_due", "reply_status", "reply_due_at"),
    )
    agency_id: Mapped[UUID] = mapped_column(ForeignKey("agencies.id", ondelete="RESTRICT"), nullable=False)
    attempt_id: Mapped[UUID] = mapped_column(nullable=False)
    recovery_case_id: Mapped[UUID] = mapped_column(nullable=False)
    channel: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    appointment_id: Mapped[UUID | None] = mapped_column(nullable=True)
    reservation_key: Mapped[str | None] = mapped_column(Text)
    readback_nonce: Mapped[UUID | None] = mapped_column(nullable=True)
    readback_fingerprint: Mapped[str | None] = mapped_column(Text)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    provider_conversation_id: Mapped[str | None] = mapped_column(Text)
    reply_status: Mapped[str | None] = mapped_column(Text)
    reply_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reply_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reply_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reply_provider_reference: Mapped[str | None] = mapped_column(Text)
    failure_code: Mapped[str | None] = mapped_column(Text)


class RecoveryWebhook(UuidPrimaryKeyMixin, Base):
    __tablename__ = "lead_recovery_webhooks"
    __table_args__ = (
        UniqueConstraint("agency_id", "provider", "event_key", name="uq_recovery_webhook_identity"),
        ForeignKeyConstraint(["agency_id", "attempt_id"], ["lead_recovery_attempts.agency_id", "lead_recovery_attempts.id"], ondelete="RESTRICT"),
        Index("ix_recovery_webhook_pending", "processed_at", "next_attempt_at", "received_at"),
    )
    agency_id: Mapped[UUID] = mapped_column(ForeignKey("agencies.id", ondelete="RESTRICT"), nullable=False)
    attempt_id: Mapped[UUID | None] = mapped_column(nullable=True)
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    event_key: Mapped[str] = mapped_column(Text, nullable=False)
    fingerprint: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    data: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failure_code: Mapped[str | None] = mapped_column(Text)


class RecoveryProviderEvent(UuidPrimaryKeyMixin, Base):
    __tablename__ = "lead_recovery_provider_events"
    __table_args__ = (
        ForeignKeyConstraint(["agency_id", "attempt_id"], ["lead_recovery_attempts.agency_id", "lead_recovery_attempts.id"], ondelete="RESTRICT"),
        UniqueConstraint("attempt_id", "event_key", name="uq_recovery_provider_event"),
    )
    agency_id: Mapped[UUID] = mapped_column(ForeignKey("agencies.id", ondelete="RESTRICT"), nullable=False)
    attempt_id: Mapped[UUID] = mapped_column(nullable=False)
    event_key: Mapped[str] = mapped_column(Text, nullable=False)
    fingerprint: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RecoveryPermission(UuidPrimaryKeyMixin, TimestampedMixin, VersionedMixin, Base):
    __tablename__ = "lead_recovery_permissions"
    __table_args__ = (
        UniqueConstraint("agency_id", "destination_digest", "channel", name="uq_recovery_permission_contact"),
        CheckConstraint("channel IN ('SMS','VOICE','ALL')", name="channel_valid"),
        CheckConstraint("scope = 'LEAD_RECOVERY'", name="scope_valid"),
        CheckConstraint("row_version > 0", name="version_positive"),
    )
    agency_id: Mapped[UUID] = mapped_column(ForeignKey("agencies.id", ondelete="RESTRICT"), nullable=False)
    destination_digest: Mapped[str] = mapped_column(Text, nullable=False)
    channel: Mapped[str] = mapped_column(Text, nullable=False)
    scope: Mapped[str] = mapped_column(Text, nullable=False, default="LEAD_RECOVERY", server_default="LEAD_RECOVERY")
    source: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_reference: Mapped[str] = mapped_column(Text, nullable=False)
    granted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RecoveryAiConnection(TimestampedMixin, VersionedMixin, Base):
    __tablename__ = "lead_recovery_ai_connections"
    __table_args__ = (
        CheckConstraint("provider IN ('OPENAI','OPENAI_COMPATIBLE')", name="provider_valid"),
        CheckConstraint("status IN ('UNTESTED','CONNECTED','ERROR','REVOKED')", name="status_valid"),
        CheckConstraint("(status = 'REVOKED') = (credential_ciphertext IS NULL)", name="credential_valid"),
        CheckConstraint("row_version > 0", name="version_positive"),
    )
    agency_id: Mapped[UUID] = mapped_column(ForeignKey("agencies.id", ondelete="RESTRICT"), primary_key=True)
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(Text, nullable=False)
    endpoint: Mapped[str] = mapped_column(Text, nullable=False)
    credential_ciphertext: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="UNTESTED")
    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
