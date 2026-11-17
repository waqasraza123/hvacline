import json
from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import httpx
import pytest
from pydantic import ValidationError

from insurance_operations.ghl.provider import GhlClient, GhlError
from insurance_operations.ghl.schemas import (
    BookingRecoveryInput,
    CalendarRoute,
    VoiceConfiguration,
)


def test_voice_configuration_rejects_duplicate_routes_and_missing_note_author() -> None:
    with pytest.raises(ValidationError):
        VoiceConfiguration(
            calendars=[
                CalendarRoute(team_key="one", calendar_id="calendar"),
                CalendarRoute(team_key="two", calendar_id="calendar"),
            ]
        )
    with pytest.raises(ValidationError):
        VoiceConfiguration(contact_notes=True)
    with pytest.raises(ValidationError):
        BookingRecoveryInput(remote_event_id="event", confirm_remote_absent=True)
    with pytest.raises(ValidationError):
        BookingRecoveryInput()


def test_free_slots_use_exclusive_next_day_and_validate_offsets() -> None:
    requested: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requested.append(request)
        return httpx.Response(
            200, json={"2026-11-20": {"slots": ["2026-11-20T09:00:00-05:00"]}}
        )

    with httpx.Client(transport=httpx.MockTransport(handle)) as transport:
        slots = GhlClient(transport, "synthetic-private-token", "location").free_slots(
            "calendar", date(2026, 11, 20), "America/New_York"
        )
    assert slots == {datetime(2026, 11, 20, 14, tzinfo=UTC)}
    assert (
        int(requested[0].url.params["endDate"])
        - int(requested[0].url.params["startDate"])
        == 86_400_000
    )


@pytest.mark.parametrize(
    "payload",
    [
        {"2026-11-20": {"slots": ["2026-11-20T09:00:00"]}},
        {"2026-11-21": {"slots": ["2026-11-21T09:00:00-05:00"]}},
        {"error": "unknown calendar"},
        {"2026-11-20": {"slots": "invalid"}},
    ],
)
def test_invalid_availability_never_becomes_a_bookable_slot(
    payload: dict[str, object],
) -> None:
    with httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=payload))
    ) as transport:
        with pytest.raises(GhlError, match="GHL_RESPONSE_INVALID"):
            GhlClient(transport, "synthetic-private-token", "location").free_slots(
                "calendar", date(2026, 11, 20), "America/New_York"
            )


def test_appointment_create_enforces_provider_validation_and_does_not_trigger_workflows() -> (
    None
):
    identifier = uuid4()
    start = datetime(2026, 11, 20, 14, tzinfo=UTC)
    sent: list[dict[str, object]] = []

    def handle(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        sent.append(body)
        return httpx.Response(200, json={**body, "id": "event"})

    with httpx.Client(transport=httpx.MockTransport(handle)) as transport:
        result = GhlClient(
            transport, "synthetic-private-token", "location"
        ).create_appointment(
            identifier, "calendar", "contact", start, start + timedelta(hours=1)
        )
    assert result == "event"
    assert sent[0]["ignoreFreeSlotValidation"] is False
    assert sent[0]["ignoreDateRange"] is False
    assert sent[0]["toNotify"] is False
    assert sent[0]["appointmentStatus"] == "confirmed"
    assert str(identifier) in str(sent[0]["title"])


def test_appointment_response_with_foreign_contact_is_an_uncertain_write() -> None:
    identifier = uuid4()
    start = datetime(2026, 11, 20, 14, tzinfo=UTC)

    def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={**json.loads(request.content), "id": "event", "contactId": "foreign"},
        )

    with httpx.Client(transport=httpx.MockTransport(handle)) as transport:
        with pytest.raises(GhlError) as caught:
            GhlClient(
                transport, "synthetic-private-token", "location"
            ).create_appointment(
                identifier, "calendar", "contact", start, start + timedelta(hours=1)
            )
    assert caught.value.ambiguous


def test_contact_summary_uses_notes_api_with_contact_relation_and_never_retries_a_timeout() -> (
    None
):
    sent: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        raise httpx.ReadTimeout("synthetic timeout")

    with httpx.Client(transport=httpx.MockTransport(handle)) as transport:
        with pytest.raises(GhlError) as caught:
            GhlClient(transport, "synthetic-private-token", "location").create_summary(
                "contact", "user", "reference\nSynthetic summary"
            )
    assert caught.value.ambiguous
    assert len(sent) == 1
    assert sent[0].url.path == "/notes"
    assert sent[0].url.params["locationId"] == "location"
    assert json.loads(sent[0].content)["relations"] == [
        {"objectKey": "contact", "recordId": "contact"}
    ]
