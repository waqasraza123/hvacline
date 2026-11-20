"""Durable recovery provider inbox and request-scoped booking grants."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "20261120_0027"
down_revision = "20261120_0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for name in ("provider", "recipient_digest"):
        op.add_column("lead_recovery_attempts", sa.Column(name, sa.Text()))
    op.add_column("lead_recovery_attempts", sa.Column("dispatch_configuration", JSONB()))
    for name in ("provider_terminal_at", "last_reconciled_at"):
        op.add_column("lead_recovery_attempts", sa.Column(name, sa.DateTime(timezone=True)))
    op.create_index("ix_recovery_attempt_recipient", "lead_recovery_attempts", ["agency_id", "recipient_digest", "started_at"])
    op.create_index("ix_recovery_attempt_channel", "lead_recovery_attempts", ["agency_id", "channel", "provider_terminal_at"])
    op.create_table(
        "lead_recovery_grants",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("agency_id", sa.Uuid(), sa.ForeignKey("agencies.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("attempt_id", sa.Uuid(), nullable=False),
        sa.Column("recovery_case_id", sa.Uuid(), nullable=False),
        sa.Column("channel", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("appointment_id", sa.Uuid()),
        sa.Column("reservation_key", sa.Text()),
        sa.Column("readback_nonce", sa.Uuid()),
        sa.Column("readback_fingerprint", sa.Text()),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("provider_conversation_id", sa.Text()),
        sa.Column("reply_status", sa.Text()),
        sa.Column("reply_due_at", sa.DateTime(timezone=True)),
        sa.Column("reply_started_at", sa.DateTime(timezone=True)),
        sa.Column("reply_completed_at", sa.DateTime(timezone=True)),
        sa.Column("reply_provider_reference", sa.Text()),
        sa.Column("failure_code", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("row_version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.UniqueConstraint("agency_id", "id", name="uq_recovery_grant_owned"),
        sa.UniqueConstraint("attempt_id", name="uq_recovery_grant_attempt"),
        sa.UniqueConstraint("appointment_id", name="uq_recovery_grant_appointment"),
        sa.ForeignKeyConstraint(["agency_id", "attempt_id"], ["lead_recovery_attempts.agency_id", "lead_recovery_attempts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["agency_id", "recovery_case_id"], ["lead_recovery_cases.agency_id", "lead_recovery_cases.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["agency_id", "appointment_id"], ["hvac_appointments.agency_id", "hvac_appointments.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("status IN ('WAITING','ACTIVE','CONSUMED','REVOKED','EXPIRED')", name="status_valid"),
        sa.CheckConstraint("channel IN ('SMS','VOICE')", name="channel_valid"),
        sa.CheckConstraint("reply_status IS NULL OR reply_status IN ('PENDING','STARTED','QUEUED','SENT','DELIVERED','FAILED','UNKNOWN','CANCELLED')", name="reply_status_valid"),
        sa.CheckConstraint("status <> 'CONSUMED' OR (appointment_id IS NOT NULL AND approved_at IS NOT NULL)", name="consumed_valid"),
        sa.CheckConstraint("approved_at IS NULL OR (appointment_id IS NOT NULL AND readback_nonce IS NOT NULL AND readback_fingerprint IS NOT NULL)", name="approval_valid"),
        sa.CheckConstraint("reply_status IS NULL OR channel = 'SMS'", name="reply_channel_valid"),
        sa.CheckConstraint("row_version > 0", name="version_positive"),
    )
    op.create_index("ix_recovery_grant_reply_due", "lead_recovery_grants", ["reply_status", "reply_due_at"])
    op.create_table(
        "lead_recovery_webhooks",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("agency_id", sa.Uuid(), sa.ForeignKey("agencies.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("attempt_id", sa.Uuid()),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("event_key", sa.Text(), nullable=False),
        sa.Column("fingerprint", sa.Text(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("data", JSONB(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("processed_at", sa.DateTime(timezone=True)),
        sa.Column("failure_code", sa.Text()),
        sa.UniqueConstraint("agency_id", "provider", "event_key", name="uq_recovery_webhook_identity"),
        sa.ForeignKeyConstraint(["agency_id", "attempt_id"], ["lead_recovery_attempts.agency_id", "lead_recovery_attempts.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_recovery_webhook_pending", "lead_recovery_webhooks", ["processed_at", "next_attempt_at", "received_at"])
    op.execute("""
        CREATE FUNCTION guard_recovery_grant() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF NOT EXISTS (SELECT 1 FROM lead_recovery_attempts a WHERE
             a.agency_id = NEW.agency_id AND a.id = NEW.attempt_id AND
             a.recovery_case_id = NEW.recovery_case_id AND a.channel = NEW.channel)
          THEN RAISE EXCEPTION 'Recovery grant does not match its owned attempt'; END IF;
          IF NEW.appointment_id IS NOT NULL AND NOT EXISTS (
             SELECT 1 FROM hvac_appointments a JOIN lead_recovery_cases c ON
             c.agency_id = a.agency_id AND c.service_request_id = a.service_request_id
             WHERE a.agency_id = NEW.agency_id AND a.id = NEW.appointment_id AND c.id = NEW.recovery_case_id)
          THEN RAISE EXCEPTION 'Recovery grant appointment does not match its request'; END IF;
          IF TG_OP = 'INSERT' THEN RETURN NEW; END IF;
          IF (NEW.agency_id, NEW.attempt_id, NEW.recovery_case_id, NEW.channel, NEW.expires_at)
             IS DISTINCT FROM
             (OLD.agency_id, OLD.attempt_id, OLD.recovery_case_id, OLD.channel, OLD.expires_at)
          THEN RAISE EXCEPTION 'Recovery grant scope is immutable'; END IF;
          IF OLD.status <> NEW.status AND NOT (
            (OLD.status = 'WAITING' AND NEW.status IN ('ACTIVE','REVOKED','EXPIRED')) OR
            (OLD.status = 'ACTIVE' AND NEW.status IN ('CONSUMED','REVOKED','EXPIRED'))
          ) THEN RAISE EXCEPTION 'Invalid recovery grant transition'; END IF;
          IF OLD.approved_at IS NOT NULL AND
             (NEW.appointment_id, NEW.readback_nonce, NEW.readback_fingerprint, NEW.approved_at)
             IS DISTINCT FROM
             (OLD.appointment_id, OLD.readback_nonce, OLD.readback_fingerprint, OLD.approved_at)
          THEN RAISE EXCEPTION 'Approved recovery selection is immutable'; END IF;
          IF OLD.reply_provider_reference IS NOT NULL AND NEW.reply_provider_reference IS DISTINCT FROM OLD.reply_provider_reference
          THEN RAISE EXCEPTION 'Recovery reply reference is immutable'; END IF;
          IF OLD.provider_conversation_id IS NOT NULL AND NEW.provider_conversation_id IS DISTINCT FROM OLD.provider_conversation_id
          THEN RAISE EXCEPTION 'Recovery conversation reference is immutable'; END IF;
          IF OLD.reply_status IS DISTINCT FROM NEW.reply_status AND NOT COALESCE((
            (OLD.reply_status = 'PENDING' AND NEW.reply_status IN ('STARTED','CANCELLED')) OR
            (OLD.reply_status = 'STARTED' AND NEW.reply_status IN ('QUEUED','SENT','DELIVERED','FAILED','UNKNOWN','CANCELLED')) OR
            (OLD.reply_status IN ('QUEUED','UNKNOWN') AND NEW.reply_status IN ('QUEUED','SENT','DELIVERED','FAILED','UNKNOWN')) OR
            (OLD.reply_status = 'SENT' AND NEW.reply_status IN ('DELIVERED','FAILED')) OR
            (OLD.reply_status = 'DELIVERED' AND NEW.reply_status = 'FAILED')
          ), FALSE) THEN RAISE EXCEPTION 'Invalid recovery reply transition'; END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER recovery_grant_guard BEFORE INSERT OR UPDATE ON lead_recovery_grants
        FOR EACH ROW EXECUTE FUNCTION guard_recovery_grant();
        CREATE TRIGGER recovery_grant_version BEFORE UPDATE ON lead_recovery_grants
        FOR EACH ROW EXECUTE FUNCTION set_mutable_record_metadata();
        CREATE FUNCTION guard_recovery_dispatch() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF OLD.started_at IS NOT NULL AND
             (NEW.provider, NEW.recipient_digest, NEW.dispatch_configuration) IS DISTINCT FROM
             (OLD.provider, OLD.recipient_digest, OLD.dispatch_configuration)
          THEN RAISE EXCEPTION 'Recovery dispatch snapshot is immutable'; END IF;
          IF OLD.provider_reference IS NOT NULL AND NEW.provider_reference IS DISTINCT FROM OLD.provider_reference
          THEN RAISE EXCEPTION 'Recovery provider reference is immutable'; END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER recovery_dispatch_guard BEFORE UPDATE ON lead_recovery_attempts
        FOR EACH ROW EXECUTE FUNCTION guard_recovery_dispatch();
        CREATE OR REPLACE FUNCTION enforce_recovery_transition() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF OLD.status <> NEW.status AND NOT (
            (OLD.status IN ('PENDING','READY','SCHEDULED','AWAITING_RESPONSE','NEEDS_REVIEW')
              AND NEW.status IN ('READY','SCHEDULED','IN_PROGRESS','AWAITING_RESPONSE','NEEDS_REVIEW','SUPPRESSED','CLOSED','RECOVERED')) OR
            (OLD.status = 'IN_PROGRESS' AND NEW.status IN ('AWAITING_RESPONSE','NEEDS_REVIEW','SUPPRESSED','CLOSED','RECOVERED'))
          ) THEN RAISE EXCEPTION 'Invalid recovery transition'; END IF;
          RETURN NEW;
        END $$;
    """)


def downgrade() -> None:
    op.execute("""DO $$ BEGIN
      IF EXISTS (SELECT 1 FROM lead_recovery_grants) OR EXISTS (SELECT 1 FROM lead_recovery_webhooks)
      THEN RAISE EXCEPTION 'Retain recovery authorization and provider history; use a forward migration'; END IF;
    END $$""")
    op.drop_table("lead_recovery_webhooks")
    op.drop_table("lead_recovery_grants")
    op.drop_index("ix_recovery_attempt_recipient", table_name="lead_recovery_attempts")
    op.drop_index("ix_recovery_attempt_channel", table_name="lead_recovery_attempts")
    op.execute("DROP FUNCTION guard_recovery_grant()")
    op.execute("DROP TRIGGER recovery_dispatch_guard ON lead_recovery_attempts")
    op.execute("DROP FUNCTION guard_recovery_dispatch()")
    op.execute("""CREATE OR REPLACE FUNCTION enforce_recovery_transition() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF OLD.status <> NEW.status AND NOT (
        (OLD.status IN ('PENDING','READY','SCHEDULED','AWAITING_RESPONSE','NEEDS_REVIEW')
          AND NEW.status IN ('READY','SCHEDULED','IN_PROGRESS','NEEDS_REVIEW','SUPPRESSED','CLOSED','RECOVERED')) OR
        (OLD.status = 'IN_PROGRESS' AND NEW.status IN ('AWAITING_RESPONSE','NEEDS_REVIEW','SUPPRESSED','CLOSED','RECOVERED'))
      ) THEN RAISE EXCEPTION 'Invalid recovery transition'; END IF;
      RETURN NEW;
    END $$""")
    for name in ("provider", "recipient_digest", "dispatch_configuration", "provider_terminal_at", "last_reconciled_at"):
        op.drop_column("lead_recovery_attempts", name)
