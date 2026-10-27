from datetime import UTC, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.database.models.booking_integrations import (
    BookingNotification,
    CalendarBooking,
)
from insurance_operations.database.models.hvac import (
    Appointment,
    BusinessSchedule,
    HvacServiceRequest,
)
from insurance_operations.hvac.calendar_sync import reconcile_booking
from insurance_operations.hvac.google_connection import integration_settings
from insurance_operations.hvac.locking import lock_business_schedule
from insurance_operations.hvac.schemas import ScheduleInput
from insurance_operations.settings import DatabaseSettings


def enqueue_booking_notifications(
    session: Session, appointment: Appointment, kind: str = "CONFIRMATION"
) -> None:
    request = session.get(HvacServiceRequest, appointment.service_request_id)
    schedule = session.get(BusinessSchedule, appointment.agency_id)
    if request is None or schedule is None:
        raise RuntimeError("Booking notification context is unavailable")
    configuration = ScheduleInput.model_validate(schedule.configuration)
    settings = session.info.get("integration_settings")
    reminder_hours = (
        settings.booking_reminder_hours
        if isinstance(settings, DatabaseSettings)
        else 24
    )
    now = datetime.now(UTC)
    local = appointment.starts_at.astimezone(ZoneInfo(configuration.timezone))
    subject = {
        "CONFIRMATION": "Your HVAC appointment is confirmed",
        "REMINDER": "Reminder: your HVAC appointment",
        "CANCELLATION": "Your HVAC appointment was cancelled",
        "RESCHEDULED": "Your HVAC appointment was rescheduled",
    }
    recipient = request.customer_details.get("email")
    sender = (
        settings.booking_email_from if isinstance(settings, DatabaseSettings) else None
    )

    def add(notification_kind: str, due_at: datetime) -> None:
        existing = session.scalar(
            select(BookingNotification.id).where(
                BookingNotification.appointment_id == appointment.id,
                BookingNotification.kind == notification_kind,
            )
        )
        if existing:
            return
        text = (
            subject[notification_kind]
            + ".\n\n"
            + local.strftime("%A, %B %d, %Y at %I:%M %p")
            + " ("
            + configuration.timezone
            + ").\n"
            + "Booking reference: "
            + str(appointment.id)
            + ".\n"
            + "Contact the service business for changes or questions."
        )
        session.add(
            BookingNotification(
                agency_id=appointment.agency_id,
                appointment_id=appointment.id,
                kind=notification_kind,
                status="PENDING" if recipient and sender else "SKIPPED",
                due_at=due_at,
                attempts=0,
                payload={
                    "from": sender,
                    "to": [recipient],
                    "subject": subject[notification_kind],
                    "text": text,
                },
                last_error=None
                if recipient and sender
                else "NO_EMAIL"
                if not recipient
                else "EMAIL_NOT_CONFIGURED",
            )
        )

    add(kind, now)
    if (
        kind != "CANCELLATION"
        and appointment.starts_at - timedelta(hours=reminder_hours) > now
    ):
        add("REMINDER", appointment.starts_at - timedelta(hours=reminder_hours))


def suppress_booking_notifications(session: Session, appointment_id: UUID) -> None:
    for row in session.scalars(
        select(BookingNotification).where(
            BookingNotification.appointment_id == appointment_id,
            BookingNotification.status == "PENDING",
        )
    ):
        row.status = "SKIPPED"
        row.last_error = "BOOKING_CHANGED"


class ResendBookingEmail:
    def __init__(self, settings: DatabaseSettings, client: httpx.Client) -> None:
        self.settings = settings
        self.client = client

    def send(self, row: BookingNotification) -> tuple[str, str | None]:
        key = self.settings.resend_api_key
        if key is None:
            return "FAILED", "EMAIL_NOT_CONFIGURED"
        try:
            response = self.client.post(
                "https://api.resend.com/emails",
                json=row.payload,
                headers={
                    "Authorization": "Bearer " + key.get_secret_value(),
                    "Idempotency-Key": "hvacline-booking-" + str(row.id),
                },
                timeout=10,
            )
            if response.status_code == 409:
                data = response.json()
                if (
                    isinstance(data, dict)
                    and data.get("name") == "concurrent_idempotent_requests"
                ):
                    return "PENDING", "EMAIL_RETRY"
                return "FAILED", "EMAIL_IDEMPOTENCY_CONFLICT"
            if response.status_code in {400, 401, 403, 404, 422}:
                return "FAILED", "EMAIL_REJECTED"
            if response.status_code == 429 or response.status_code >= 500:
                return "PENDING", "EMAIL_RETRY"
            response.raise_for_status()
            data = response.json()
            if (
                not isinstance(data, dict)
                or not isinstance(data.get("id"), str)
                or not data["id"]
            ):
                return "PENDING", "EMAIL_RESPONSE_UNKNOWN"
            return "ACCEPTED", str(data["id"])
        except (httpx.HTTPError, ValueError):
            return "PENDING", "EMAIL_RESPONSE_UNKNOWN"


def deliver_notification(
    sessions: sessionmaker[Session], notification_id: UUID
) -> None:
    with sessions() as session:
        candidate = session.get(BookingNotification, notification_id)
        if candidate is None:
            return
        agency_id = candidate.agency_id
    # Persist the first attempt before contacting a provider with a bounded deduplication window.
    with sessions() as session, session.begin():
        lock_business_schedule(session, agency_id)
        row = session.scalar(
            select(BookingNotification)
            .where(BookingNotification.id == notification_id)
            .with_for_update()
        )
        if row is None or row.status != "PENDING" or row.due_at > datetime.now(UTC):
            return
        settings = integration_settings(session)
        if not settings.booking_email_enabled:
            row.last_error = "EMAIL_DISABLED"
            row.due_at = datetime.now(UTC) + timedelta(minutes=5)
            return
        if not ready_for_delivery(session, row):
            return
        if row.first_attempt_at is None:
            row.first_attempt_at = datetime.now(UTC)
    with sessions() as session, session.begin():
        lock_business_schedule(session, agency_id)
        row = session.scalar(
            select(BookingNotification)
            .where(BookingNotification.id == notification_id)
            .with_for_update()
        )
        now = datetime.now(UTC)
        if row is None or row.status != "PENDING" or row.due_at > now:
            return
        if not ready_for_delivery(session, row):
            return
        row.attempts += 1
        with httpx.Client() as client:
            outcome, detail = ResendBookingEmail(
                integration_settings(session), client
            ).send(row)
        row.status = outcome
        if outcome == "ACCEPTED":
            row.provider_reference, row.last_error = detail, None
        else:
            row.last_error = detail
            row.due_at = now + timedelta(
                seconds=min(3600, 30 * 2 ** min(row.attempts, 7))
            )


def ready_for_delivery(session: Session, row: BookingNotification) -> bool:
    now = datetime.now(UTC)
    appointment = session.get(Appointment, row.appointment_id)
    if appointment is None or appointment.agency_id != row.agency_id:
        row.status, row.last_error = "FAILED", "BOOKING_NOT_FOUND"
        return False
    cancellation = row.kind == "CANCELLATION"
    service_request = session.get(HvacServiceRequest, appointment.service_request_id)
    if (
        not cancellation
        and service_request
        and service_request.service_details.get("hazardous_condition")
    ):
        row.status, row.last_error = "SKIPPED", "HUMAN_ATTENTION_REQUIRED"
        return False
    if (cancellation and appointment.status != "CANCELLED") or (
        not cancellation
        and (appointment.status != "CONFIRMED" or appointment.starts_at <= now)
    ):
        row.status, row.last_error = "SKIPPED", "BOOKING_CHANGED"
        return False
    binding = session.get(CalendarBooking, appointment.id)
    if binding:
        reconcile_booking(session, appointment, binding)
        if (
            not cancellation and (binding.status != "SYNCED" or binding.last_error)
        ) or (cancellation and binding.status != "CANCELLED"):
            row.last_error = "CALENDAR_NOT_SYNCED"
            row.due_at = now + timedelta(minutes=1)
            return False
    if row.kind == "REMINDER":
        receipt = session.scalar(
            select(BookingNotification).where(
                BookingNotification.appointment_id == appointment.id,
                BookingNotification.kind.in_(["CONFIRMATION", "RESCHEDULED"]),
            )
        )
        if receipt and receipt.delivery_status in {
            "FAILED",
            "SUPPRESSED",
            "BOUNCED",
            "COMPLAINED",
        }:
            row.status, row.last_error = "SKIPPED", "CONFIRMATION_DELIVERY_FAILED"
            return False
        if (
            receipt is None
            or receipt.status != "ACCEPTED"
            or receipt.delivery_status != "DELIVERED"
        ):
            row.last_error = "CONFIRMATION_NOT_ACCEPTED"
            row.due_at = now + timedelta(minutes=5)
            return False
    if row.first_attempt_at and now - row.first_attempt_at >= timedelta(hours=23):
        row.status, row.last_error = "UNKNOWN", "PROVIDER_DEDUPLICATION_WINDOW_EXPIRED"
        return False
    return True
