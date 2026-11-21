import json
from dataclasses import dataclass, field
from datetime import UTC, datetime, time, timedelta
from unittest.mock import patch
from uuid import uuid4
from zoneinfo import ZoneInfo

import httpx
import pytest

from insurance_operations.customers import CustomerAddressInput, CustomerInput
from insurance_operations.database.models.ghl import GhlCalendarBooking
from insurance_operations.database.models.hvac import Appointment
from insurance_operations.errors import ApiError
from insurance_operations.ghl.booking import GhlBookingService
from insurance_operations.ghl.provider import GhlError
from insurance_operations.ghl.schemas import (
    BookingRecoveryInput,
    CalendarRoute,
    RetryInput,
    VoiceConfigurationInput,
)
from insurance_operations.hvac.schemas import (
    AvailabilityInput,
    ReservationInput,
    ScheduleInput,
    ServiceDetails,
    ServiceKind,
    ServiceRequestInput,
)
from insurance_operations.hvac.service import SchedulingService
from tests.database.test_ghl import Harness, Remote, configuration, harness as harness


@dataclass
class VoiceRemote(Remote):
    slots: list[datetime] = field(default_factory=list)
    events: dict[str, dict[str, object]] = field(default_factory=dict)
    notes: dict[str, dict[str, object]] = field(default_factory=dict)
    lose_event_response: bool = False
    lose_note_response: bool = False

    def handle(self, request: httpx.Request) -> httpx.Response:
        path, method = request.url.path, request.method
        if path == "/calendars/calendar":
            return httpx.Response(
                200,
                json={
                    "calendar": {
                        "id": "calendar",
                        "locationId": "location",
                        "name": "Synthetic calendar",
                        "isActive": True,
                        "calendarType": "personal",
                        "slotDuration": 60,
                        "slotDurationUnit": "mins",
                    }
                },
            )
        if path == "/calendars/calendar/free-slots":
            return httpx.Response(
                200,
                json={
                    value.astimezone(ZoneInfo("America/New_York")).date().isoformat(): {
                        "slots": [value.isoformat()]
                    }
                    for value in self.slots
                },
            )
        if path == "/calendars/events/appointments" and method == "POST":
            identifier = f"event-{len(self.events) + 1}"
            self.events[identifier] = {**json.loads(request.content), "id": identifier}
            self.slots = []
            if self.lose_event_response:
                self.lose_event_response = False
                return httpx.Response(503)
            return httpx.Response(200, json=self.events[identifier])
        if path.startswith("/calendars/events/appointments/"):
            return httpx.Response(
                200, json={"event": self.events[path.rsplit("/", 1)[1]]}
            )
        if path == "/notes" and method == "POST":
            body = json.loads(request.content)
            identifier = f"note-{len(self.notes) + 1}"
            self.notes[identifier] = {
                **body,
                "id": identifier,
                "contactId": body["relations"][0]["recordId"],
            }
            if self.lose_note_response:
                self.lose_note_response = False
                return httpx.Response(503)
            return httpx.Response(201, json={"note": self.notes[identifier]})
        if path.startswith("/notes/"):
            return httpx.Response(
                200, json={"note": self.notes[path.rsplit("/", 1)[1]]}
            )
        return super().handle(request)


def prepare(
    owner: Harness,
) -> tuple[VoiceRemote, SchedulingService, GhlBookingService, ReservationInput]:
    remote = VoiceRemote()
    owner.remote = remote
    owner.service.factory = remote.factory
    owner.service.connect(owner.owner, configuration())
    scheduling = SchedulingService(owner.sessions)
    schedule = ScheduleInput.model_validate(
        {
            "expected_version": 0,
            "enabled": True,
            "timezone": "America/New_York",
            "postal_codes": ["10001"],
            "windows": [
                {"weekday": day, "start": "09:00", "end": "17:00"} for day in range(7)
            ],
            "teams": [
                {
                    "key": "team",
                    "name": "Synthetic team",
                    "windows": [
                        {"weekday": day, "start": "09:00", "end": "17:00"}
                        for day in range(7)
                    ],
                }
            ],
            "duration_minutes": 60,
            "notice_minutes": 0,
        }
    )
    scheduling.configure(owner.owner.agency_id, schedule, uuid4())
    voice = GhlBookingService(owner.sessions, remote.factory)
    voice.configure(
        owner.owner,
        VoiceConfigurationInput(
            expected_version=0,
            calendars=[CalendarRoute(team_key="team", calendar_id="calendar")],
        ),
        owner.service.settings,
    )
    day = (datetime.now(ZoneInfo("America/New_York")) + timedelta(days=3)).date()
    start = datetime.combine(day, time(9), ZoneInfo("America/New_York")).astimezone(UTC)
    remote.slots = [start]
    request_id = scheduling.create_request(
        owner.owner.agency_id,
        ServiceRequestInput(
            customer=CustomerInput(
                full_name="Synthetic caller",
                phone="+12025550123",
                address=CustomerAddressInput(
                    line1="1 Example Street",
                    city="New York",
                    state_code="NY",
                    postal_code="10001",
                    country_code="US",
                ),
            ),
            service=ServiceDetails(
                kind=ServiceKind.AC_REPAIR,
                equipment_issue="Synthetic cooling issue",
                preferred_window="Morning",
            ),
            explicit_confirmation=True,
        ),
        uuid4(),
    )
    return (
        remote,
        scheduling,
        voice,
        ReservationInput(
            service_request_id=request_id,
            team_key="team",
            starts_at=start,
            idempotency_key=f"synthetic-{uuid4()}",
        ),
    )


def test_ghl_confirm_is_idempotent_and_uses_only_returned_availability(
    harness: Harness,
) -> None:
    remote, scheduling, _, request = prepare(harness)
    with patch("insurance_operations.ghl.booking.open_provider", remote.factory):
        available = scheduling.availability(
            harness.owner.agency_id,
            AvailabilityInput(
                postal_code="10001",
                day=request.starts_at.astimezone(ZoneInfo("America/New_York")).date(),
            ),
        )
        assert [slot.starts_at for slot in available.slots] == [request.starts_at]
        held = scheduling.reserve(harness.owner.agency_id, request, uuid4())
        assert not remote.events
        result = scheduling.confirm(harness.owner.agency_id, held.id, True, uuid4())
        repeated = scheduling.confirm(harness.owner.agency_id, held.id, True, uuid4())
    assert result.status == repeated.status == "CONFIRMED"
    assert len(remote.events) == 1
    with harness.sessions() as session:
        binding = session.get(GhlCalendarBooking, held.id)
        assert (
            binding and binding.status == "CONFIRMED" and binding.event_id == "event-1"
        )


def test_lost_create_response_blocks_duplicate_even_after_hold_expiry_and_recovers(
    harness: Harness,
) -> None:
    remote, scheduling, voice, request = prepare(harness)
    with patch("insurance_operations.ghl.booking.open_provider", remote.factory):
        held = scheduling.reserve(harness.owner.agency_id, request, uuid4())
        remote.lose_event_response = True
        with pytest.raises(ApiError):
            scheduling.confirm(harness.owner.agency_id, held.id, True, uuid4())
        with pytest.raises(ApiError, match="GHL|booking"):
            scheduling.confirm(harness.owner.agency_id, held.id, True, uuid4())
    assert len(remote.events) == 1
    with harness.sessions() as session, session.begin():
        row = session.get(Appointment, held.id)
        assert row is not None
        row.hold_expires_at = datetime.now(UTC) - timedelta(seconds=1)
    with harness.sessions() as session:
        assert [
            row.id
            for row in scheduling._busy(
                session, harness.owner.agency_id, datetime.now(UTC)
            )
        ] == [held.id]
    voice.recover(
        harness.owner, held.id, BookingRecoveryInput(remote_event_id="event-1")
    )
    with harness.sessions() as session:
        row = session.get(Appointment, held.id)
        assert row and row.status == "CONFIRMED"
    assert len(remote.events) == 1


def test_declined_confirmation_and_hazard_never_create_ghl_appointments(
    harness: Harness,
) -> None:
    remote, scheduling, _, request = prepare(harness)
    with patch("insurance_operations.ghl.booking.open_provider", remote.factory):
        held = scheduling.reserve(harness.owner.agency_id, request, uuid4())
        with pytest.raises(ApiError):
            scheduling.confirm(harness.owner.agency_id, held.id, False, uuid4())
        scheduling.flag_hazard(
            harness.owner.agency_id, request.service_request_id, uuid4()
        )
        with pytest.raises(ApiError):
            scheduling.confirm(harness.owner.agency_id, held.id, True, uuid4())
    assert not remote.contacts and not remote.events


def test_foreign_booking_recovery_and_wrong_contact_are_rejected(
    harness: Harness,
) -> None:
    remote, scheduling, voice, request = prepare(harness)
    with patch("insurance_operations.ghl.booking.open_provider", remote.factory):
        held = scheduling.reserve(harness.owner.agency_id, request, uuid4())
        remote.lose_event_response = True
        with pytest.raises(ApiError):
            scheduling.confirm(harness.owner.agency_id, held.id, True, uuid4())
    with pytest.raises(ApiError) as foreign:
        voice.recover(
            harness.foreign, held.id, BookingRecoveryInput(remote_event_id="event-1")
        )
    assert foreign.value.status_code == 404
    remote.events["event-1"]["contactId"] = "foreign"
    with pytest.raises(GhlError, match="OWNERSHIP_INVALID"):
        voice.recover(
            harness.owner, held.id, BookingRecoveryInput(remote_event_id="event-1")
        )


def test_summary_timeout_requires_review_and_links_existing_note_without_duplicate(
    harness: Harness,
) -> None:
    remote, _, voice, _ = prepare(harness)
    voice.configure(
        harness.owner,
        VoiceConfigurationInput(
            expected_version=1,
            calendars=[CalendarRoute(team_key="team", calendar_id="calendar")],
            contact_notes=True,
            note_user_id="author",
        ),
        harness.service.settings,
    )
    lead_id = harness.lead()
    remote.lose_note_response = True
    delivered = harness.deliver(lead_id)
    assert delivered.note_unknown
    harness.due(lead_id)
    delivered = harness.deliver(lead_id)
    assert delivered.status == "NEEDS_REVIEW" and len(remote.notes) == 1
    harness.service.retry(
        harness.owner, delivered.id, RetryInput(remote_note_id="note-1")
    )
    delivered = harness.deliver(lead_id)
    assert delivered.status == "SYNCED" and delivered.note_id == "note-1"
    assert len(remote.notes) == 1


def test_response_after_remote_create_survives_local_finalization_rollback(
    harness: Harness,
) -> None:
    remote, scheduling, _, request = prepare(harness)
    with patch("insurance_operations.ghl.booking.open_provider", remote.factory):
        held = scheduling.reserve(harness.owner.agency_id, request, uuid4())
        with patch(
            "insurance_operations.ghl.booking.enqueue_booking_notifications",
            side_effect=RuntimeError("synthetic interruption"),
        ):
            with pytest.raises(RuntimeError):
                scheduling.confirm(harness.owner.agency_id, held.id, True, uuid4())
        with harness.sessions() as session:
            row = session.get(Appointment, held.id)
            binding = session.get(GhlCalendarBooking, held.id)
            assert row and row.status == "HELD"
            assert binding and binding.event_id == "event-1"
        recovered = scheduling.confirm(harness.owner.agency_id, held.id, True, uuid4())
    assert recovered.status == "CONFIRMED" and len(remote.events) == 1


def test_slot_taken_after_reservation_is_not_booked_and_hold_can_be_released(
    harness: Harness,
) -> None:
    remote, scheduling, _, request = prepare(harness)
    with patch("insurance_operations.ghl.booking.open_provider", remote.factory):
        held = scheduling.reserve(harness.owner.agency_id, request, uuid4())
        remote.slots = []
        with pytest.raises(ApiError) as rejected:
            scheduling.confirm(harness.owner.agency_id, held.id, True, uuid4())
        assert rejected.value.code == "GHL_SLOT_UNAVAILABLE"
        released = scheduling.release_hold(harness.owner.agency_id, held.id, uuid4())
    assert released.status == "CANCELLED" and not remote.events


def test_mapping_change_and_disconnect_are_blocked_for_active_reservations(
    harness: Harness,
) -> None:
    remote, scheduling, voice, request = prepare(harness)
    with patch("insurance_operations.ghl.booking.open_provider", remote.factory):
        scheduling.reserve(harness.owner.agency_id, request, uuid4())
    with pytest.raises(ApiError) as changed:
        voice.configure(
            harness.owner,
            VoiceConfigurationInput(expected_version=1),
            harness.service.settings,
        )
    assert changed.value.code == "GHL_CALENDAR_IN_USE"
    with pytest.raises(ApiError) as disconnected:
        harness.service.action(harness.owner, "disconnect")
    assert disconnected.value.code == "GHL_CALENDAR_IN_USE"
