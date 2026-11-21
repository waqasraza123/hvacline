"""Business-owned GHL connections and transactional delivery queue."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "20261113_0024"
down_revision = "20261113_0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_agency_leads_agency_id", "agency_leads", ["agency_id", "id"]
    )
    op.create_table(
        "ghl_connections",
        sa.Column(
            "id",
            sa.Uuid(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "agency_id",
            sa.Uuid(),
            sa.ForeignKey("agencies.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("location_id", sa.Text(), nullable=False),
        sa.Column("pipeline_id", sa.Text(), nullable=False),
        sa.Column("stages", JSONB(), nullable=False),
        sa.Column("fields", JSONB(), nullable=False),
        sa.Column("token_ciphertext", sa.Text()),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_checked_at", sa.DateTime(timezone=True)),
        sa.Column("blocked_until", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text()),
        sa.UniqueConstraint("agency_id", "id", name="uq_ghl_connections_agency_id"),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'PAUSED', 'ERROR', 'DISCONNECTED')",
            name="status_valid",
        ),
        sa.CheckConstraint(
            "(status = 'DISCONNECTED' AND token_ciphertext IS NULL) OR "
            "(status <> 'DISCONNECTED' AND token_ciphertext IS NOT NULL)",
            name="token_state_valid",
        ),
    )
    for column in ("agency_id", "location_id"):
        suffix = "agency" if column == "agency_id" else "location"
        op.create_index(
            f"uq_ghl_connections_active_{suffix}",
            "ghl_connections",
            [column],
            unique=True,
            postgresql_where=sa.text("status <> 'DISCONNECTED'"),
        )
    op.create_table(
        "ghl_deliveries",
        sa.Column(
            "id",
            sa.Uuid(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "agency_id",
            sa.Uuid(),
            sa.ForeignKey("agencies.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("connection_id", sa.Uuid(), nullable=False),
        sa.Column("lead_id", sa.Uuid(), nullable=False),
        sa.Column(
            "desired_version", sa.BigInteger(), nullable=False, server_default="1"
        ),
        sa.Column(
            "delivered_version", sa.BigInteger(), nullable=False, server_default="0"
        ),
        sa.Column("status", sa.Text(), nullable=False, server_default="PENDING"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("contact_id", sa.Text()),
        sa.Column("opportunity_id", sa.Text()),
        sa.Column(
            "contact_unknown", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column(
            "opportunity_unknown", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column("last_stage_id", sa.Text()),
        sa.Column("pending_stage_id", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("clock_timestamp()"),
        ),
        sa.Column(
            "next_attempt_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("clock_timestamp()"),
        ),
        sa.Column("last_synced_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text()),
        sa.ForeignKeyConstraint(
            ["agency_id", "connection_id"],
            ["ghl_connections.agency_id", "ghl_connections.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["agency_id", "lead_id"],
            ["agency_leads.agency_id", "agency_leads.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("connection_id", "lead_id", name="uq_ghl_deliveries_lead"),
        sa.UniqueConstraint(
            "connection_id", "opportunity_id", name="uq_ghl_deliveries_opportunity"
        ),
        sa.CheckConstraint(
            "status IN ('PENDING', 'PROCESSING', 'SYNCED', 'RETRYING', 'NEEDS_REVIEW')",
            name="status_valid",
        ),
        sa.CheckConstraint(
            "desired_version > 0 AND delivered_version >= 0 "
            "AND delivered_version <= desired_version AND attempts >= 0",
            name="progress_valid",
        ),
    )
    op.create_index(
        "ix_ghl_deliveries_due", "ghl_deliveries", ["status", "next_attempt_at"]
    )
    op.create_index(
        "ix_ghl_deliveries_agency_created",
        "ghl_deliveries",
        ["agency_id", "created_at"],
    )
    op.execute("""
        CREATE FUNCTION ghl_touch_lead(owner_id uuid, target_id uuid, enroll boolean)
        RETURNS void LANGUAGE plpgsql AS $$
        BEGIN
          INSERT INTO ghl_deliveries (agency_id, connection_id, lead_id)
          SELECT owner_id, c.id, l.id
          FROM ghl_connections c JOIN agency_leads l ON l.agency_id = c.agency_id
          JOIN conversation_intakes i ON i.id = l.conversation_intake_id
            AND i.agency_id = l.agency_id
          WHERE c.agency_id = owner_id AND l.id = target_id
            AND c.status <> 'DISCONNECTED'
            AND ((enroll AND i.confirmed_at >= c.activated_at) OR EXISTS (
              SELECT 1 FROM ghl_deliveries d
              WHERE d.connection_id = c.id AND d.lead_id = l.id
            ))
          ON CONFLICT (connection_id, lead_id) DO UPDATE SET
            desired_version = ghl_deliveries.desired_version + 1,
            status = CASE WHEN ghl_deliveries.status = 'SYNCED'
              THEN 'PENDING' ELSE ghl_deliveries.status END,
            next_attempt_at = CASE WHEN ghl_deliveries.status = 'SYNCED'
              THEN clock_timestamp() ELSE ghl_deliveries.next_attempt_at END;
        END $$;

        CREATE FUNCTION ghl_touch_request(owner_id uuid, request_id uuid)
        RETURNS void LANGUAGE plpgsql AS $$
        DECLARE target uuid;
        BEGIN
          FOR target IN
            SELECT l.id FROM agency_leads l
            JOIN conversation_intakes i ON i.id = l.conversation_intake_id
              AND i.agency_id = l.agency_id
            JOIN conversation_sessions s ON s.id = i.conversation_session_id
              AND s.agency_id = i.agency_id
            JOIN hvac_service_requests r ON r.agency_id = s.agency_id AND (
              r.conversation_session_id = s.id OR
              (s.inbound_call_id IS NOT NULL AND r.inbound_call_id = s.inbound_call_id)
            )
            WHERE r.id = request_id AND r.agency_id = owner_id
          LOOP
            PERFORM ghl_touch_lead(owner_id, target, false);
          END LOOP;
        END $$;

        CREATE FUNCTION ghl_capture_change() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF TG_TABLE_NAME = 'agency_leads' THEN
            IF TG_OP = 'UPDATE' THEN
              IF NEW.summary IS NOT DISTINCT FROM OLD.summary
                AND NEW.urgency IS NOT DISTINCT FROM OLD.urgency THEN
                RETURN NEW;
              END IF;
            END IF;
            PERFORM ghl_touch_lead(NEW.agency_id, NEW.id, TG_OP = 'INSERT');
          ELSIF TG_TABLE_NAME = 'lead_handoff_requests' THEN
            IF TG_OP = 'UPDATE' THEN
              IF NEW.status IS NOT DISTINCT FROM OLD.status THEN RETURN NEW; END IF;
            END IF;
            PERFORM ghl_touch_lead(NEW.agency_id, NEW.lead_id, false);
          ELSIF TG_TABLE_NAME = 'hvac_service_requests' THEN
            IF TG_OP = 'UPDATE' THEN
              IF NEW.status IS NOT DISTINCT FROM OLD.status
                AND NEW.service_details IS NOT DISTINCT FROM OLD.service_details THEN
                RETURN NEW;
              END IF;
            END IF;
            PERFORM ghl_touch_request(NEW.agency_id, NEW.id);
          ELSIF TG_TABLE_NAME = 'hvac_appointments' THEN
            IF TG_OP = 'UPDATE' THEN
              IF NEW.status IS NOT DISTINCT FROM OLD.status
                AND NEW.starts_at IS NOT DISTINCT FROM OLD.starts_at
                AND NEW.ends_at IS NOT DISTINCT FROM OLD.ends_at THEN
                RETURN NEW;
              END IF;
            END IF;
            IF NEW.status = 'CONFIRMED' THEN
              PERFORM ghl_touch_request(NEW.agency_id, NEW.service_request_id);
            ELSIF TG_OP = 'UPDATE' THEN
              IF OLD.status = 'CONFIRMED' THEN
                PERFORM ghl_touch_request(NEW.agency_id, NEW.service_request_id);
              END IF;
            END IF;
          ELSIF TG_TABLE_NAME = 'calendar_bookings' THEN
            IF TG_OP = 'UPDATE' THEN
              IF NEW.status IS NOT DISTINCT FROM OLD.status
                AND NEW.last_error IS NOT DISTINCT FROM OLD.last_error THEN
                RETURN NEW;
              END IF;
            END IF;
            PERFORM ghl_touch_request(NEW.agency_id, (
              SELECT service_request_id FROM hvac_appointments
              WHERE id = NEW.appointment_id AND agency_id = NEW.agency_id
            ));
          END IF;
          RETURN NEW;
        END $$;
    """)
    for table in (
        "agency_leads",
        "lead_handoff_requests",
        "hvac_service_requests",
        "hvac_appointments",
        "calendar_bookings",
    ):
        op.execute(f"""
            CREATE TRIGGER trg_{table}_ghl
            AFTER INSERT OR UPDATE ON {table}
            FOR EACH ROW EXECUTE FUNCTION ghl_capture_change()
        """)


def downgrade() -> None:
    for table in (
        "calendar_bookings",
        "hvac_appointments",
        "hvac_service_requests",
        "lead_handoff_requests",
        "agency_leads",
    ):
        op.execute(f"DROP TRIGGER trg_{table}_ghl ON {table}")
    op.execute("DROP FUNCTION ghl_capture_change()")
    op.execute("DROP FUNCTION ghl_touch_request(uuid, uuid)")
    op.execute("DROP FUNCTION ghl_touch_lead(uuid, uuid, boolean)")
    op.drop_table("ghl_deliveries")
    op.drop_table("ghl_connections")
    op.drop_constraint("uq_agency_leads_agency_id", "agency_leads", type_="unique")
