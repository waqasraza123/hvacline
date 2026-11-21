import hashlib
import json
from datetime import UTC, date, datetime
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.database.models.hvac import Appointment
from insurance_operations.database.models.recovery import RecoveryGrant
from insurance_operations.errors import ApiError
from insurance_operations.hvac.locking import lock_business_schedule
from insurance_operations.hvac.schemas import AppointmentView, AvailabilityInput, AvailabilityResponse, ReservationInput
from insurance_operations.recovery.domain import audit, policy_for
from insurance_operations.recovery.grants import authenticate, booking_scope, scope, unavailable
from insurance_operations.settings import DatabaseSettings


class SlotSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_row_version: int = Field(ge=1)
    team_key: str = Field(pattern=r"^[a-z0-9-]{1,40}$")
    starts_at: datetime

    @field_validator("starts_at")
    @classmethod
    def aware_start(cls, value: datetime) -> datetime:
        if value.utcoffset() is None:
            raise ValueError("Appointment selection requires a timezone offset")
        return value


class Confirmation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_row_version: int = Field(ge=1)
    nonce: UUID
    explicit_confirmation: bool = Field(strict=True)


def fingerprint(appointment: Appointment, request_fingerprint: str) -> str:
    return hashlib.sha256(json.dumps({"id": str(appointment.id), "start": appointment.starts_at.isoformat(),
        "end": appointment.ends_at.isoformat(), "team": appointment.team_key, "request": request_fingerprint}, sort_keys=True).encode()).hexdigest()


class RecoveryContinuation:
    def __init__(self, sessions: sessionmaker[Session], settings: DatabaseSettings) -> None:
        from insurance_operations.hvac.service import SchedulingService

        self.sessions, self.settings = sessions, settings
        self.scheduling = SchedulingService(sessions)

    def _locked(self, session: Session, token: str, *, consumed: bool = False) -> RecoveryGrant:
        seed = authenticate(session, self.settings, token)
        if lock_business_schedule(session, seed.agency_id) is None:
            raise unavailable()
        grant = authenticate(session, self.settings, token, lock=True)
        scope(session, self.settings, grant, allow_consumed=consumed)
        return grant

    def context(self, token: str) -> dict[str, object]:
        with self.sessions() as session, session.begin():
            grant = self._locked(session, token, consumed=True)
            case, _, request = scope(session, self.settings, grant, allow_consumed=True)
            appointment = session.get(Appointment, grant.appointment_id) if grant.appointment_id else None
            return {"status": grant.status, "row_version": grant.row_version, "expires_at": grant.expires_at.isoformat(),
                "service": request.service_details, "customer": request.customer_details,
                "timezone": policy_for(session, grant.agency_id).timezone,
                "appointment": AppointmentView.model_validate(appointment).model_dump(mode="json") if appointment else None,
                "approved_confirmation": {"nonce": str(grant.readback_nonce), "row_version": grant.row_version} if grant.approved_at and grant.readback_nonce else None,
                "confirmed": bool(appointment and appointment.status == "CONFIRMED" and grant.status == "CONSUMED")}

    def availability(self, token: str, day: date) -> AvailabilityResponse:
        with self.sessions() as session, session.begin():
            grant = self._locked(session, token)
            _, _, request = scope(session, self.settings, grant)
            if grant.status != "ACTIVE":
                raise unavailable()
            address = request.customer_details.get("address")
            if not isinstance(address, dict):
                raise unavailable()
            agency_id, postal_code = grant.agency_id, str(address.get("postal_code") or "")
        return self.scheduling.availability(agency_id, AvailabilityInput(postal_code=postal_code, day=day))

    def reserve(self, token: str, data: SlotSelection) -> dict[str, object]:
        with self.sessions() as session, session.begin():
            grant = self._locked(session, token)
            _, _, request = scope(session, self.settings, grant)
            if grant.row_version != data.expected_row_version or grant.status != "ACTIVE":
                raise ApiError(status_code=409, code="RECOVERY_SESSION_CHANGED", message="Refresh the booking session before selecting a time.")
            if grant.appointment_id:
                previous = session.get(Appointment, grant.appointment_id)
                if previous and previous.team_key == data.team_key and previous.starts_at == data.starts_at:
                    return {"appointment": AppointmentView.model_validate(previous).model_dump(mode="json"), "row_version": grant.row_version}
                raise ApiError(status_code=409, code="RECOVERY_RESERVATION_EXISTS", message="Review or release the existing reservation first.")
            # Freeze a single reservation identity before the existing booking service runs.
            key = grant.reservation_key or f"recovery:{grant.id}:{uuid4()}"
            grant.reservation_key = key
            session.flush()
            session.refresh(grant)
            agency_id, request_id = grant.agency_id, request.id
        with booking_scope(grant):
            appointment = self.scheduling.reserve(agency_id, ReservationInput(service_request_id=request_id,
                team_key=data.team_key, starts_at=data.starts_at, idempotency_key=key), uuid4())
        return {"appointment": appointment.model_dump(mode="json"), "session": self.context(token)}

    def release(self, token: str) -> dict[str, object]:
        with self.sessions() as session, session.begin():
            grant = self._locked(session, token)
            if grant.approved_at:
                raise ApiError(status_code=409, code="RECOVERY_CONFIRMATION_PENDING", message="Check the approved booking outcome before changing this reservation.")
            agency_id, appointment_id = grant.agency_id, grant.appointment_id
        if appointment_id:
            with booking_scope(grant):
                self.scheduling.release_hold(agency_id, appointment_id, uuid4())
        with self.sessions() as session, session.begin():
            grant = self._locked(session, token)
            if grant.appointment_id != appointment_id or grant.approved_at:
                raise unavailable()
            grant.appointment_id, grant.reservation_key = None, None
            grant.readback_nonce, grant.readback_fingerprint = None, None
        return self.context(token)

    def readback(self, token: str) -> dict[str, object]:
        with self.sessions() as session, session.begin():
            grant = self._locked(session, token)
            _, _, request = scope(session, self.settings, grant)
            appointment = session.get(Appointment, grant.appointment_id) if grant.appointment_id else None
            if not appointment or appointment.agency_id != grant.agency_id or appointment.service_request_id != request.id or appointment.status != "HELD" or appointment.hold_expires_at <= datetime.now(UTC):
                raise ApiError(status_code=409, code="RESERVATION_EXPIRED", message="This reservation is no longer active. Contact the business or release it before choosing again.")
            readback = self._readback_text(session, grant, appointment, request.customer_details, request.service_details)
            if grant.approved_at:
                raise ApiError(status_code=409, code="RECOVERY_CONFIRMATION_PENDING", message="The previous confirmation is pending. Refresh its saved outcome.")
            grant.readback_nonce = uuid4()
            grant.readback_fingerprint = fingerprint(appointment, request.fingerprint)
            session.flush()
            session.refresh(grant)
            return {"readback": readback, "nonce": str(grant.readback_nonce), "row_version": grant.row_version}

    def current_readback(self, token: str, nonce: UUID) -> str:
        with self.sessions() as session, session.begin():
            grant = self._locked(session, token, consumed=True)
            _, _, request = scope(session, self.settings, grant, allow_consumed=True)
            appointment = session.get(Appointment, grant.appointment_id) if grant.appointment_id else None
            if not appointment or grant.readback_nonce != nonce or grant.readback_fingerprint != fingerprint(appointment, request.fingerprint):
                raise unavailable()
            return self._readback_text(session, grant, appointment, request.customer_details, request.service_details)

    @staticmethod
    def _readback_text(session: Session, grant: RecoveryGrant, appointment: Appointment,
                       customer: dict[str, object], service: dict[str, object]) -> str:
        zone = ZoneInfo(policy_for(session, grant.agency_id).timezone)
        local = appointment.starts_at.astimezone(zone)
        address = customer.get("address")
        if not isinstance(address, dict):
            raise unavailable()
        street = str(address.get("line1", ""))
        if address.get("line2"):
            street += f", {address['line2']}"
        return (f"Please confirm your {str(service.get('kind', 'HVAC service')).replace('_', ' ').lower()} appointment "
            f"on {local.strftime('%A, %B %d, %Y at %I:%M %p')} {zone.key}, "
            f"at {street}, {address.get('city', '')}, {address.get('state_code', '')} {address.get('postal_code', '')}. "
            "May I confirm this appointment? Reply yes to confirm the appointment, or tell me what to correct.")

    def confirm(self, token: str, data: Confirmation) -> AppointmentView:
        if data.explicit_confirmation is not True:
            raise ApiError(status_code=422, code="EXPLICIT_CONFIRMATION_REQUIRED", message="Confirm the exact displayed appointment before booking.")
        with self.sessions() as session, session.begin():
            grant = self._locked(session, token, consumed=True)
            _, _, request = scope(session, self.settings, grant, allow_consumed=True)
            appointment = session.get(Appointment, grant.appointment_id) if grant.appointment_id else None
            if not appointment or appointment.agency_id != grant.agency_id or appointment.service_request_id != request.id:
                raise unavailable()
            if grant.status == "CONSUMED" and appointment.status == "CONFIRMED":
                return AppointmentView.model_validate(appointment)
            if grant.approved_at is None:
                if grant.row_version != data.expected_row_version or grant.readback_nonce != data.nonce or grant.readback_fingerprint != fingerprint(appointment, request.fingerprint):
                    raise ApiError(status_code=409, code="RECOVERY_READBACK_CHANGED", message="Read back the current selection and obtain a fresh confirmation.")
                if appointment.status != "HELD" or appointment.hold_expires_at <= datetime.now(UTC):
                    raise ApiError(status_code=409, code="RESERVATION_EXPIRED", message="The reservation expired before confirmation.")
                grant.approved_at = datetime.now(UTC)
                audit(session, grant.agency_id, "LEAD_RECOVERY_SELECTION_APPROVED", {"grant_id": str(grant.id), "appointment_id": str(appointment.id)})
            elif data.nonce != grant.readback_nonce:
                raise unavailable()
            agency_id, appointment_id = grant.agency_id, appointment.id
        # All capacity, external-calendar and GHL confirmation rules remain in this service.
        try:
            with booking_scope(grant):
                return self.scheduling.confirm(agency_id, appointment_id, True, uuid4())
        except ApiError as error:
            from insurance_operations.database.models.recovery import RecoveryCase
            from insurance_operations.recovery.domain import TERMINAL

            with self.sessions() as session, session.begin():
                lock_business_schedule(session, agency_id)
                case = session.scalar(select(RecoveryCase).where(RecoveryCase.agency_id == agency_id,
                    RecoveryCase.service_request_id == request.id).with_for_update())
                if case and case.status not in TERMINAL:
                    case.status, case.paused, case.reason = "NEEDS_REVIEW", True, "BOOKING_CONFIRMATION_REQUIRES_REVIEW"
                    audit(session, agency_id, "LEAD_RECOVERY_BOOKING_REVIEW", {"case_id": str(case.id), "appointment_id": str(appointment_id), "code": error.code})
            raise
