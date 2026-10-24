import hashlib
import json
from datetime import UTC, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.database.models.hvac import (
    Appointment,
    BusinessSchedule,
    HvacServiceRequest,
)
from insurance_operations.database.models.identity import Agency
from insurance_operations.errors import ApiError
from insurance_operations.hvac.availability import candidate_slots, overlaps
from insurance_operations.hvac.schemas import (
    AppointmentView,
    AvailabilityInput,
    AvailabilityResponse,
    ReservationInput,
    ScheduleInput,
    ServiceRequestInput,
)
from insurance_operations.telephony.phone_service import system_audit


def fingerprint(value: dict[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def unavailable(message: str, code: str = "SCHEDULING_UNAVAILABLE") -> ApiError:
    return ApiError(status_code=409, code=code, message=message)


class SchedulingService:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.sessions = session_factory

    def configuration(self, agency_id: UUID) -> dict[str, object]:
        with self.sessions() as session:
            schedule = session.get(BusinessSchedule, agency_id)
            return (
                {"version": schedule.version, "configuration": schedule.configuration}
                if schedule
                else {"version": 0, "configuration": None}
            )

    def configure(
        self, agency_id: UUID, request: ScheduleInput, correlation_id: UUID
    ) -> dict[str, object]:
        with self.sessions() as session, session.begin():
            session.scalar(
                select(Agency).where(Agency.id == agency_id).with_for_update()
            )
            schedule = session.get(BusinessSchedule, agency_id)
            version = schedule.version if schedule else 0
            if version != request.expected_version:
                raise unavailable(
                    "Business scheduling settings changed. Reload before saving.",
                    "SCHEDULE_VERSION_CONFLICT",
                )
            content = request.model_dump(mode="json")
            if schedule is None:
                schedule = BusinessSchedule(
                    agency_id=agency_id, version=1, configuration=content
                )
                session.add(schedule)
            else:
                schedule.configuration = content
                schedule.version += 1
            session.add(
                system_audit(
                    agency_id=agency_id,
                    event_type="HVAC_SCHEDULE_CONFIGURED",
                    summary="Business scheduling updated",
                    details={"version": schedule.version},
                    correlation_id=correlation_id,
                )
            )
            return {"version": schedule.version, "configuration": content}

    def create_request(
        self,
        agency_id: UUID,
        request: ServiceRequestInput,
        correlation_id: UUID,
        call_id: UUID | None = None,
    ) -> UUID:
        value = fingerprint(
            request.model_dump(
                mode="json", include=set(ServiceRequestInput.model_fields)
            )
        )
        with self.sessions() as session, session.begin():
            session.scalar(
                select(Agency).where(Agency.id == agency_id).with_for_update()
            )
            if call_id:
                existing = session.scalar(
                    select(HvacServiceRequest).where(
                        HvacServiceRequest.agency_id == agency_id,
                        HvacServiceRequest.inbound_call_id == call_id,
                    )
                )
                if existing:
                    if existing.fingerprint != value:
                        raise unavailable(
                            "This call already has a different confirmed "
                            "service request.",
                            "SERVICE_REQUEST_CONFLICT",
                        )
                    return existing.id
            row = HvacServiceRequest(
                agency_id=agency_id,
                inbound_call_id=call_id,
                customer_details=request.customer.model_dump(mode="json"),
                service_details=request.service.model_dump(mode="json"),
                status="HANDOFF_REQUESTED"
                if request.service.hazardous_condition
                else "OPEN",
                fingerprint=value,
                confirmed_at=datetime.now(UTC),
            )
            session.add(row)
            session.flush()
            session.add(
                system_audit(
                    agency_id=agency_id,
                    event_type="HVAC_SERVICE_REQUEST_CONFIRMED",
                    summary="Caller confirmed HVAC service details",
                    details={
                        "service_request_id": str(row.id),
                        "hazardous_condition": request.service.hazardous_condition,
                    },
                    correlation_id=correlation_id,
                )
            )
            return row.id

    def availability(
        self, agency_id: UUID, request: AvailabilityInput
    ) -> AvailabilityResponse:
        with self.sessions() as session:
            schedule = session.get(BusinessSchedule, agency_id)
            if schedule is None:
                return AvailabilityResponse(
                    configured=False,
                    in_service_area=False,
                    message="Scheduling is not configured. Offer a callback.",
                )
            configuration = ScheduleInput.model_validate(schedule.configuration)
            in_area = request.postal_code in configuration.postal_codes
            now = datetime.now(UTC)
            slots = candidate_slots(configuration, request.day, now) if in_area else []
            busy = self._busy(session, agency_id, now)
            free = [
                slot
                for slot in slots
                if not any(
                    row.team_key == slot.team_key
                    and overlaps(
                        slot.starts_at, slot.ends_at, row.starts_at, row.ends_at
                    )
                    for row in busy
                )
            ]
            return AvailabilityResponse(
                configured=configuration.enabled,
                in_service_area=in_area,
                timezone=configuration.timezone,
                slots=free[:100],
                message=None
                if free
                else (
                    "No bookable appointments for this date. "
                    "Offer another date or callback."
                ),
            )

    def reserve(
        self, agency_id: UUID, request: ReservationInput, correlation_id: UUID
    ) -> AppointmentView:
        with self.sessions() as session, session.begin():
            configuration = self._lock_schedule(session, agency_id)
            row = self._reserve(
                session, agency_id, request, configuration, datetime.now(UTC)
            )
            session.add(
                system_audit(
                    agency_id=agency_id,
                    event_type="HVAC_APPOINTMENT_RESERVED",
                    summary="Appointment reservation persisted",
                    details={"appointment_id": str(row.id)},
                    correlation_id=correlation_id,
                )
            )
            return AppointmentView.model_validate(row)

    def _reserve(
        self,
        session: Session,
        agency_id: UUID,
        request: ReservationInput,
        configuration: ScheduleInput,
        now: datetime,
        replace_id: UUID | None = None,
    ) -> Appointment:
        digest = fingerprint(
            request.model_dump(mode="json", include=set(ReservationInput.model_fields))
        )
        existing = session.scalar(
            select(Appointment).where(
                Appointment.agency_id == agency_id,
                Appointment.idempotency_key == request.idempotency_key,
            )
        )
        if existing:
            if existing.fingerprint != digest:
                raise unavailable(
                    "The booking key was already used with different details.",
                    "BOOKING_KEY_CONFLICT",
                )
            return existing
        service_request = self._request(session, agency_id, request.service_request_id)
        if (
            service_request.service_details.get("hazardous_condition")
            or service_request.status == "CLOSED"
        ):
            raise unavailable(
                "This service request requires human attention.",
                "HUMAN_ATTENTION_REQUIRED",
            )
        customer = ServiceRequestInput.model_validate(
            {
                "customer": service_request.customer_details,
                "service": service_request.service_details,
                "explicit_confirmation": True,
            }
        ).customer
        if (
            customer.address is None
            or customer.address.postal_code not in configuration.postal_codes
        ):
            raise unavailable(
                "The service address is outside the configured service area.",
                "OUTSIDE_SERVICE_AREA",
            )
        day = request.starts_at.astimezone(ZoneInfo(configuration.timezone)).date()
        slot = next(
            (
                slot
                for slot in candidate_slots(configuration, day, now)
                if slot.team_key == request.team_key
                and slot.starts_at == request.starts_at
            ),
            None,
        )
        if slot is None:
            raise unavailable(
                "That time is not currently bookable.", "SLOT_UNAVAILABLE"
            )
        for row in self._busy(session, agency_id, now):
            if row.id == replace_id:
                continue
            if row.service_request_id == request.service_request_id or (
                row.team_key == slot.team_key
                and overlaps(slot.starts_at, slot.ends_at, row.starts_at, row.ends_at)
            ):
                raise unavailable(
                    "The appointment or technician is already reserved.",
                    "SLOT_CONFLICT",
                )
        row = Appointment(
            agency_id=agency_id,
            service_request_id=service_request.id,
            team_key=slot.team_key,
            starts_at=slot.starts_at,
            ends_at=slot.ends_at,
            status="HELD",
            hold_expires_at=now + timedelta(minutes=5),
            idempotency_key=request.idempotency_key,
            fingerprint=digest,
        )
        session.add(row)
        session.flush()
        return row

    def confirm(
        self,
        agency_id: UUID,
        appointment_id: UUID,
        explicit_confirmation: bool,
        correlation_id: UUID,
    ) -> AppointmentView:
        if not explicit_confirmation:
            raise unavailable("Explicit confirmation of the appointment is required.")
        with self.sessions() as session, session.begin():
            configuration = self._lock_schedule(session, agency_id)
            row = self._appointment(session, agency_id, appointment_id)
            if row.status == "CONFIRMED":
                return AppointmentView.model_validate(row)
            now = datetime.now(UTC)
            if row.status != "HELD" or row.hold_expires_at <= now:
                raise unavailable(
                    "The reservation expired or is no longer active.",
                    "RESERVATION_EXPIRED",
                )
            day = row.starts_at.astimezone(ZoneInfo(configuration.timezone)).date()
            if not any(
                slot.team_key == row.team_key and slot.starts_at == row.starts_at
                for slot in candidate_slots(configuration, day, now)
            ):
                raise unavailable(
                    "Availability changed. Request a new appointment.",
                    "SLOT_UNAVAILABLE",
                )
            row.status = "CONFIRMED"
            self._request(session, agency_id, row.service_request_id).status = "BOOKED"
            session.add(
                system_audit(
                    agency_id=agency_id,
                    event_type="HVAC_APPOINTMENT_CONFIRMED",
                    summary="Appointment confirmed",
                    details={"appointment_id": str(row.id)},
                    correlation_id=correlation_id,
                )
            )
            return AppointmentView.model_validate(row)

    def cancel(
        self, agency_id: UUID, appointment_id: UUID, correlation_id: UUID
    ) -> AppointmentView:
        with self.sessions() as session, session.begin():
            configuration = self._lock_schedule(session, agency_id)
            row = self._appointment(session, agency_id, appointment_id)
            if row.status == "CANCELLED":
                return AppointmentView.model_validate(row)
            self._allow_change(row, configuration, datetime.now(UTC))
            row.status = "CANCELLED"
            self._request(session, agency_id, row.service_request_id).status = "OPEN"
            session.add(
                system_audit(
                    agency_id=agency_id,
                    event_type="HVAC_APPOINTMENT_CANCELLED",
                    summary="Appointment cancelled",
                    details={"appointment_id": str(row.id)},
                    correlation_id=correlation_id,
                )
            )
            return AppointmentView.model_validate(row)

    def reschedule(
        self,
        agency_id: UUID,
        appointment_id: UUID,
        request: ReservationInput,
        correlation_id: UUID,
    ) -> AppointmentView:
        with self.sessions() as session, session.begin():
            configuration = self._lock_schedule(session, agency_id)
            old = self._appointment(session, agency_id, appointment_id)
            if old.service_request_id != request.service_request_id:
                raise unavailable(
                    "The new appointment must belong to the same service request."
                )
            replacement = session.scalar(
                select(Appointment).where(
                    Appointment.agency_id == agency_id,
                    Appointment.idempotency_key == request.idempotency_key,
                )
            )
            if (
                old.status == "CANCELLED"
                and replacement
                and replacement.fingerprint
                == fingerprint(
                    request.model_dump(
                        mode="json", include=set(ReservationInput.model_fields)
                    )
                )
            ):
                return AppointmentView.model_validate(replacement)
            self._allow_change(old, configuration, datetime.now(UTC))
            new = self._reserve(
                session,
                agency_id,
                request,
                configuration,
                datetime.now(UTC),
                replace_id=old.id,
            )
            if new.id == old.id or new.status != "HELD":
                raise unavailable("Use a fresh booking key to reschedule.")
            old.status = "CANCELLED"
            new.status = "CONFIRMED"
            self._request(session, agency_id, old.service_request_id).status = "BOOKED"
            session.add(
                system_audit(
                    agency_id=agency_id,
                    event_type="HVAC_APPOINTMENT_RESCHEDULED",
                    summary="Appointment rescheduled atomically",
                    details={
                        "previous_appointment_id": str(old.id),
                        "appointment_id": str(new.id),
                    },
                    correlation_id=correlation_id,
                )
            )
            return AppointmentView.model_validate(new)

    @staticmethod
    def _allow_change(
        row: Appointment, configuration: ScheduleInput, now: datetime
    ) -> None:
        if row.status not in {"HELD", "CONFIRMED"} or row.starts_at < now + timedelta(
            minutes=configuration.cancellation_notice_minutes
        ):
            raise unavailable(
                "This appointment requires a human to change it.",
                "CHANGE_NOTICE_REQUIRED",
            )

    @staticmethod
    def _lock_schedule(session: Session, agency_id: UUID) -> ScheduleInput:
        schedule = session.scalar(
            select(BusinessSchedule)
            .where(BusinessSchedule.agency_id == agency_id)
            .with_for_update()
        )
        if schedule is None:
            raise unavailable("Scheduling is not configured. Offer a callback.")
        return ScheduleInput.model_validate(schedule.configuration)

    @staticmethod
    def _request(
        session: Session, agency_id: UUID, request_id: UUID
    ) -> HvacServiceRequest:
        row = session.scalar(
            select(HvacServiceRequest).where(
                HvacServiceRequest.agency_id == agency_id,
                HvacServiceRequest.id == request_id,
            )
        )
        if row is None:
            raise ApiError(
                status_code=404,
                code="SERVICE_REQUEST_NOT_FOUND",
                message="Service request not found",
            )
        return row

    @staticmethod
    def _appointment(
        session: Session, agency_id: UUID, appointment_id: UUID
    ) -> Appointment:
        row = session.scalar(
            select(Appointment).where(
                Appointment.agency_id == agency_id, Appointment.id == appointment_id
            )
        )
        if row is None:
            raise ApiError(
                status_code=404,
                code="APPOINTMENT_NOT_FOUND",
                message="Appointment not found",
            )
        return row

    @staticmethod
    def _busy(session: Session, agency_id: UUID, now: datetime) -> list[Appointment]:
        return list(
            session.scalars(
                select(Appointment).where(
                    Appointment.agency_id == agency_id,
                    or_(
                        Appointment.status == "CONFIRMED",
                        (Appointment.status == "HELD")
                        & (Appointment.hold_expires_at > now),
                    ),
                )
            )
        )
