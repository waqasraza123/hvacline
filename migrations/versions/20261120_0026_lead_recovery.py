"""Prospective lead recovery, explicit permissions and encrypted AI connections."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "20261120_0026"
down_revision = "20261118_0025"
branch_labels = None
depends_on = None


def agency() -> sa.Column:
    return sa.Column("agency_id", sa.Uuid(), sa.ForeignKey("agencies.id", ondelete="RESTRICT"), nullable=False)


def timestamps(versioned: bool = True) -> list[sa.Column]:
    columns = [sa.Column(name, sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()) for name in ("created_at", "updated_at")]
    if versioned:
        columns.append(sa.Column("row_version", sa.BigInteger(), nullable=False, server_default="1"))
    return columns


def identifier() -> sa.Column:
    return sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()"))


def upgrade() -> None:
    op.create_table("lead_recovery_policies", agency(), *timestamps(),
        sa.PrimaryKeyConstraint("agency_id"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("configuration", JSONB(), nullable=False),
        sa.Column("capture_from", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("row_version > 0", name="version_positive"))
    op.execute("""
        INSERT INTO lead_recovery_policies (agency_id, enabled, capture_from, configuration)
        SELECT a.id, false, clock_timestamp(), jsonb_build_object(
          'channels', '[]'::jsonb,
          'timezone', COALESCE(s.configuration->>'timezone', 'America/New_York'),
          'contact_start', '09:00:00', 'contact_end', '18:00:00',
          'max_attempts', 2, 'interval_hours', 24, 'expiry_days', 7,
          'abandoned_delay_minutes', 10, 'booking_delay_minutes', 30)
        FROM agencies a LEFT JOIN business_schedules s ON s.agency_id = a.id
    """)
    op.create_table("lead_recovery_cases", identifier(), agency(), *timestamps(),
        sa.Column("service_request_id", sa.Uuid(), nullable=False),
        sa.Column("lead_id", sa.Uuid()),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("source_reference", sa.Uuid(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="PENDING"),
        sa.Column("eligible_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recovered_appointment_id", sa.Uuid()),
        sa.Column("paused", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("assigned_to", sa.Uuid(), sa.ForeignKey("app_users.id", ondelete="RESTRICT")),
        sa.Column("reason", sa.Text()),
        sa.UniqueConstraint("agency_id", "id", name="uq_recovery_cases_owned"),
        sa.UniqueConstraint("agency_id", "service_request_id", name="uq_recovery_cases_request"),
        sa.UniqueConstraint("agency_id", "source_type", "source_reference", name="uq_recovery_cases_source"),
        sa.ForeignKeyConstraint(["agency_id", "service_request_id"], ["hvac_service_requests.agency_id", "hvac_service_requests.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["agency_id", "lead_id"], ["agency_leads.agency_id", "agency_leads.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["agency_id", "recovered_appointment_id"], ["hvac_appointments.agency_id", "hvac_appointments.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["agency_id", "assigned_to"], ["agency_memberships.agency_id", "agency_memberships.app_user_id"], ondelete="RESTRICT"),
        sa.CheckConstraint("status IN ('PENDING','READY','SCHEDULED','IN_PROGRESS','AWAITING_RESPONSE','RECOVERED','NEEDS_REVIEW','SUPPRESSED','CLOSED')", name="status_valid"),
        sa.CheckConstraint("source_type IN ('MISSED_CALL','ABANDONED_CONVERSATION','UNCONFIRMED_BOOKING')", name="source_valid"),
        sa.CheckConstraint("status <> 'RECOVERED' OR recovered_appointment_id IS NOT NULL", name="recovered_valid"),
        sa.CheckConstraint("row_version > 0", name="version_positive"))
    op.create_index("ix_recovery_cases_due", "lead_recovery_cases", ["status", "eligible_at"])
    op.create_index("ix_recovery_cases_agency_activity", "lead_recovery_cases", ["agency_id", "last_activity_at"])
    op.create_table("lead_recovery_attempts", identifier(), agency(), *timestamps(False),
        sa.Column("recovery_case_id", sa.Uuid(), nullable=False),
        sa.Column("channel", sa.Text(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("provider_reference", sa.Text()),
        sa.Column("failure_code", sa.Text()),
        sa.Column("idempotency_key", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["agency_id", "recovery_case_id"], ["lead_recovery_cases.agency_id", "lead_recovery_cases.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("recovery_case_id", "attempt_number", name="uq_recovery_attempt_number"),
        sa.UniqueConstraint("agency_id", "id", name="uq_recovery_attempt_owned"),
        sa.UniqueConstraint("idempotency_key", name="uq_recovery_attempt_key"),
        sa.UniqueConstraint("agency_id", "provider_reference", name="uq_recovery_attempt_provider"),
        sa.CheckConstraint("channel IN ('SMS','VOICE')", name="channel_valid"),
        sa.CheckConstraint("attempt_number BETWEEN 1 AND 2", name="number_valid"),
        sa.CheckConstraint("status IN ('SCHEDULED','STARTED','QUEUED','SENT','DELIVERED','FAILED','UNKNOWN','CANCELLED')", name="status_valid"))
    op.create_index("ix_recovery_attempts_due", "lead_recovery_attempts", ["status", "scheduled_at"])
    op.create_table("lead_recovery_provider_events", identifier(), agency(),
        sa.Column("attempt_id", sa.Uuid(), nullable=False),
        sa.Column("event_key", sa.Text(), nullable=False),
        sa.Column("fingerprint", sa.Text(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["agency_id", "attempt_id"], ["lead_recovery_attempts.agency_id", "lead_recovery_attempts.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("attempt_id", "event_key", name="uq_recovery_provider_event"))
    op.create_table("lead_recovery_permissions", identifier(), agency(), *timestamps(),
        sa.Column("destination_digest", sa.Text(), nullable=False),
        sa.Column("channel", sa.Text(), nullable=False),
        sa.Column("scope", sa.Text(), nullable=False, server_default="LEAD_RECOVERY"),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("evidence_reference", sa.Text(), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("agency_id", "destination_digest", "channel", name="uq_recovery_permission_contact"),
        sa.CheckConstraint("channel IN ('SMS','VOICE','ALL')", name="channel_valid"),
        sa.CheckConstraint("scope = 'LEAD_RECOVERY'", name="scope_valid"),
        sa.CheckConstraint("row_version > 0", name="version_positive"))
    op.create_table("lead_recovery_ai_connections", agency(), *timestamps(),
        sa.PrimaryKeyConstraint("agency_id"),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("credential_ciphertext", sa.Text()),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("last_tested_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text()),
        sa.CheckConstraint("provider IN ('OPENAI','OPENAI_COMPATIBLE')", name="provider_valid"),
        sa.CheckConstraint("status IN ('UNTESTED','CONNECTED','ERROR','REVOKED')", name="status_valid"),
        sa.CheckConstraint("(status = 'REVOKED') = (credential_ciphertext IS NULL)", name="credential_valid"),
        sa.CheckConstraint("row_version > 0", name="version_positive"))
    op.execute("""
        CREATE FUNCTION preserve_recovery_capture() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF NEW.capture_from <> OLD.capture_from THEN
            RAISE EXCEPTION 'Recovery capture watermark is immutable';
          END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER recovery_capture BEFORE UPDATE ON lead_recovery_policies
        FOR EACH ROW EXECUTE FUNCTION preserve_recovery_capture();
        CREATE FUNCTION enforce_recovery_transition() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF OLD.status <> NEW.status AND NOT (
            (OLD.status IN ('PENDING','READY','SCHEDULED','AWAITING_RESPONSE','NEEDS_REVIEW')
              AND NEW.status IN ('READY','SCHEDULED','IN_PROGRESS','NEEDS_REVIEW','SUPPRESSED','CLOSED','RECOVERED')) OR
            (OLD.status = 'IN_PROGRESS' AND NEW.status IN ('AWAITING_RESPONSE','NEEDS_REVIEW','SUPPRESSED','CLOSED','RECOVERED'))
          ) THEN RAISE EXCEPTION 'Invalid recovery transition'; END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER recovery_transition BEFORE UPDATE ON lead_recovery_cases
        FOR EACH ROW EXECUTE FUNCTION enforce_recovery_transition();
        CREATE FUNCTION enforce_recovery_attempt_transition() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF OLD.status <> NEW.status AND NOT (
            (OLD.status = 'SCHEDULED' AND NEW.status IN ('STARTED','CANCELLED')) OR
            (OLD.status = 'STARTED' AND NEW.status IN ('QUEUED','SENT','DELIVERED','FAILED','UNKNOWN','CANCELLED')) OR
            (OLD.status IN ('QUEUED','UNKNOWN') AND NEW.status IN ('QUEUED','SENT','DELIVERED','FAILED','UNKNOWN')) OR
            (OLD.status = 'SENT' AND NEW.status IN ('DELIVERED','FAILED')) OR
            (OLD.status = 'DELIVERED' AND NEW.status = 'FAILED')
          ) THEN RAISE EXCEPTION 'Invalid recovery attempt transition'; END IF;
          NEW.updated_at = clock_timestamp();
          RETURN NEW;
        END $$;
        CREATE TRIGGER recovery_attempt_transition BEFORE UPDATE ON lead_recovery_attempts
        FOR EACH ROW EXECUTE FUNCTION enforce_recovery_attempt_transition();
    """)
    for table in ("lead_recovery_policies", "lead_recovery_cases", "lead_recovery_permissions", "lead_recovery_ai_connections"):
        op.execute(f"CREATE TRIGGER {table}_version BEFORE UPDATE ON {table} FOR EACH ROW EXECUTE FUNCTION set_mutable_record_metadata()")


def downgrade() -> None:
    op.execute("DO $$ BEGIN IF EXISTS (SELECT 1 FROM lead_recovery_cases) THEN RAISE EXCEPTION 'Retain recovery history'; END IF; END $$")
    for table in ("lead_recovery_provider_events", "lead_recovery_attempts", "lead_recovery_cases", "lead_recovery_permissions", "lead_recovery_ai_connections", "lead_recovery_policies"):
        op.drop_table(table)
    op.execute("DROP FUNCTION enforce_recovery_transition()")
    op.execute("DROP FUNCTION enforce_recovery_attempt_transition()")
    op.execute("DROP FUNCTION preserve_recovery_capture()")
