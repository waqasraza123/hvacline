from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import exists, func, or_, select
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.actors import ActorContext
from insurance_operations.customers import CustomerInput
from insurance_operations.database.models.booking_integrations import CalendarConnection
from insurance_operations.database.models.ghl import GhlCalendarBooking, GhlConnection
from insurance_operations.database.models.hvac import Appointment, BusinessSchedule
from insurance_operations.errors import ApiError
from insurance_operations.ghl.provider import GhlClient, GhlError
from insurance_operations.ghl.schemas import (
    BookingRecoveryInput,
    VoiceConfiguration,
    VoiceConfigurationInput,
)
from insurance_operations.ghl.service import (
    GhlBusy,
    GhlService,
    GhlVault,
    ProviderFactory,
    agency_lock,
    audit,
    open_provider,
    unavailable,
)
from insurance_operations.hvac.locking import lock_business_schedule
from insurance_operations.hvac.schemas import AppointmentView, ScheduleInput, Slot
from insurance_operations.job_execution import JobDeadlineExceeded, job_budget
from insurance_operations.notifications.booking import enqueue_booking_notifications
from insurance_operations.settings import DatabaseSettings, RuntimeEnvironment
from insurance_operations.telephony.phone_service import system_audit


UNRESOLVED = ("CONTACT_PENDING", "CREATING", "UNKNOWN", "NEEDS_REVIEW")


def voice_configuration(connection: GhlConnection) -> VoiceConfiguration:
    try:
        return VoiceConfiguration.model_validate(connection.voice_configuration or {})
    except ValueError:
        raise GhlError("GHL_CONNECTION_INVALID", connection_error=True) from None


def routed_connection(
    session: Session, agency_id: UUID, team_key: str
) -> tuple[GhlConnection, str] | None:
    connection = session.scalar(
        select(GhlConnection).where(
            GhlConnection.agency_id == agency_id,
            GhlConnection.status != "DISCONNECTED",
        )
    )
    if connection is None:
        return None
    route = next(
        (
            row
            for row in voice_configuration(connection).calendars
            if row.team_key == team_key
        ),
        None,
    )
    return (connection, route.calendar_id) if route else None


def require_booking_connection(session: Session, connection: GhlConnection) -> None:
    settings = session.info.get("integration_settings")
    if (
        not isinstance(settings, DatabaseSettings)
        or not settings.ghl_enabled
        or settings.app_environment is RuntimeEnvironment.PRODUCTION
        or connection.status != "ACTIVE"
        or (connection.blocked_until and connection.blocked_until > datetime.now(UTC))
    ):
        raise GhlError("GHL_BOOKING_UNAVAILABLE")


def booking_error(error: GhlError) -> ApiError:
    return ApiError(
        code=error.code,
        message=(
            "GHL could not confirm this booking. Do not promise an appointment. "
            "Keep the reservation reference and ask staff to review GHL booking status."
        ),
        status_code=503 if error.retryable else 409,
        headers={
            "Cache-Control": "no-store",
            **(
                {"Retry-After": str(error.retry_after or 60)} if error.retryable else {}
            ),
        },
    )


def guard_change(session: Session, appointment: Appointment) -> None:
    binding = session.get(GhlCalendarBooking, appointment.id)
    if (
        binding
        and binding.agency_id == appointment.agency_id
        and (binding.status in UNRESOLVED or binding.event_id)
    ):
        raise unavailable(
            "GHL_BOOKING_REVIEW_REQUIRED",
            (
                "This appointment is linked to GHL or has an unresolved booking attempt. "
                "Ask staff to review it in Integrations before making changes."
            ),
        )


def bind_ghl_reservation(session: Session, appointment: Appointment) -> None:
    route = routed_connection(session, appointment.agency_id, appointment.team_key)
    if route:
        try:
            require_booking_connection(session, route[0])
        except GhlError as error:
            raise booking_error(error) from None
        session.add(
            GhlCalendarBooking(
                appointment_id=appointment.id,
                agency_id=appointment.agency_id,
                connection_id=route[0].id,
                calendar_id=route[1],
                status="RESERVED",
            )
        )


def release_ghl_reservation(session: Session, appointment: Appointment) -> None:
    guard_change(session, appointment)
    binding = session.get(GhlCalendarBooking, appointment.id)
    if binding and binding.agency_id == appointment.agency_id:
        binding.status = "RELEASED"


def check_ghl_slots(
    session: Session, agency_id: UUID, slots: list[Slot], timezone: str, duration: int
) -> list[Slot]:
    try:
        with job_budget(12):
            return _filter_ghl_slots(session, agency_id, slots, timezone, duration)
    except JobDeadlineExceeded:
        raise booking_error(GhlError("GHL_TIMEOUT", retryable=True)) from None


def _filter_ghl_slots(
    session: Session, agency_id: UUID, slots: list[Slot], timezone: str, duration: int
) -> list[Slot]:
    try:
        for team_key in sorted({slot.team_key for slot in slots}):
            route = routed_connection(session, agency_id, team_key)
            if route is None:
                continue
            connection, calendar_id = route
            require_booking_connection(session, connection)
            if session.scalar(
                select(CalendarConnection.id).where(
                    CalendarConnection.agency_id == agency_id,
                    CalendarConnection.team_key == team_key,
                    CalendarConnection.status != "DISCONNECTED",
                )
            ):
                raise GhlError("GHL_CALENDAR_PROVIDER_CONFLICT")
            settings = session.info["integration_settings"]
            token = GhlVault(settings).decrypt(connection)
            team_slots = [slot for slot in slots if slot.team_key == team_key]
            day = team_slots[0].starts_at.astimezone(ZoneInfo(timezone)).date()
            with open_provider(token, connection.location_id) as client:
                client.calendar(calendar_id).require_duration(duration)
                available = client.free_slots(calendar_id, day, timezone)
            slots = [
                slot
                for slot in slots
                if slot.team_key != team_key or slot.starts_at in available
            ]
        return slots
    except GhlError as error:
        raise booking_error(error) from None


class GhlBookingService:
    def __init__(
        self, sessions: sessionmaker[Session], factory: ProviderFactory | None = None
    ) -> None:
        self.sessions = sessions
        self.factory = factory or open_provider

    def configuration(self, actor: ActorContext) -> dict[str, object]:
        with self.sessions() as session:
            connection = session.scalar(
                select(GhlConnection).where(
                    GhlConnection.agency_id == actor.agency_id,
                    GhlConnection.status != "DISCONNECTED",
                )
            )
            schedule = session.get(BusinessSchedule, actor.agency_id)
            configuration = (
                ScheduleInput.model_validate(schedule.configuration)
                if schedule
                else None
            )
            return {
                "configuration": voice_configuration(connection).model_dump()
                if connection
                else VoiceConfiguration().model_dump(),
                "version": connection.voice_version if connection else 0,
                "teams": [
                    {"key": team.key, "name": team.name} for team in configuration.teams
                ]
                if configuration
                else [],
            }

    def configure(
        self,
        actor: ActorContext,
        data: VoiceConfigurationInput,
        settings: DatabaseSettings,
    ) -> dict[str, object]:
        integration = GhlService(self.sessions, settings, self.factory)
        integration.enabled()
        with agency_lock(self.sessions, actor.agency_id):
            with self.sessions() as session:
                connection = integration.current(session, actor.agency_id)
                if connection.status != "ACTIVE":
                    raise unavailable(
                        "GHL_BOOKING_UNAVAILABLE",
                        "Resume the connection before changing voice settings.",
                    )
                token = GhlVault(settings).decrypt(connection)
                schedule = session.get(BusinessSchedule, actor.agency_id)
                schedule_version = schedule.version if schedule else 0
                configuration = (
                    ScheduleInput.model_validate(schedule.configuration)
                    if schedule
                    else None
                )
            if data.calendars:
                if not configuration or not {
                    row.team_key for row in data.calendars
                } <= {team.key for team in configuration.teams}:
                    raise unavailable(
                        "GHL_CALENDAR_TEAM_INVALID",
                        "Configure the business schedule and select existing teams first.",
                    )
                with self.factory(token, connection.location_id) as client:
                    for route in data.calendars:
                        client.calendar(route.calendar_id).require_duration(
                            configuration.duration_minutes
                        )
            with self.sessions() as session, session.begin():
                locked = lock_business_schedule(session, actor.agency_id)
                if (locked.version if locked else 0) != schedule_version:
                    raise unavailable(
                        "SCHEDULE_VERSION_CONFLICT",
                        "The schedule changed. Reload before saving.",
                    )
                current = integration.current(session, actor.agency_id)
                if current.voice_version != data.expected_version:
                    raise unavailable(
                        "GHL_VOICE_VERSION_CONFLICT",
                        "Voice settings changed. Reload before saving.",
                    )
                old = voice_configuration(current)
                old_routes = {
                    route.team_key: route.calendar_id for route in old.calendars
                }
                new_routes = {
                    route.team_key: route.calendar_id for route in data.calendars
                }
                for team_key in old_routes.keys() | new_routes.keys():
                    if old_routes.get(team_key) == new_routes.get(team_key):
                        continue
                    if session.scalar(
                        select(Appointment.id)
                        .where(
                            Appointment.agency_id == actor.agency_id,
                            Appointment.team_key == team_key,
                            or_(
                                (Appointment.status == "CONFIRMED")
                                & (Appointment.ends_at > datetime.now(UTC)),
                                (Appointment.status == "HELD")
                                & (Appointment.hold_expires_at > datetime.now(UTC)),
                                exists(
                                    select(GhlCalendarBooking.appointment_id).where(
                                        GhlCalendarBooking.appointment_id
                                        == Appointment.id,
                                        GhlCalendarBooking.status.in_(UNRESOLVED),
                                    )
                                ),
                            ),
                        )
                        .limit(1)
                    ):
                        raise unavailable(
                            "GHL_CALENDAR_IN_USE",
                            "Resolve existing reservations and appointments before changing a team's booking provider.",
                        )
                if new_routes and session.scalar(
                    select(CalendarConnection.id)
                    .where(
                        CalendarConnection.agency_id == actor.agency_id,
                        CalendarConnection.team_key.in_(new_routes),
                        CalendarConnection.status != "DISCONNECTED",
                    )
                    .limit(1)
                ):
                    raise unavailable(
                        "GHL_CALENDAR_PROVIDER_CONFLICT",
                        "Disconnect Google Calendar for the selected teams before routing them to GHL.",
                    )
                current.voice_configuration = data.model_dump(
                    exclude={"expected_version"}
                )
                current.voice_version += 1
                audit(session, actor, "GHL_VOICE_CONFIGURED", current.id)
            return self.configuration(actor)

    def _save(self, appointment_id: UUID, **values: object) -> None:
        with self.sessions() as session, session.begin():
            row = session.get(GhlCalendarBooking, appointment_id)
            if row is None:
                raise GhlError("GHL_BOOKING_UNAVAILABLE")
            for key, value in values.items():
                setattr(row, key, value)

    def _context(
        self,
        session: Session,
        agency_id: UUID,
        appointment_id: UUID,
        *,
        active: bool = True,
    ) -> tuple[Appointment, GhlCalendarBooking, GhlConnection]:
        binding = session.get(GhlCalendarBooking, appointment_id)
        appointment = session.get(Appointment, appointment_id)
        if (
            not binding
            or not appointment
            or binding.agency_id != agency_id
            or appointment.agency_id != agency_id
        ):
            raise unavailable(
                "GHL_BOOKING_NOT_FOUND", "GHL booking was not found.", 404
            )
        connection = session.get(GhlConnection, binding.connection_id)
        if not connection or connection.agency_id != agency_id:
            raise GhlError("GHL_BOOKING_UNAVAILABLE")
        if active:
            require_booking_connection(session, connection)
        return appointment, binding, connection

    def confirm(
        self, agency_id: UUID, appointment_id: UUID, correlation_id: UUID
    ) -> AppointmentView:
        try:
            with agency_lock(self.sessions, agency_id):
                try:
                    return self._confirm(agency_id, appointment_id, correlation_id)
                except GhlError as error:
                    self._failure(agency_id, appointment_id, error)
                    raise
                except JobDeadlineExceeded:
                    self._failure(
                        agency_id,
                        appointment_id,
                        GhlError("GHL_TIMEOUT", retryable=True),
                    )
                    raise
        except GhlBusy:
            raise unavailable(
                "GHL_BUSY",
                "A GHL operation is in progress. Keep this reservation and retry shortly.",
            ) from None
        except GhlError as error:
            raise booking_error(error) from None
        except JobDeadlineExceeded:
            raise booking_error(GhlError("GHL_TIMEOUT", retryable=True)) from None

    def _failure(self, agency_id: UUID, appointment_id: UUID, error: GhlError) -> None:
        with self.sessions() as session, session.begin():
            binding = session.get(GhlCalendarBooking, appointment_id)
            if binding is None or binding.agency_id != agency_id:
                return
            binding.last_error = error.code
            if binding.status == "CONTACT_PENDING" and not binding.contact_unknown:
                binding.status = "RESERVED"
            connection = session.get(GhlConnection, binding.connection_id)
            if connection and connection.agency_id == agency_id:
                connection.last_error = error.code
                if error.connection_error:
                    connection.status = "ERROR"
                if error.code == "GHL_RATE_LIMITED":
                    connection.blocked_until = datetime.now(UTC) + timedelta(
                        seconds=error.retry_after or 60
                    )

    def _confirm(
        self, agency_id: UUID, appointment_id: UUID, correlation_id: UUID
    ) -> AppointmentView:
        from insurance_operations.hvac.service import SchedulingService

        scheduling = SchedulingService(self.sessions)
        with self.sessions() as session, session.begin():
            configuration = scheduling._lock_schedule(session, agency_id)
            appointment, binding, connection = self._context(
                session, agency_id, appointment_id, active=False
            )
            if appointment.status == "CONFIRMED" and binding.status == "CONFIRMED":
                return AppointmentView.model_validate(appointment)
            require_booking_connection(session, connection)
            if (
                binding.status in {"CREATING", "UNKNOWN", "NEEDS_REVIEW"}
                and not binding.event_id
            ):
                raise GhlError("GHL_APPOINTMENT_CREATION_UNKNOWN")
            if binding.status == "RELEASED":
                raise GhlError("GHL_BOOKING_UNAVAILABLE")
            if not binding.event_id:
                scheduling._validate_confirmation(
                    session, agency_id, appointment, configuration
                )
            token = GhlVault(session.info["integration_settings"]).decrypt(connection)
            request = scheduling._request(
                session, agency_id, appointment.service_request_id
            )
            customer = CustomerInput.model_validate(request.customer_details)
            if not binding.event_id:
                binding.status = "CONTACT_PENDING"
            calendar_id, event_id = binding.calendar_id, binding.event_id
        with self.factory(token, connection.location_id) as client:
            if not event_id:
                self._contact(client, binding, customer)
                with self.sessions() as session:
                    saved = session.get(GhlCalendarBooking, appointment_id)
                    assert saved is not None
                    contact_id = saved.contact_id
                if contact_id is None:
                    raise GhlError("GHL_CONTACT_IDENTIFIER_REQUIRED")
                client.calendar(calendar_id).require_duration(
                    configuration.duration_minutes
                )
                day = appointment.starts_at.astimezone(
                    ZoneInfo(configuration.timezone)
                ).date()
                if appointment.starts_at not in client.free_slots(
                    calendar_id, day, configuration.timezone
                ):
                    self._save(
                        appointment_id,
                        status="RESERVED",
                        last_error="GHL_SLOT_UNAVAILABLE",
                    )
                    raise GhlError("GHL_SLOT_UNAVAILABLE")
                with self.sessions() as session, session.begin():
                    current_configuration = scheduling._lock_schedule(
                        session, agency_id
                    )
                    current_appointment, current_binding, _ = self._context(
                        session, agency_id, appointment_id
                    )
                    scheduling._validate_confirmation(
                        session, agency_id, current_appointment, current_configuration
                    )
                    current_binding.status, current_binding.last_error = (
                        "CREATING",
                        None,
                    )
                try:
                    event_id = client.create_appointment(
                        appointment_id,
                        calendar_id,
                        contact_id,
                        appointment.starts_at,
                        appointment.ends_at,
                    )
                except GhlError as error:
                    self._save(
                        appointment_id,
                        status="UNKNOWN" if error.ambiguous else "RESERVED",
                        last_error=error.code,
                    )
                    raise
                self._save(appointment_id, event_id=event_id)
            self._verify(client, binding, appointment, event_id)
        return self._finalize(agency_id, appointment_id, correlation_id)

    def _contact(
        self, client: GhlClient, binding: GhlCalendarBooking, customer: CustomerInput
    ) -> None:
        from insurance_operations.ghl.projection import normalized_phone

        if customer.address is None:
            raise GhlError("GHL_CONTACT_IDENTIFIER_REQUIRED")
        phone = normalized_phone(customer.phone, customer.address.country_code)
        if phone is None:
            raise GhlError("GHL_CONTACT_IDENTIFIER_REQUIRED")
        contact_id = client.match_contact(
            str(customer.email).casefold() if customer.email else None, phone
        )
        if binding.contact_id and contact_id != binding.contact_id:
            raise GhlError("GHL_CONTACT_MAPPING_CHANGED")
        if contact_id:
            self._save(
                binding.appointment_id, contact_id=contact_id, contact_unknown=False
            )
            binding.contact_id = contact_id
            return
        if binding.contact_unknown:
            raise GhlError("GHL_CONTACT_CREATION_UNKNOWN")
        self._save(binding.appointment_id, contact_unknown=True)
        values: dict[str, object] = {
            "name": customer.full_name,
            "phone": phone,
            "source": "HVACLine",
        }
        if customer.email:
            values["email"] = str(customer.email)
        try:
            contact_id = client.create_contact(values)
        except GhlError as error:
            if not error.ambiguous:
                self._save(
                    binding.appointment_id,
                    status="RESERVED",
                    contact_unknown=False,
                    last_error=error.code,
                )
            raise
        self._save(binding.appointment_id, contact_id=contact_id, contact_unknown=False)
        binding.contact_id = contact_id

    def _verify(
        self,
        client: GhlClient,
        binding: GhlCalendarBooking,
        appointment: Appointment,
        event_id: str,
    ) -> None:
        try:
            event = client.appointment(event_id)
            event.require_booking(
                location_id=client.location_id,
                calendar_id=binding.calendar_id,
                contact_id=binding.contact_id or "",
                appointment_id=appointment.id,
                starts_at=appointment.starts_at,
                ends_at=appointment.ends_at,
            )
        except GhlError as error:
            self._save(appointment.id, status="NEEDS_REVIEW", last_error=error.code)
            raise

    def _finalize(
        self, agency_id: UUID, appointment_id: UUID, correlation_id: UUID
    ) -> AppointmentView:
        from insurance_operations.hvac.service import SchedulingService

        scheduling = SchedulingService(self.sessions)
        try:
            with self.sessions() as session, session.begin():
                configuration = scheduling._lock_schedule(session, agency_id)
                appointment, binding, connection = self._context(
                    session, agency_id, appointment_id
                )
                if appointment.status == "CONFIRMED" and binding.status == "CONFIRMED":
                    return AppointmentView.model_validate(appointment)
                scheduling._validate_confirmation(
                    session, agency_id, appointment, configuration, allow_expired=True
                )
                if not binding.event_id:
                    raise GhlError("GHL_APPOINTMENT_CREATION_UNKNOWN")
                appointment.status, binding.status = "CONFIRMED", "CONFIRMED"
                binding.last_error = None
                scheduling._request(
                    session, agency_id, appointment.service_request_id
                ).status = "BOOKED"
                enqueue_booking_notifications(session, appointment)
                session.add(
                    system_audit(
                        agency_id=agency_id,
                        event_type="HVAC_APPOINTMENT_CONFIRMED",
                        summary="GHL appointment confirmed and verified",
                        details={"appointment_id": str(appointment_id)},
                        correlation_id=correlation_id,
                    )
                )
                return AppointmentView.model_validate(appointment)
        except (ApiError, GhlError):
            self._save(
                appointment_id,
                status="NEEDS_REVIEW",
                last_error="GHL_LOCAL_CONFIRMATION_REQUIRED",
            )
            raise GhlError("GHL_LOCAL_CONFIRMATION_REQUIRED") from None

    def recover(
        self, actor: ActorContext, appointment_id: UUID, data: BookingRecoveryInput
    ) -> dict[str, bool]:
        with agency_lock(self.sessions, actor.agency_id):
            with self.sessions() as session:
                appointment, binding, connection = self._context(
                    session, actor.agency_id, appointment_id
                )
                if binding.status not in UNRESOLVED:
                    raise unavailable(
                        "GHL_RECOVERY_INVALID",
                        "Only unresolved attempts can be reviewed.",
                    )
                token = GhlVault(session.info["integration_settings"]).decrypt(
                    connection
                )
            if data.remote_event_id:
                if binding.event_id and binding.event_id != data.remote_event_id:
                    raise GhlError("GHL_MAPPING_IMMUTABLE")
                with self.factory(token, connection.location_id) as client:
                    self._verify(client, binding, appointment, data.remote_event_id)
                self._save(
                    appointment_id, event_id=data.remote_event_id, status="NEEDS_REVIEW"
                )
                self._finalize(actor.agency_id, appointment_id, uuid4())
            else:
                if binding.event_id:
                    raise unavailable(
                        "GHL_RECOVERY_INVALID",
                        "A linked GHL appointment cannot be declared absent.",
                    )
                with self.sessions() as session, session.begin():
                    lock_business_schedule(session, actor.agency_id)
                    current = session.get(GhlCalendarBooking, appointment_id)
                    assert current is not None
                    current.status, current.contact_unknown, current.last_error = (
                        "RELEASED",
                        False,
                        None,
                    )
                    local = session.get(Appointment, appointment_id)
                    assert local is not None
                    local.status = "CANCELLED"
                    audit(
                        session, actor, "GHL_BOOKING_ABSENCE_REVIEWED", appointment_id
                    )
        return {"reviewed": True}

    def bookings(
        self, actor: ActorContext, offset: int, limit: int
    ) -> dict[str, object]:
        with self.sessions() as session:
            rows = session.execute(
                select(GhlCalendarBooking, Appointment)
                .join(Appointment, Appointment.id == GhlCalendarBooking.appointment_id)
                .where(
                    GhlCalendarBooking.agency_id == actor.agency_id,
                    Appointment.agency_id == actor.agency_id,
                )
                .order_by(
                    GhlCalendarBooking.created_at.desc(),
                    GhlCalendarBooking.appointment_id.desc(),
                )
                .offset(offset)
                .limit(limit)
            ).all()
            total = (
                session.scalar(
                    select(func.count())
                    .select_from(GhlCalendarBooking)
                    .where(GhlCalendarBooking.agency_id == actor.agency_id)
                )
                or 0
            )
            return {
                "items": [
                    {
                        "appointment_id": str(binding.appointment_id),
                        "calendar_id": binding.calendar_id,
                        "status": binding.status,
                        "contact_id": binding.contact_id,
                        "event_id": binding.event_id,
                        "last_error": binding.last_error,
                        "starts_at": appointment.starts_at,
                        "ends_at": appointment.ends_at,
                        "team_key": appointment.team_key,
                    }
                    for binding, appointment in rows
                ],
                "total": total,
                "offset": offset,
                "limit": limit,
            }
