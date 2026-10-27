from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.database.models.booking_integrations import (
    BookingEmailEvent,
    BookingNotification,
    CalendarBooking,
    CalendarConnection,
)
from insurance_operations.database.models.hvac import Appointment, HvacServiceRequest
from insurance_operations.database.models.identity import Agency
from insurance_operations.errors import ApiError
from insurance_operations.hvac.calendar import (
    CalendarConflict,
    CalendarUnavailable,
    GoogleCalendarAdapter,
)
from insurance_operations.hvac.calendar_sync import reconcile_booking
from insurance_operations.hvac.schemas import (
    AvailabilityInput,
    ReservationInput,
    ScheduleInput,
    ServiceRequestInput,
)
from insurance_operations.hvac.service import SchedulingService
from insurance_operations.notifications.booking import (
    ResendBookingEmail,
    deliver_notification,
)
from insurance_operations.notifications.email_events import apply_delivery_events
from insurance_operations.settings import DatabaseSettings, RuntimeEnvironment


def configure(engine: Engine) -> tuple[SchedulingService, UUID, ReservationInput]:
    with Session(engine) as session, session.begin():
        agency = Agency(
            name="Synthetic HVAC company",
            slug=str(uuid4()),
            environment_kind="DEVELOPMENT",
        )
        session.add(agency)
        session.flush()
        agency_id = agency.id
    service = SchedulingService(sessionmaker(bind=engine, expire_on_commit=False))
    day = (datetime.now(UTC) + timedelta(days=2)).date()
    windows = [{"weekday": day.weekday(), "start": "08:00", "end": "17:00"}]
    service.configure(
        agency_id,
        ScheduleInput(
            expected_version=0,
            enabled=True,
            timezone="America/New_York",
            postal_codes=["10001"],
            windows=windows,
            teams=[{"key": "team-a", "name": "Service team", "windows": windows}],
            notice_minutes=0,
        ),
        uuid4(),
    )
    request_id = service.create_request(agency_id, service_request(), uuid4())
    slot = service.availability(
        agency_id, AvailabilityInput(postal_code="10001", day=day)
    ).slots[0]
    return (
        service,
        agency_id,
        ReservationInput(
            service_request_id=request_id,
            team_key=slot.team_key,
            starts_at=slot.starts_at,
            idempotency_key=str(uuid4()),
        ),
    )


def service_request(hazardous: bool = False) -> ServiceRequestInput:
    return ServiceRequestInput.model_validate(
        {
            "customer": {
                "full_name": "Synthetic Caller",
                "phone": "+15559991002",
                "address": {
                    "line1": "123 Example St",
                    "city": "New York",
                    "state_code": "NY",
                    "postal_code": "10001",
                },
            },
            "service": {
                "kind": "AC_REPAIR",
                "equipment_issue": "AC stopped cooling",
                "preferred_window": "Morning",
                "hazardous_condition": hazardous,
            },
            "explicit_confirmation": True,
        }
    )


def test_booking_is_persistent_idempotent_and_tenant_scoped(
    migrated_database: Engine,
) -> None:
    service, agency_id, request = configure(migrated_database)
    reserved = service.reserve(agency_id, request, uuid4())
    assert reserved.status == "HELD"
    assert service.reserve(agency_id, request, uuid4()).id == reserved.id
    confirmed = service.confirm(agency_id, reserved.id, True, uuid4())
    assert confirmed.status == "CONFIRMED"
    with Session(migrated_database) as session:
        assert (
            session.scalar(
                select(Appointment.status).where(Appointment.id == confirmed.id)
            )
            == "CONFIRMED"
        )
    with pytest.raises(ApiError) as error:
        service.confirm(uuid4(), reserved.id, True, uuid4())
    assert error.value.status_code in {404, 409}
    with pytest.raises(ApiError) as error:
        service.reserve(
            agency_id, request.model_copy(update={"team_key": "other"}), uuid4()
        )
    assert error.value.code == "BOOKING_KEY_CONFLICT"


def test_concurrent_requests_cannot_double_book_one_technician(
    migrated_database: Engine,
) -> None:
    service, agency_id, first = configure(migrated_database)
    second_id = service.create_request(agency_id, service_request(), uuid4())
    second = first.model_copy(
        update={"service_request_id": second_id, "idempotency_key": str(uuid4())}
    )

    def reserve(request: ReservationInput) -> str:
        try:
            return service.reserve(agency_id, request, uuid4()).status
        except ApiError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(reserve, [first, second]))
    assert sorted(results) == ["HELD", "SLOT_CONFLICT"]


def test_expired_hold_and_hazard_cannot_be_confirmed_or_booked(
    migrated_database: Engine,
) -> None:
    service, agency_id, request = configure(migrated_database)
    reserved = service.reserve(agency_id, request, uuid4())
    with Session(migrated_database) as session, session.begin():
        appointment = session.get(Appointment, reserved.id)
        assert appointment is not None
        appointment.hold_expires_at = datetime.now(UTC) - timedelta(seconds=1)
    with pytest.raises(ApiError) as error:
        service.confirm(agency_id, reserved.id, True, uuid4())
    assert error.value.code == "RESERVATION_EXPIRED"
    hazardous = service.create_request(agency_id, service_request(True), uuid4())
    with pytest.raises(ApiError) as error:
        service.reserve(
            agency_id,
            request.model_copy(
                update={
                    "service_request_id": hazardous,
                    "idempotency_key": str(uuid4()),
                }
            ),
            uuid4(),
        )
    assert error.value.code == "HUMAN_ATTENTION_REQUIRED"


def test_reschedule_is_atomic_and_cancellation_releases_capacity(
    migrated_database: Engine,
) -> None:
    service, agency_id, request = configure(migrated_database)
    reserved = service.reserve(agency_id, request, uuid4())
    service.confirm(agency_id, reserved.id, True, uuid4())
    replacement = request.model_copy(
        update={
            "starts_at": request.starts_at + timedelta(hours=2),
            "idempotency_key": str(uuid4()),
        }
    )
    changed = service.reschedule(agency_id, reserved.id, replacement, uuid4())
    assert changed.status == "CONFIRMED"
    assert (
        service.reschedule(agency_id, reserved.id, replacement, uuid4()).id
        == changed.id
    )
    service.cancel(agency_id, changed.id, uuid4())
    assert (
        service.reserve(
            agency_id,
            request.model_copy(update={"idempotency_key": str(uuid4())}),
            uuid4(),
        ).status
        == "HELD"
    )


def test_phone_request_rejects_unresolved_call_context(
    migrated_database: Engine,
) -> None:
    service, agency_id, _ = configure(migrated_database)
    with pytest.raises(ApiError) as error:
        service.create_request(agency_id, service_request(), uuid4(), call_id=uuid4())
    assert error.value.status_code == 404


def test_active_hold_preserves_notice_period_until_confirmation(
    migrated_database: Engine,
) -> None:
    service, agency_id, request = configure(migrated_database)
    configuration = ScheduleInput.model_validate(
        service.configuration(agency_id)["configuration"]
    )
    configuration.expected_version = 1
    configuration.notice_minutes = 120
    service.configure(agency_id, configuration, uuid4())
    reserved_at = request.starts_at - timedelta(minutes=120)
    with patch("insurance_operations.hvac.service.datetime", wraps=datetime) as clock:
        clock.now.return_value = reserved_at
        reserved = service.reserve(agency_id, request, uuid4())
        clock.now.return_value = reserved_at + timedelta(minutes=4)
        assert (
            service.confirm(agency_id, reserved.id, True, uuid4()).status == "CONFIRMED"
        )


def connect_synthetic_calendar(
    service: SchedulingService, agency_id: UUID
) -> MagicMock:
    with service.sessions() as session, session.begin():
        session.add(
            CalendarConnection(
                agency_id=agency_id,
                team_key="team-a",
                calendar_id="synthetic-team",
                refresh_token_ciphertext="synthetic-encrypted-placeholder",
                status="CONNECTED",
            )
        )
    provider = MagicMock(spec=GoogleCalendarAdapter)
    provider.busy_events.return_value = []
    provider.event.return_value = None
    provider.publish.side_effect = lambda appointment_id, starts_at, ends_at: (
        appointment_id.hex
    )
    return provider


def test_external_conflict_leaves_hold_and_confirmation_queue_unchanged(
    migrated_database: Engine,
) -> None:
    service, agency_id, request = configure(migrated_database)
    provider = connect_synthetic_calendar(service, agency_id)
    with patch("insurance_operations.hvac.calendar_sync.calendar_adapter") as adapters:
        adapters.return_value.__enter__.return_value = provider
        held = service.reserve(agency_id, request, uuid4())
        provider.busy_events.side_effect = CalendarConflict("synthetic conflict")
        with pytest.raises(ApiError) as error:
            service.confirm(agency_id, held.id, True, uuid4())
    assert error.value.code == "CALENDAR_CONFLICT"
    provider.publish.assert_not_called()
    with service.sessions() as session:
        row = session.get(Appointment, held.id)
        assert row and row.status == "HELD"
        assert not session.scalar(
            select(BookingNotification.id).where(
                BookingNotification.appointment_id == held.id
            )
        )


def test_lost_remote_confirmation_response_recovers_the_same_event_and_one_queue(
    migrated_database: Engine,
) -> None:
    service, agency_id, request = configure(migrated_database)
    provider = connect_synthetic_calendar(service, agency_id)
    with patch("insurance_operations.hvac.calendar_sync.calendar_adapter") as adapters:
        adapters.return_value.__enter__.return_value = provider
        held = service.reserve(agency_id, request, uuid4())
        provider.publish.side_effect = [
            CalendarUnavailable("synthetic response lost"),
            held.id.hex,
        ]
        with pytest.raises(ApiError):
            service.confirm(agency_id, held.id, True, uuid4())
        provider.event.return_value = {"id": held.id.hex}
        assert service.confirm(agency_id, held.id, True, uuid4()).status == "CONFIRMED"
        service.confirm(agency_id, held.id, True, uuid4())
    assert {call.args[0] for call in provider.publish.call_args_list} == {held.id}
    with service.sessions() as session:
        binding = session.get(CalendarBooking, held.id)
        assert binding and binding.status == "SYNCED"
        kinds = list(
            session.scalars(
                select(BookingNotification.kind).where(
                    BookingNotification.appointment_id == held.id
                )
            )
        )
        assert kinds.count("CONFIRMATION") == 1


def test_provider_write_followed_by_database_failure_is_cleaned_from_durable_hold(
    migrated_database: Engine,
) -> None:
    service, agency_id, request = configure(migrated_database)
    provider = connect_synthetic_calendar(service, agency_id)
    with patch("insurance_operations.hvac.calendar_sync.calendar_adapter") as adapters:
        adapters.return_value.__enter__.return_value = provider
        held = service.reserve(agency_id, request, uuid4())
        with patch(
            "insurance_operations.hvac.service.enqueue_booking_notifications",
            side_effect=RuntimeError("synthetic transaction failure"),
        ):
            with pytest.raises(RuntimeError):
                service.confirm(agency_id, held.id, True, uuid4())
        with service.sessions() as session, session.begin():
            row = session.get(Appointment, held.id)
            binding = session.get(CalendarBooking, held.id)
            assert (
                row and binding and row.status == "HELD" and binding.status == "PENDING"
            )
            row.hold_expires_at = datetime.now(UTC) - timedelta(seconds=1)
            reconcile_booking(session, row, binding)
            assert row.status == "EXPIRED" and binding.status == "CANCELLED"
    provider.cancel_owned.assert_called_once_with(held.id, held.starts_at, held.ends_at)


def test_reschedule_failure_preserves_original_and_durable_replacement(
    migrated_database: Engine,
) -> None:
    service, agency_id, request = configure(migrated_database)
    provider = connect_synthetic_calendar(service, agency_id)
    with patch("insurance_operations.hvac.calendar_sync.calendar_adapter") as adapters:
        adapters.return_value.__enter__.return_value = provider
        held = service.reserve(agency_id, request, uuid4())
        service.confirm(agency_id, held.id, True, uuid4())
        replacement = request.model_copy(
            update={
                "starts_at": request.starts_at + timedelta(hours=2),
                "idempotency_key": str(uuid4()),
            }
        )
        provider.publish.side_effect = CalendarUnavailable("synthetic response lost")
        with pytest.raises(ApiError):
            service.reschedule(agency_id, held.id, replacement, uuid4())
        with service.sessions() as session:
            original = session.get(Appointment, held.id)
            new = session.scalar(
                select(Appointment).where(
                    Appointment.agency_id == agency_id,
                    Appointment.idempotency_key == replacement.idempotency_key,
                )
            )
            assert original and original.status == "CONFIRMED"
            assert new and new.status == "HELD" and session.get(CalendarBooking, new.id)
        provider.publish.side_effect = lambda appointment_id, starts_at, ends_at: (
            appointment_id.hex
        )
        booked = service.reschedule(agency_id, held.id, replacement, uuid4())
        assert booked.id == new.id and booked.status == "CONFIRMED"


def configure_booking_email(service: SchedulingService, request_id: UUID) -> None:
    from pydantic import SecretStr

    settings = DatabaseSettings(
        app_environment=RuntimeEnvironment.DEVELOPMENT,
        database_url="postgresql://synthetic:synthetic@localhost/development",
        booking_email_enabled=True,
        booking_email_from="sender@example.com",
        resend_api_key=SecretStr("synthetic"),
        resend_webhook_secret=SecretStr("whsec_c3ludGhldGljLXNpZ25pbmcta2V5"),
        _env_file=None,
    )
    service.sessions.configure(info={"integration_settings": settings})
    with service.sessions() as session, session.begin():
        row = session.get(HvacServiceRequest, request_id)
        assert row
        row.customer_details = {
            **row.customer_details,
            "email": "recipient@example.com",
        }


def test_cancelled_booking_suppresses_confirmation_and_reminder(
    migrated_database: Engine,
) -> None:
    service, agency_id, request = configure(migrated_database)
    configure_booking_email(service, request.service_request_id)
    held = service.reserve(agency_id, request, uuid4())
    service.confirm(agency_id, held.id, True, uuid4())
    service.cancel(agency_id, held.id, uuid4())
    with service.sessions() as session:
        rows = {
            row.kind: row
            for row in session.scalars(
                select(BookingNotification).where(
                    BookingNotification.appointment_id == held.id
                )
            )
        }
        assert rows["CONFIRMATION"].status == rows["REMINDER"].status == "SKIPPED"
        assert rows["CANCELLATION"].status == "PENDING"


def test_concurrent_email_workers_send_a_single_provider_request(
    migrated_database: Engine,
) -> None:
    service, agency_id, request = configure(migrated_database)
    configure_booking_email(service, request.service_request_id)
    held = service.reserve(agency_id, request, uuid4())
    service.confirm(agency_id, held.id, True, uuid4())
    with service.sessions() as session:
        notification_id = session.scalar(
            select(BookingNotification.id).where(
                BookingNotification.appointment_id == held.id,
                BookingNotification.kind == "CONFIRMATION",
            )
        )
        assert notification_id
    with patch.object(
        ResendBookingEmail,
        "send",
        return_value=("ACCEPTED", "synthetic-email-" + str(uuid4())),
    ) as send:
        with ThreadPoolExecutor(max_workers=2) as executor:
            list(
                executor.map(
                    lambda _: deliver_notification(service.sessions, notification_id),
                    range(2),
                )
            )
    send.assert_called_once()
    with service.sessions() as session:
        row = session.get(BookingNotification, notification_id)
        assert row and row.status == "ACCEPTED" and row.first_attempt_at


def test_unknown_email_outcome_stops_before_provider_deduplication_expires(
    migrated_database: Engine,
) -> None:
    service, agency_id, request = configure(migrated_database)
    configure_booking_email(service, request.service_request_id)
    held = service.reserve(agency_id, request, uuid4())
    service.confirm(agency_id, held.id, True, uuid4())
    with service.sessions() as session, session.begin():
        notification = session.scalar(
            select(BookingNotification).where(
                BookingNotification.appointment_id == held.id,
                BookingNotification.kind == "CONFIRMATION",
            )
        )
        assert notification
        notification.first_attempt_at = datetime.now(UTC) - timedelta(hours=24)
        notification_id = notification.id
    with patch.object(ResendBookingEmail, "send") as send:
        deliver_notification(service.sessions, notification_id)
    send.assert_not_called()
    with service.sessions() as session:
        notification = session.get(BookingNotification, notification_id)
        assert notification and notification.status == "UNKNOWN"


def test_out_of_order_email_webhooks_do_not_hide_delivery_failure(
    migrated_database: Engine,
) -> None:
    service, agency_id, request = configure(migrated_database)
    configure_booking_email(service, request.service_request_id)
    held = service.reserve(agency_id, request, uuid4())
    service.confirm(agency_id, held.id, True, uuid4())
    reference = "synthetic-email-" + str(uuid4())
    with service.sessions() as session, session.begin():
        notification = session.scalar(
            select(BookingNotification).where(
                BookingNotification.appointment_id == held.id,
                BookingNotification.kind == "CONFIRMATION",
            )
        )
        assert notification
        notification.status, notification.provider_reference = "ACCEPTED", reference
        session.add_all(
            [
                BookingEmailEvent(
                    id=str(uuid4()),
                    provider_reference=reference,
                    status=status,
                    occurred_at=datetime.now(UTC),
                )
                for status in ["BOUNCED", "DELIVERED", "ACCEPTED"]
            ]
        )
        session.flush()
        apply_delivery_events(session)
        assert notification.delivery_status == "BOUNCED"


def test_calendar_oauth_is_browser_bound_expiring_and_single_use(
    migrated_database: Engine,
) -> None:
    from cryptography.fernet import Fernet
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from pydantic import SecretStr

    from insurance_operations.actors import ActorContext
    from insurance_operations.database.models.booking_integrations import (
        CalendarAuthorization,
    )
    from insurance_operations.database.models.identity import AgencyMembership, AppUser
    from insurance_operations.hvac.google_connection import GoogleOAuth, digest
    from insurance_operations.hvac.integration_routes import (
        PREFIX,
        create_booking_integration_router,
    )
    from insurance_operations.settings import ApiSettings

    service, agency_id, _ = configure(migrated_database)
    with service.sessions() as session, session.begin():
        user = AppUser(
            auth_subject=uuid4(), display_name="Synthetic operator", status="ACTIVE"
        )
        session.add(user)
        session.flush()
        session.add(
            AgencyMembership(agency_id=agency_id, app_user_id=user.id, status="ACTIVE")
        )
        actor_id = user.id
    actor = ActorContext(
        actor_id, "Synthetic operator", agency_id, "Synthetic business", "DEVELOPMENT"
    )
    settings = ApiSettings(
        app_environment=RuntimeEnvironment.DEVELOPMENT,
        database_url="postgresql://synthetic:synthetic@localhost/development",
        api_host="localhost",
        api_port=8000,
        web_origin="http://localhost:3000",
        google_calendar_enabled=True,
        google_client_id="synthetic-client",
        google_client_secret=SecretStr("synthetic-secret"),
        google_redirect_uri="http://localhost:8000" + PREFIX + "/google/callback",
        calendar_token_encryption_key=SecretStr(Fernet.generate_key().decode()),
        _env_file=None,
    )
    app = FastAPI()
    app.include_router(
        create_booking_integration_router(settings, service.sessions, lambda: actor)
    )
    client = TestClient(app)
    grant = client.post(
        PREFIX + "/google/authorize",
        json={"team_key": "team-a", "calendar_id": "primary"},
    ).json()
    with service.sessions() as session:
        record = session.scalar(
            select(CalendarAuthorization).where(
                CalendarAuthorization.agency_id == agency_id
            )
        )
        assert record and record.state_digest == digest(grant["state"])
        assert record.browser_digest != grant["browser_secret"]
    with patch.object(GoogleOAuth, "tokens") as exchange:
        response = client.get(
            PREFIX + "/google/callback",
            params={"state": grant["state"], "code": "synthetic"},
        )
        assert "expired" in response.text
        exchange.assert_not_called()
        with pytest.raises(ApiError):
            client.post(
                PREFIX + "/google/launch",
                data={
                    "state": grant["state"],
                    "browser_secret": grant["browser_secret"],
                },
                headers={"Origin": "https://untrusted.example.com"},
            )
        response = client.post(
            PREFIX + "/google/launch",
            data={"state": grant["state"], "browser_secret": grant["browser_secret"]},
            headers={"Origin": settings.web_origin},
            follow_redirects=False,
        )
        assert response.status_code == 303 and response.headers["location"].startswith(
            "https://accounts.google.com/"
        )
        response = client.get(
            PREFIX + "/google/callback",
            params={"state": grant["state"], "error": "access_denied"},
        )
        assert (
            "not completed" in response.text
            and response.headers["Cache-Control"] == "no-store"
        )
        replay = client.get(
            PREFIX + "/google/callback",
            params={"state": grant["state"], "code": "synthetic"},
        )
        assert "expired" in replay.text
        exchange.assert_not_called()
    with service.sessions() as session:
        assert (
            session.scalar(
                select(CalendarAuthorization).where(
                    CalendarAuthorization.agency_id == agency_id
                )
            )
            is None
        )


def test_external_calendar_drift_blocks_email_delivery(
    migrated_database: Engine,
) -> None:
    service, agency_id, request = configure(migrated_database)
    configure_booking_email(service, request.service_request_id)
    provider = connect_synthetic_calendar(service, agency_id)
    with patch("insurance_operations.hvac.calendar_sync.calendar_adapter") as adapters:
        adapters.return_value.__enter__.return_value = provider
        held = service.reserve(agency_id, request, uuid4())
        service.confirm(agency_id, held.id, True, uuid4())
        with service.sessions() as session:
            notification_id = session.scalar(
                select(BookingNotification.id).where(
                    BookingNotification.appointment_id == held.id,
                    BookingNotification.kind == "CONFIRMATION",
                )
            )
            assert notification_id
        provider.verify.side_effect = CalendarConflict("synthetic external edit")
        with patch.object(ResendBookingEmail, "send") as send:
            deliver_notification(service.sessions, notification_id)
        send.assert_not_called()
    with service.sessions() as session:
        binding = session.get(CalendarBooking, held.id)
        notification = session.get(BookingNotification, notification_id)
        assert binding and binding.status == "ATTENTION"
        assert (
            notification
            and notification.status == "PENDING"
            and notification.first_attempt_at is None
        )


def test_calendar_binding_cannot_reference_another_tenants_booking(
    migrated_database: Engine,
) -> None:
    from sqlalchemy.exc import IntegrityError

    service, agency_id, request = configure(migrated_database)
    held = service.reserve(agency_id, request, uuid4())
    other_service, other_agency_id, _ = configure(migrated_database)
    connect_synthetic_calendar(other_service, other_agency_id)
    with service.sessions() as session:
        connection_id = session.scalar(
            select(CalendarConnection.id).where(
                CalendarConnection.agency_id == other_agency_id
            )
        )
        assert connection_id
    with pytest.raises(IntegrityError), service.sessions() as session, session.begin():
        session.add(
            CalendarBooking(
                agency_id=agency_id,
                appointment_id=held.id,
                connection_id=connection_id,
                status="PENDING",
                next_attempt_at=datetime.now(UTC),
            )
        )
