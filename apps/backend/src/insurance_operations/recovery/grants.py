import hashlib
import hmac
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Iterator
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from insurance_operations.database.models.hvac import Appointment, HvacServiceRequest
from insurance_operations.database.models.recovery import RecoveryAttempt, RecoveryCase, RecoveryGrant
from insurance_operations.errors import ApiError
from insurance_operations.recovery.domain import TERMINAL, channel_allowed, destination_digest, permission_rows, request_block, pending_opt_out
from insurance_operations.settings import DatabaseSettings


def unavailable() -> ApiError:
    return ApiError(status_code=403, code="RECOVERY_CONTINUATION_UNAVAILABLE",
        message="This recovery session is unavailable or expired. Contact the business for scheduling help.",
        headers={"Cache-Control": "no-store"})


def grant_token(settings: DatabaseSettings, grant: RecoveryGrant) -> str:
    secret = settings.recovery_token_encryption_key
    if secret is None:
        raise unavailable()
    content = f"recovery-booking-v1:{grant.id}:{grant.agency_id}:{grant.attempt_id}:{grant.channel}:{int(grant.expires_at.timestamp())}"
    digest = hmac.new(secret.get_secret_value().encode(), content.encode(), hashlib.sha256).hexdigest()
    return f"{grant.id.hex}.{digest}"


def authenticate(session: Session, settings: DatabaseSettings, token: str, *, lock: bool = False) -> RecoveryGrant:
    try:
        identifier, signature = token.split(".", 1)
        if len(identifier) != 32 or len(signature) != 64:
            raise ValueError
        query = select(RecoveryGrant).where(RecoveryGrant.id == UUID(hex=identifier))
        grant = session.scalar(query.with_for_update() if lock else query)
    except (ValueError, TypeError):
        raise unavailable() from None
    if grant is None or not hmac.compare_digest(grant_token(settings, grant), token) or grant.expires_at <= datetime.now(UTC) or grant.status in {"REVOKED", "EXPIRED"}:
        raise unavailable()
    return grant


def scope(session: Session, settings: DatabaseSettings, grant: RecoveryGrant, *, allow_consumed: bool = False) -> tuple[RecoveryCase, RecoveryAttempt, HvacServiceRequest]:
    case = session.scalar(select(RecoveryCase).where(RecoveryCase.agency_id == grant.agency_id, RecoveryCase.id == grant.recovery_case_id).with_for_update())
    attempt = session.scalar(select(RecoveryAttempt).where(RecoveryAttempt.agency_id == grant.agency_id, RecoveryAttempt.id == grant.attempt_id))
    request = session.scalar(select(HvacServiceRequest).where(HvacServiceRequest.agency_id == grant.agency_id, HvacServiceRequest.id == case.service_request_id)) if case else None
    if case is None or attempt is None or request is None or attempt.recovery_case_id != case.id:
        raise unavailable()
    if allow_consumed and grant.status == "CONSUMED" and case.status == "RECOVERED" and case.recovered_appointment_id == grant.appointment_id:
        return case, attempt, request
    if grant.status not in {"WAITING", "ACTIVE"} or grant.expires_at <= datetime.now(UTC) or case.status in TERMINAL or request_block(session, request):
        raise unavailable()
    if not channel_allowed(permission_rows(session, settings, request), grant.channel):
        raise unavailable()
    if attempt.recipient_digest != destination_digest(settings, case.agency_id, str(request.customer_details.get("phone") or "")):
        raise unavailable()
    if pending_opt_out(session, case.agency_id, attempt.recipient_digest):
        raise unavailable()
    if attempt.status not in {"STARTED", "QUEUED", "SENT", "DELIVERED"} or not attempt.provider_reference:
        raise unavailable()
    return case, attempt, request


def create_grant(session: Session, attempt: RecoveryAttempt, *, active: bool, expires_at: datetime, reply_due_at: datetime | None = None) -> RecoveryGrant:
    existing = session.scalar(select(RecoveryGrant).where(RecoveryGrant.agency_id == attempt.agency_id, RecoveryGrant.attempt_id == attempt.id))
    if existing:
        return existing
    grant = RecoveryGrant(id=uuid4(), agency_id=attempt.agency_id, attempt_id=attempt.id, recovery_case_id=attempt.recovery_case_id,
        channel=attempt.channel, status="ACTIVE" if active else "WAITING", expires_at=expires_at,
        reply_status="PENDING" if reply_due_at else None, reply_due_at=reply_due_at)
    session.add(grant)
    session.flush()
    return grant


def revoke_case_grants(session: Session, case: RecoveryCase) -> None:
    for grant in session.scalars(select(RecoveryGrant).where(RecoveryGrant.agency_id == case.agency_id,
        RecoveryGrant.recovery_case_id == case.id, RecoveryGrant.status.in_(["WAITING", "ACTIVE"])).with_for_update()):
        grant.status = "REVOKED"
        if grant.reply_status == "PENDING":
            grant.reply_status = "CANCELLED"


@dataclass(frozen=True)
class BookingScope:
    grant_id: UUID
    expected_version: int


current_recovery_booking: ContextVar[BookingScope | None] = ContextVar("recovery_booking", default=None)


@contextmanager
def booking_scope(grant: RecoveryGrant) -> Iterator[None]:
    token = current_recovery_booking.set(BookingScope(grant.id, grant.row_version))
    try:
        yield
    finally:
        current_recovery_booking.reset(token)


def bind_reservation(session: Session, appointment: Appointment) -> None:
    context = current_recovery_booking.get()
    if context is None:
        return
    settings = session.info.get("integration_settings")
    grant = session.get(RecoveryGrant, context.grant_id, with_for_update=True)
    if grant is None or not isinstance(settings, DatabaseSettings):
        raise unavailable()
    if grant.row_version != context.expected_version:
        raise ApiError(status_code=409, code="RECOVERY_SESSION_CHANGED", message="The recovery session changed. Refresh saved status before reserving again.")
    case, _, request = scope(session, settings, grant)
    if grant.status != "ACTIVE" or request.id != appointment.service_request_id or grant.agency_id != appointment.agency_id or grant.approved_at:
        raise unavailable()
    if grant.appointment_id and grant.appointment_id != appointment.id:
        raise ApiError(status_code=409, code="RECOVERY_RESERVATION_EXISTS", message="Review the existing reservation before selecting another appointment.")
    grant.appointment_id = appointment.id
    grant.readback_nonce, grant.readback_fingerprint = None, None
    case.paused, case.reason = True, "CUSTOMER_CONTINUING_BOOKING"


def guard_confirmation(session: Session, appointment: Appointment) -> None:
    from insurance_operations.recovery.continuation import fingerprint

    context = current_recovery_booking.get()
    if context is None:
        return
    settings = session.info.get("integration_settings")
    grant = session.get(RecoveryGrant, context.grant_id, with_for_update=True)
    if grant is None or not isinstance(settings, DatabaseSettings):
        raise unavailable()
    _, _, request = scope(session, settings, grant)
    if grant.status != "ACTIVE" or not grant.approved_at or grant.appointment_id != appointment.id or request.id != appointment.service_request_id or grant.readback_fingerprint != fingerprint(appointment, request.fingerprint):
        raise unavailable()


def guard_release(session: Session, appointment: Appointment) -> None:
    context = current_recovery_booking.get()
    if context is None:
        return
    settings = session.info.get("integration_settings")
    grant = session.get(RecoveryGrant, context.grant_id, with_for_update=True)
    if grant is None or not isinstance(settings, DatabaseSettings):
        raise unavailable()
    scope(session, settings, grant)
    if grant.status != "ACTIVE" or grant.approved_at or grant.appointment_id != appointment.id or grant.row_version != context.expected_version:
        raise unavailable()


def attribution_for(session: Session, appointment: Appointment) -> UUID | None:
    from insurance_operations.recovery.continuation import fingerprint

    grant = session.scalar(select(RecoveryGrant).where(RecoveryGrant.agency_id == appointment.agency_id,
        RecoveryGrant.appointment_id == appointment.id).with_for_update())
    if grant is None or grant.status not in {"ACTIVE", "CONSUMED"} or grant.approved_at is None:
        return None
    settings = session.info.get("integration_settings")
    case = session.get(RecoveryCase, grant.recovery_case_id)
    request = session.get(HvacServiceRequest, appointment.service_request_id)
    attempt = session.get(RecoveryAttempt, grant.attempt_id)
    if not isinstance(settings, DatabaseSettings) or not case or not request or not attempt:
        return None
    if case.agency_id != appointment.agency_id or case.service_request_id != request.id or case.status in {"CLOSED", "SUPPRESSED"} or attempt.recovery_case_id != case.id or attempt.channel != grant.channel:
        return None
    if grant.readback_fingerprint != fingerprint(appointment, request.fingerprint):
        return None
    if not channel_allowed(permission_rows(session, settings, request), grant.channel):
        return None
    if not attempt.recipient_digest or pending_opt_out(session, grant.agency_id, attempt.recipient_digest):
        return None
    if grant.status == "ACTIVE":
        # Approval is durable so GHL's existing unknown-write recovery can finalize the same selection.
        grant.status = "CONSUMED"
    return attempt.id
