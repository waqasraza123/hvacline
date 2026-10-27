from collections.abc import Sequence
from uuid import UUID

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261027_0012"
down_revision: str | None = "20261025_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def identity() -> sa.Column[UUID]:
    return sa.Column(
        "id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")
    )


def agency() -> sa.Column[UUID]:
    return sa.Column(
        "agency_id",
        sa.Uuid(),
        sa.ForeignKey("agencies.id", ondelete="RESTRICT"),
        nullable=False,
    )


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_hvac_appointments_agency_id", "hvac_appointments", ["agency_id", "id"]
    )
    op.create_table(
        "calendar_connections",
        identity(),
        agency(),
        sa.Column("team_key", sa.Text(), nullable=False),
        sa.Column("calendar_id", sa.Text(), nullable=False),
        sa.Column("refresh_token_ciphertext", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("last_checked_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text()),
        sa.UniqueConstraint(
            "agency_id", "team_key", name="uq_calendar_connections_team"
        ),
        sa.UniqueConstraint(
            "agency_id", "id", name="uq_calendar_connections_agency_id"
        ),
        sa.UniqueConstraint(
            "agency_id", "calendar_id", name="uq_calendar_connections_calendar"
        ),
        sa.CheckConstraint(
            "status IN ('CONNECTED', 'REAUTH_REQUIRED', 'DISCONNECTED')",
            name="status_valid",
        ),
    )
    op.create_table(
        "calendar_authorizations",
        identity(),
        agency(),
        sa.Column(
            "actor_id",
            sa.Uuid(),
            sa.ForeignKey("app_users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("state_digest", sa.Text(), unique=True, nullable=False),
        sa.Column("browser_digest", sa.Text(), nullable=False),
        sa.Column("verifier_ciphertext", sa.Text(), nullable=False),
        sa.Column("team_key", sa.Text(), nullable=False),
        sa.Column("calendar_id", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "calendar_bookings",
        sa.Column("appointment_id", sa.Uuid(), primary_key=True),
        agency(),
        sa.Column("connection_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_error", sa.Text()),
        sa.ForeignKeyConstraint(
            ["agency_id", "appointment_id"],
            ["hvac_appointments.agency_id", "hvac_appointments.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["agency_id", "connection_id"],
            ["calendar_connections.agency_id", "calendar_connections.id"],
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "status IN ('PENDING', 'SYNCED', 'ATTENTION', 'CANCELLED', 'COMPLETED')",
            name="status_valid",
        ),
    )
    op.create_index(
        "ix_calendar_bookings_agency_id", "calendar_bookings", ["agency_id"]
    )
    op.create_index(
        "ix_calendar_bookings_next_attempt_at", "calendar_bookings", ["next_attempt_at"]
    )
    op.create_table(
        "booking_notifications",
        identity(),
        agency(),
        sa.Column("appointment_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("first_attempt_at", sa.DateTime(timezone=True)),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("provider_reference", sa.Text()),
        sa.Column("last_error", sa.Text()),
        sa.Column("delivery_status", sa.Text()),
        sa.ForeignKeyConstraint(
            ["agency_id", "appointment_id"],
            ["hvac_appointments.agency_id", "hvac_appointments.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "appointment_id", "kind", name="uq_booking_notifications_kind"
        ),
        sa.CheckConstraint(
            "kind IN ('CONFIRMATION', 'REMINDER', 'CANCELLATION', 'RESCHEDULED')",
            name="kind_valid",
        ),
        sa.CheckConstraint(
            "status IN ('PENDING', 'ACCEPTED', 'SKIPPED', 'FAILED', 'UNKNOWN')",
            name="status_valid",
        ),
        sa.CheckConstraint("attempts >= 0", name="attempts_valid"),
    )
    op.create_index(
        "ix_booking_notifications_agency_id", "booking_notifications", ["agency_id"]
    )
    op.create_index(
        "ix_booking_notifications_due_at", "booking_notifications", ["due_at"]
    )
    op.create_table(
        "booking_email_events",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("provider_reference", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_booking_email_events_provider_reference",
        "booking_email_events",
        ["provider_reference"],
    )


def downgrade() -> None:
    for table in (
        "booking_email_events",
        "booking_notifications",
        "calendar_bookings",
        "calendar_authorizations",
        "calendar_connections",
    ):
        op.drop_table(table)
    op.drop_constraint(
        "uq_hvac_appointments_agency_id", "hvac_appointments", type_="unique"
    )
