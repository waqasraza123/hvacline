import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import partial
from itertools import zip_longest
from typing import Literal
from uuid import UUID

from sqlalchemy import delete, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

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
from insurance_operations.job_execution import (
    JobDeadlineExceeded,
    check_job_deadline,
    job_budget,
)
from insurance_operations.notifications.booking import deliver_notification
from insurance_operations.notifications.email_events import apply_delivery_events

# Shared by HTTP invocations and the standalone worker in this database.
JOB_LOCK_NAME = "hvacline.booking-jobs"


@dataclass
class JobBatchResult:
    status: Literal["completed", "busy", "deferred"] = "completed"
    processed: int = 0
    failed: int = 0


def reconcile_connection_job(
    sessions: sessionmaker[Session], connection_id: UUID, agency_id: UUID
) -> None:
    with sessions() as session, session.begin():
        schedule = lock_business_schedule(session, agency_id, skip_locked=True)
        if schedule is None:
            return
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


def reconcile_booking_job(
    sessions: sessionmaker[Session], appointment_id: UUID, agency_id: UUID
) -> None:
    with sessions() as session, session.begin():
        schedule = lock_business_schedule(session, agency_id, skip_locked=True)
        if schedule is None:
            return
        binding = session.get(CalendarBooking, appointment_id)
        appointment = session.get(Appointment, appointment_id)
        if (
            binding
            and appointment
            and binding.status not in {"CANCELLED", "COMPLETED"}
            and binding.next_attempt_at <= datetime.now(UTC)
        ):
            reconcile_booking(session, appointment, binding)


def collect_booking_jobs(
    sessions: sessionmaker[Session], batch_size: int
) -> list[Callable[[], None]]:
    now = datetime.now(UTC)
    with sessions() as session, session.begin():
        expired = (
            select(CalendarAuthorization.id)
            .where(CalendarAuthorization.expires_at <= now)
            .limit(batch_size)
        )
        session.execute(
            delete(CalendarAuthorization).where(CalendarAuthorization.id.in_(expired))
        )
        apply_delivery_events(session)
        bindings = list(
            session.execute(
                select(CalendarBooking.appointment_id, CalendarBooking.agency_id)
                .where(
                    CalendarBooking.status.not_in(["CANCELLED", "COMPLETED"]),
                    CalendarBooking.next_attempt_at <= now,
                )
                .order_by(CalendarBooking.next_attempt_at, CalendarBooking.appointment_id)
                .limit(batch_size)
            ).all()
        )
        notifications = list(
            session.scalars(
                select(BookingNotification.id)
                .where(
                    BookingNotification.status == "PENDING",
                    BookingNotification.due_at <= now,
                )
                .order_by(BookingNotification.due_at, BookingNotification.id)
                .limit(batch_size)
            )
        )
        connections = list(
            session.execute(
                select(CalendarConnection.id, CalendarConnection.agency_id)
                .where(
                    CalendarConnection.status == "CONNECTED",
                    CalendarConnection.last_checked_at.is_(None)
                    | (CalendarConnection.last_checked_at <= now - timedelta(minutes=5)),
                )
                .order_by(
                    CalendarConnection.last_checked_at.nulls_first(),
                    CalendarConnection.id,
                )
                .limit(batch_size)
            ).all()
        )
    jobs: list[Callable[[], None]] = []
    for notification, binding, connection in zip_longest(
        notifications, bindings, connections
    ):
        if notification is not None:
            jobs.append(partial(deliver_notification, sessions, notification))
        if binding is not None:
            jobs.append(partial(reconcile_booking_job, sessions, binding[0], binding[1]))
        if connection is not None:
            jobs.append(
                partial(reconcile_connection_job, sessions, connection[0], connection[1])
            )
    return jobs


def process_booking_jobs(
    sessions: sessionmaker[Session], *, seconds: float = 20, batch_size: int = 12
) -> JobBatchResult:
    if not 0 < seconds <= 20 or not 1 <= batch_size <= 50:
        raise ValueError("Invalid booking job batch limits")
    result = JobBatchResult()
    logger = logging.getLogger(__name__)
    try:
        with job_budget(seconds), sessions() as guard, guard.begin():
            acquired = guard.scalar(
                text("SELECT pg_try_advisory_xact_lock(hashtextextended(:name, 0))"),
                {"name": JOB_LOCK_NAME},
            )
            if not acquired:
                result.status = "busy"
                return result
            for job in collect_booking_jobs(sessions, batch_size):
                check_job_deadline()
                try:
                    job()
                    result.processed += 1
                except (SQLAlchemyError, RuntimeError):
                    result.failed += 1
                    logger.error("booking job failed; durable work retained for retry")
            check_job_deadline()
    except JobDeadlineExceeded:
        result.status = "deferred"
    return result
