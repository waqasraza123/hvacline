from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest

from insurance_operations.hvac.calendar import (
    CalendarUnavailable,
    GoogleCalendarAdapter,
)


def test_google_calendar_errors_fail_closed_instead_of_returning_free_time() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200, json={"calendars": {"team": {"errors": [{"reason": "notFound"}]}}}
        )
    )
    with httpx.Client(transport=transport) as client:
        adapter = GoogleCalendarAdapter(
            calendar_id="team", access_token=lambda: "synthetic", client=client
        )
        with pytest.raises(CalendarUnavailable):
            adapter.busy(
                datetime(2026, 10, 26, 14, tzinfo=UTC),
                datetime(2026, 10, 26, 15, tzinfo=UTC),
            )


def test_google_duplicate_event_is_verified_before_success() -> None:
    appointment_id = uuid4()
    start = datetime(2026, 10, 26, 14, tzinfo=UTC)
    end = datetime(2026, 10, 26, 15, tzinfo=UTC)

    def respond(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(409)
        return httpx.Response(
            200,
            json={
                "id": appointment_id.hex,
                "status": "confirmed",
                "start": {"dateTime": start.isoformat()},
                "end": {"dateTime": end.isoformat()},
                "extendedProperties": {
                    "private": {"hvacline_appointment_id": str(appointment_id)}
                },
            },
        )

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        adapter = GoogleCalendarAdapter(
            calendar_id="team", access_token=lambda: "synthetic", client=client
        )
        assert adapter.publish(appointment_id, start, end) == appointment_id.hex
