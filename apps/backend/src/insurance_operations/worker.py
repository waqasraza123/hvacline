import argparse
import json
import logging
import signal
from datetime import UTC, datetime, timedelta
from threading import Event
from types import FrameType

from pydantic import ValidationError
from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.database.connection import (
    DatabaseReadinessError,
    check_database_readiness,
    create_database_engine,
)
from insurance_operations.database.models.booking_integrations import (
    BookingNotification,
    CalendarAuthorization,
    CalendarBooking,
    CalendarConnection,
)
from insurance_operations.database.models.hvac import Appointment
from insurance_operations.hvac.calendar_sync import (
    reconcile_booking,
    reconcile_connection,
)
from insurance_operations.hvac.locking import lock_business_schedule
from insurance_operations.notifications.booking import deliver_notification
from insurance_operations.notifications.email_events import apply_delivery_events
from insurance_operations.settings import WorkerSettings


def process_booking_jobs(sessions: sessionmaker[Session]) -> None:
    logger = logging.getLogger(__name__)
    now = datetime.now(UTC)
    with sessions() as session, session.begin():
        session.execute(
            delete(CalendarAuthorization).where(CalendarAuthorization.expires_at <= now)
        )
        bindings = list(
            session.execute(
                select(CalendarBooking.appointment_id, CalendarBooking.agency_id)
                .where(
                    CalendarBooking.status.not_in(["CANCELLED", "COMPLETED"]),
                    CalendarBooking.next_attempt_at <= now,
                )
                .order_by(CalendarBooking.next_attempt_at)
                .limit(20)
            ).all()
        )
        notifications = list(
            session.scalars(
                select(BookingNotification.id)
                .where(
                    BookingNotification.status == "PENDING",
                    BookingNotification.due_at <= now,
                )
                .order_by(BookingNotification.due_at)
                .limit(20)
            )
        )
        apply_delivery_events(session)
        connections = list(
            session.execute(
                select(CalendarConnection.id, CalendarConnection.agency_id)
                .where(
                    CalendarConnection.status == "CONNECTED",
                    CalendarConnection.last_checked_at.is_(None)
                    | (
                        CalendarConnection.last_checked_at <= now - timedelta(minutes=5)
                    ),
                )
                .order_by(CalendarConnection.last_checked_at.nulls_first())
                .limit(10)
            ).all()
        )
    for connection_id, agency_id in connections:
        try:
            with sessions() as session, session.begin():
                schedule = lock_business_schedule(session, agency_id, skip_locked=True)
                if schedule is None:
                    continue
                connection = session.get(CalendarConnection, connection_id)
                if (
                    connection
                    and connection.status == "CONNECTED"
                    and (
                        connection.last_checked_at is None
                        or connection.last_checked_at
                        <= datetime.now(UTC) - timedelta(minutes=5)
                    )
                ):
                    reconcile_connection(session, connection)
        except (SQLAlchemyError, RuntimeError):
            logger.error(
                "calendar connection refresh failed; retrying on next interval"
            )
    for appointment_id, agency_id in bindings:
        try:
            with sessions() as session, session.begin():
                schedule = lock_business_schedule(session, agency_id, skip_locked=True)
                if schedule is None:
                    continue
                binding = session.get(CalendarBooking, appointment_id)
                appointment = session.get(Appointment, appointment_id)
                if (
                    binding
                    and appointment
                    and binding.next_attempt_at <= datetime.now(UTC)
                ):
                    reconcile_booking(session, appointment, binding)
        except (SQLAlchemyError, RuntimeError):
            logger.error("calendar reconciliation failed; durable job retained")
    for notification_id in notifications:
        try:
            deliver_notification(sessions, notification_id)
        except (SQLAlchemyError, RuntimeError):
            logger.error("booking notification failed; durable job retained")


def readiness(settings: WorkerSettings) -> dict[str, str]:
    database_engine = create_database_engine(
        settings, service_name=settings.worker_name
    )
    try:
        check_database_readiness(database_engine)
    finally:
        database_engine.dispose()

    return {
        "status": "ready",
        "service": "worker",
        "environment": settings.app_environment,
        "worker": settings.worker_name,
        "database": "ready",
    }


def run(settings: WorkerSettings) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    logger = logging.getLogger(__name__)
    stopped = Event()
    database_engine = create_database_engine(
        settings, service_name=settings.worker_name
    )

    def request_shutdown(signum: int, frame: FrameType | None) -> None:
        del signum, frame
        stopped.set()

    signal.signal(signal.SIGINT, request_shutdown)
    signal.signal(signal.SIGTERM, request_shutdown)
    try:
        check_database_readiness(database_engine)
        logger.info("worker ready: %s", settings.worker_name)
        sessions = sessionmaker(
            bind=database_engine,
            expire_on_commit=False,
            info={"integration_settings": settings},
        )
        while not stopped.is_set():
            try:
                process_booking_jobs(sessions)
            except SQLAlchemyError:
                logger.error("booking job polling failed; retrying on next interval")
            stopped.wait(settings.worker_poll_seconds)
        logger.info("worker stopped: %s", settings.worker_name)
    finally:
        database_engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(prog="insurance-operations-worker")
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate configuration and exit",
    )
    arguments = parser.parse_args()

    try:
        settings = WorkerSettings()
    except ValidationError as error:
        parser.exit(2, f"configuration error:\n{error}\n")

    try:
        if arguments.check:
            result = readiness(settings)
            print(json.dumps(result, sort_keys=True))
            return

        run(settings)
    except (DatabaseReadinessError, SQLAlchemyError):
        parser.exit(1, "readiness error: database unavailable\n")


if __name__ == "__main__":
    main()
