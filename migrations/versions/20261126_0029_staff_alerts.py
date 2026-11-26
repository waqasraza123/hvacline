"""Prospective staff email alerts with immutable payloads and bounded retries."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "20261126_0029"
down_revision = "20261121_0028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "staff_alert_policies",
        sa.Column("agency_id", sa.Uuid(), sa.ForeignKey("agencies.id", ondelete="RESTRICT"), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("recipients", JSONB(), nullable=False, server_default="[]"),
        sa.Column("sender", sa.Text()),
        sa.Column("row_version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("row_version > 0", name="version_positive"),
        sa.CheckConstraint("jsonb_typeof(recipients) = 'array' AND jsonb_array_length(recipients) <= 5", name="recipients_valid"),
        sa.CheckConstraint("NOT enabled OR (sender IS NOT NULL AND jsonb_array_length(recipients) > 0)", name="enabled_valid"),
    )
    op.execute("CREATE TRIGGER staff_alert_policies_version BEFORE UPDATE ON staff_alert_policies FOR EACH ROW EXECUTE FUNCTION set_mutable_record_metadata()")
    op.create_table(
        "staff_alerts",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("agency_id", sa.Uuid(), sa.ForeignKey("agencies.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("recipient", sa.Text(), nullable=False),
        sa.Column("policy_version", sa.BigInteger(), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="PENDING"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("first_attempt_at", sa.DateTime(timezone=True)),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("provider_reference", sa.Text()),
        sa.Column("last_error", sa.Text()),
        sa.Column("delivery_status", sa.Text()),
        sa.UniqueConstraint("agency_id", "event_type", "source_id", "recipient", name="uq_staff_alert_source_recipient"),
        sa.CheckConstraint("event_type IN ('HANDOFF', 'URGENT_SERVICE')", name="event_type_valid"),
        sa.CheckConstraint("status IN ('PENDING', 'ACCEPTED', 'SKIPPED', 'FAILED', 'UNKNOWN')", name="status_valid"),
        sa.CheckConstraint("attempts >= 0", name="attempts_valid"),
        sa.CheckConstraint("policy_version > 0", name="policy_version_positive"),
    )
    op.create_index("ix_staff_alerts_agency_id", "staff_alerts", ["agency_id"])
    op.create_index("ix_staff_alerts_due_at", "staff_alerts", ["due_at"])
    op.execute("""
        CREATE FUNCTION capture_staff_alert() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE
          policy staff_alert_policies%ROWTYPE;
          kind text;
          destination text;
        BEGIN
          IF TG_TABLE_NAME = 'hvac_service_requests' THEN
            IF NEW.status <> 'HANDOFF_REQUESTED' OR
               NEW.service_details->>'hazardous_condition' IS DISTINCT FROM 'true'
            THEN RETURN NEW; END IF;
            IF TG_OP = 'UPDATE' AND OLD.status = 'HANDOFF_REQUESTED' AND
               OLD.service_details->>'hazardous_condition' = 'true'
            THEN RETURN NEW; END IF;
            kind := 'URGENT_SERVICE';
          ELSE
            IF NEW.status NOT IN ('REQUESTED', 'ACKNOWLEDGED') THEN RETURN NEW; END IF;
            kind := 'HANDOFF';
          END IF;
          SELECT * INTO policy FROM staff_alert_policies
            WHERE agency_id = NEW.agency_id FOR SHARE;
          IF NOT FOUND OR NOT policy.enabled THEN RETURN NEW; END IF;
          FOR destination IN SELECT jsonb_array_elements_text(policy.recipients) LOOP
            INSERT INTO staff_alerts (agency_id, event_type, source_id, recipient, policy_version, payload)
              VALUES (NEW.agency_id, kind, NEW.id, destination, policy.row_version,
                jsonb_build_object('from', policy.sender, 'to', jsonb_build_array(destination),
                  'subject', CASE WHEN kind = 'URGENT_SERVICE' THEN 'HVACLine: urgent service requires staff review' ELSE 'HVACLine: customer follow-up requested' END,
                  'text', 'A new request requires your team in the protected HVACLine Operations workspace.' || E'\\n' ||
                    'Business reference: ' || NEW.agency_id::text || E'\\n' ||
                    'Request reference: ' || NEW.id::text || E'\\n' ||
                    'This is a staff notification, not confirmation that the customer was contacted.'))
              ON CONFLICT (agency_id, event_type, source_id, recipient) DO NOTHING;
          END LOOP;
          RETURN NEW;
        END $$;
        CREATE TRIGGER handoff_staff_alert AFTER INSERT ON lead_handoff_requests
          FOR EACH ROW EXECUTE FUNCTION capture_staff_alert();
        CREATE TRIGGER urgent_staff_alert AFTER INSERT OR UPDATE OF status, service_details ON hvac_service_requests
          FOR EACH ROW EXECUTE FUNCTION capture_staff_alert();
        CREATE FUNCTION preserve_staff_alert_payload() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF (NEW.agency_id, NEW.event_type, NEW.source_id, NEW.recipient, NEW.policy_version, NEW.payload, NEW.created_at)
             IS DISTINCT FROM
             (OLD.agency_id, OLD.event_type, OLD.source_id, OLD.recipient, OLD.policy_version, OLD.payload, OLD.created_at)
          THEN RAISE EXCEPTION 'Staff alert delivery context is immutable'; END IF;
          IF OLD.first_attempt_at IS NOT NULL AND NEW.first_attempt_at IS DISTINCT FROM OLD.first_attempt_at
          THEN RAISE EXCEPTION 'Staff alert attempt horizon is immutable'; END IF;
          IF OLD.status <> 'PENDING' AND NEW.status <> OLD.status
          THEN RAISE EXCEPTION 'Staff alert outcomes cannot be reopened'; END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER staff_alert_payload BEFORE UPDATE ON staff_alerts
          FOR EACH ROW EXECUTE FUNCTION preserve_staff_alert_payload();
    """)


def downgrade() -> None:
    op.execute("DO $$ BEGIN IF EXISTS (SELECT 1 FROM staff_alerts) THEN RAISE EXCEPTION 'Retain staff alert history'; END IF; END $$")
    op.execute("DROP TRIGGER urgent_staff_alert ON hvac_service_requests")
    op.execute("DROP TRIGGER handoff_staff_alert ON lead_handoff_requests")
    op.drop_table("staff_alerts")
    op.drop_table("staff_alert_policies")
    op.execute("DROP FUNCTION preserve_staff_alert_payload()")
    op.execute("DROP FUNCTION capture_staff_alert()")
