"""Optional GHL calendar routing and durable voice delivery outcomes."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "20261118_0025"
down_revision = "20261113_0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ghl_connections",
        sa.Column(
            "voice_configuration",
            JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "ghl_connections",
        sa.Column("voice_version", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("ghl_deliveries", sa.Column("note_id", sa.Text()))
    op.add_column(
        "ghl_deliveries",
        sa.Column("note_unknown", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_table(
        "ghl_calendar_bookings",
        sa.Column("appointment_id", sa.Uuid(), primary_key=True),
        sa.Column(
            "agency_id",
            sa.Uuid(),
            sa.ForeignKey("agencies.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("connection_id", sa.Uuid(), nullable=False),
        sa.Column("calendar_id", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="RESERVED"),
        sa.Column("contact_id", sa.Text()),
        sa.Column(
            "contact_unknown", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column("event_id", sa.Text()),
        sa.Column("last_error", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("clock_timestamp()"),
        ),
        sa.ForeignKeyConstraint(
            ["agency_id", "connection_id"],
            ["ghl_connections.agency_id", "ghl_connections.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["agency_id", "appointment_id"],
            ["hvac_appointments.agency_id", "hvac_appointments.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "connection_id", "event_id", name="uq_ghl_calendar_bookings_event"
        ),
        sa.CheckConstraint(
            "status IN ('RESERVED', 'CONTACT_PENDING', 'CREATING', 'UNKNOWN', 'CONFIRMED', 'NEEDS_REVIEW', 'RELEASED')",
            name="status_valid",
        ),
        sa.CheckConstraint(
            "status <> 'CONFIRMED' OR (event_id IS NOT NULL AND contact_id IS NOT NULL AND NOT contact_unknown)",
            name="confirmation_valid",
        ),
    )
    op.create_index(
        "ix_ghl_calendar_bookings_agency_created",
        "ghl_calendar_bookings",
        ["agency_id", "created_at"],
    )


def downgrade() -> None:
    op.execute("""
        DO $$ BEGIN
          IF EXISTS (SELECT 1 FROM ghl_calendar_bookings WHERE status <> 'RELEASED')
             OR EXISTS (SELECT 1 FROM ghl_deliveries WHERE note_id IS NOT NULL OR note_unknown)
          THEN RAISE EXCEPTION 'Reconcile GHL bookings and summary deliveries before downgrade';
          END IF;
        END $$;
    """)
    op.drop_table("ghl_calendar_bookings")
    op.drop_column("ghl_deliveries", "note_unknown")
    op.drop_column("ghl_deliveries", "note_id")
    op.drop_column("ghl_connections", "voice_version")
    op.drop_column("ghl_connections", "voice_configuration")
