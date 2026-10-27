from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from insurance_operations.database.models.booking_integrations import (
    CalendarBooking,
    CalendarConnection,
)
from insurance_operations.database.models.hvac import Appointment
from insurance_operations.errors import ApiError
from insurance_operations.hvac.calendar import (
    CalendarAuthorizationRequired,
    CalendarConflict,
    CalendarUnavailable,
)
from insurance_operations.hvac.google_connection import calendar_adapter
from insurance_operations.telephony.phone_service import system_audit


def connection_for_team(
    session: Session, agency_id: UUID, team_key: str
) -> CalendarConnection | None:
    return session.scalar(
        select(CalendarConnection).where(
            CalendarConnection.agency_id == agency_id,
            CalendarConnection.team_key == team_key,
        )
    )


def calendar_error(error: CalendarUnavailable) -> ApiError:
    return ApiError(
        status_code=409,
        code="CALENDAR_CONFLICT"
        if isinstance(error, CalendarConflict)
        else "CALENDAR_UNAVAILABLE",
        message=(
            "That time conflicts with the connected calendar. "
            "Choose another time or contact staff."
        )
        if isinstance(error, CalendarConflict)
        else "The connected calendar could not be verified. Retry or request a callback.",
    )


def check_external_slot(
    session: Session,
    agency_id: UUID,
    team_key: str,
    starts_at: datetime,
    ends_at: datetime,
    replace_id: UUID | None = None,
) -> None:
    connection = connection_for_team(session, agency_id, team_key)
    if connection is None:
        return
    try:
        with calendar_adapter(session, connection) as adapter:
            excluded: frozenset[str] = frozenset()
            if replace_id:
                previous = session.get(Appointment, replace_id)
                binding = session.get(CalendarBooking, replace_id)
                if previous and binding and binding.connection_id == connection.id:
                    adapter.verify(previous.id, previous.starts_at, previous.ends_at)
                    excluded = frozenset({replace_id.hex})
            if adapter.busy_events(starts_at, ends_at, excluded):
                raise CalendarConflict("External calendar conflict")
    except CalendarUnavailable as error:
        raise calendar_error(error) from error


def bind_reservation(session: Session, row: Appointment) -> None:
    connection = connection_for_team(session, row.agency_id, row.team_key)
    if connection:
        session.add(
            CalendarBooking(
                appointment_id=row.id,
                agency_id=row.agency_id,
                connection_id=connection.id,
                status="PENDING",
                next_attempt_at=datetime.now(UTC),
            )
        )


def publish_confirmation(
    session: Session, row: Appointment, replace_id: UUID | None = None
) -> None:
    binding = session.get(CalendarBooking, row.id)
    if binding is None:
        return
    connection = session.get(CalendarConnection, binding.connection_id)
    if connection is None or connection.agency_id != row.agency_id:
        raise calendar_error(CalendarUnavailable("Calendar binding is unavailable"))
    try:
        with calendar_adapter(session, connection) as adapter:
            excluded = {row.id.hex}
            existing = adapter.event(row.id)
            if existing is not None:
                adapter.verify(row.id, row.starts_at, row.ends_at)
            if replace_id:
                previous = session.get(Appointment, replace_id)
                previous_binding = session.get(CalendarBooking, replace_id)
                if (
                    previous
                    and previous_binding
                    and previous_binding.connection_id == connection.id
                ):
                    adapter.verify(previous.id, previous.starts_at, previous.ends_at)
                    excluded.add(replace_id.hex)
            if adapter.busy_events(row.starts_at, row.ends_at, frozenset(excluded)):
                raise CalendarConflict("External calendar conflict")
            adapter.publish(row.id, row.starts_at, row.ends_at)
            adapter.verify(row.id, row.starts_at, row.ends_at)
            if adapter.busy_events(row.starts_at, row.ends_at, frozenset(excluded)):
                raise CalendarConflict("External calendar changed during confirmation")
        binding.status = "SYNCED"
        binding.last_error = None
        binding.next_attempt_at = datetime.now(UTC) + timedelta(seconds=60)
        connection.last_checked_at = datetime.now(UTC)
        connection.last_error = None
    except CalendarUnavailable as error:
        raise calendar_error(error) from error


def request_cleanup(session: Session, row: Appointment) -> None:
    binding = session.get(CalendarBooking, row.id)
    if binding:
        binding.next_attempt_at = datetime.now(UTC)


def reconcile_connection(session: Session, connection: CalendarConnection) -> None:
    now = datetime.now(UTC)
    try:
        with calendar_adapter(session, connection) as adapter:
            adapter.busy_events(now, now + timedelta(minutes=1))
        connection.last_error = None
    except CalendarAuthorizationRequired:
        connection.status = "REAUTH_REQUIRED"
        connection.last_error = "REAUTH_REQUIRED"
    except CalendarUnavailable:
        connection.last_error = "CALENDAR_UNAVAILABLE"
    connection.last_checked_at = now


def reconcile_booking(
    session: Session, row: Appointment, binding: CalendarBooking
) -> None:
    now = datetime.now(UTC)
    previous = (binding.status, binding.last_error)
    if row.status == "HELD" and row.hold_expires_at > now:
        binding.next_attempt_at = row.hold_expires_at
        return
    if row.status == "CONFIRMED" and row.ends_at <= now:
        binding.status = "COMPLETED"
        return
    connection = session.get(CalendarConnection, binding.connection_id)
    if connection is None or connection.agency_id != row.agency_id:
        raise CalendarUnavailable("Calendar connection is unavailable")
    try:
        with calendar_adapter(session, connection) as adapter:
            if row.status in {"CANCELLED", "EXPIRED"} or (
                row.status == "HELD" and row.hold_expires_at <= now
            ):
                adapter.cancel_owned(row.id, row.starts_at, row.ends_at)
                binding.status = "CANCELLED"
                if row.status == "HELD":
                    row.status = "EXPIRED"
            elif row.status == "CONFIRMED":
                adapter.verify(row.id, row.starts_at, row.ends_at)
                if adapter.busy_events(
                    row.starts_at, row.ends_at, frozenset({row.id.hex})
                ):
                    raise CalendarConflict("External calendar overlaps this booking")
                binding.status = "COMPLETED" if row.ends_at <= now else "SYNCED"
            binding.last_error = None
            connection.last_checked_at = now
            connection.last_error = None
    except CalendarAuthorizationRequired:
        connection.status = "REAUTH_REQUIRED"
        connection.last_error = "REAUTH_REQUIRED"
        binding.last_error = "REAUTH_REQUIRED"
    except CalendarConflict:
        binding.status = "ATTENTION"
        binding.last_error = "CALENDAR_CONFLICT"
    except CalendarUnavailable:
        binding.last_error = "CALENDAR_UNAVAILABLE"
        connection.last_error = "CALENDAR_UNAVAILABLE"
    binding.next_attempt_at = now + timedelta(seconds=60)
    if previous != (binding.status, binding.last_error):
        session.add(
            system_audit(
                agency_id=row.agency_id,
                event_type="HVAC_CALENDAR_RECONCILED",
                summary="Appointment calendar synchronization updated",
                details={
                    "appointment_id": str(row.id),
                    "status": binding.status,
                    "error": binding.last_error,
                },
                correlation_id=uuid4(),
            )
        )
