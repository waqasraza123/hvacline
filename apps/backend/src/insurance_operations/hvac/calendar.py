from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from urllib.parse import quote
from uuid import UUID

import httpx


class CalendarUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class BusyPeriod:
    starts_at: datetime
    ends_at: datetime


class CalendarAdapter(Protocol):
    def busy(self, starts_at: datetime, ends_at: datetime) -> list[BusyPeriod]: ...

    def publish(
        self, appointment_id: UUID, starts_at: datetime, ends_at: datetime
    ) -> str: ...

    def cancel(self, event_id: str) -> None: ...


class GoogleCalendarAdapter:
    def __init__(
        self, *, calendar_id: str, access_token: Callable[[], str], client: httpx.Client
    ) -> None:
        self.calendar_id = calendar_id
        self.access_token = access_token
        self.client = client

    def _request(
        self, method: str, path: str, payload: dict[str, object] | None = None
    ) -> httpx.Response:
        try:
            return self.client.request(
                method,
                "https://www.googleapis.com/calendar/v3" + path,
                headers={"Authorization": "Bearer " + self.access_token()},
                json=payload,
                timeout=10,
            )
        except httpx.HTTPError as error:
            raise CalendarUnavailable("The calendar provider is unavailable") from error

    def busy(self, starts_at: datetime, ends_at: datetime) -> list[BusyPeriod]:
        response = self._request(
            "POST",
            "/freeBusy",
            {
                "timeMin": starts_at.isoformat(),
                "timeMax": ends_at.isoformat(),
                "items": [{"id": self.calendar_id}],
            },
        )
        try:
            response.raise_for_status()
            calendar = response.json()["calendars"][self.calendar_id]
            if calendar.get("errors") or not isinstance(calendar.get("busy"), list):
                raise ValueError("calendar availability is unknown")
            periods = [
                BusyPeriod(
                    datetime.fromisoformat(row["start"].replace("Z", "+00:00")),
                    datetime.fromisoformat(row["end"].replace("Z", "+00:00")),
                )
                for row in calendar["busy"]
            ]
            if any(
                period.starts_at.utcoffset() is None
                or period.ends_at.utcoffset() is None
                or period.starts_at >= period.ends_at
                for period in periods
            ):
                raise ValueError("calendar period is invalid")
            return periods
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as error:
            raise CalendarUnavailable(
                "Calendar availability could not be verified"
            ) from error

    def publish(
        self, appointment_id: UUID, starts_at: datetime, ends_at: datetime
    ) -> str:
        event_id = appointment_id.hex
        path = "/calendars/" + quote(self.calendar_id, safe="") + "/events"
        response = self._request(
            "POST",
            path,
            {
                "id": event_id,
                "summary": "HVAC service appointment",
                "start": {"dateTime": starts_at.isoformat()},
                "end": {"dateTime": ends_at.isoformat()},
                "extendedProperties": {
                    "private": {"hvacline_appointment_id": str(appointment_id)}
                },
            },
        )
        if response.status_code == 409:
            response = self._request("GET", path + "/" + event_id)
        try:
            response.raise_for_status()
            data = response.json()
            if data.get("id") != event_id or data.get("status") != "confirmed":
                raise ValueError("provider event was not confirmed")
            if data.get("extendedProperties", {}).get("private", {}).get(
                "hvacline_appointment_id"
            ) != str(appointment_id):
                raise ValueError("provider event identity does not match")
            actual_start = datetime.fromisoformat(
                data["start"]["dateTime"].replace("Z", "+00:00")
            )
            actual_end = datetime.fromisoformat(
                data["end"]["dateTime"].replace("Z", "+00:00")
            )
            if actual_start != starts_at or actual_end != ends_at:
                raise ValueError("provider event times do not match")
            return event_id
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as error:
            raise CalendarUnavailable(
                "Calendar event confirmation could not be verified"
            ) from error

    def cancel(self, event_id: str) -> None:
        response = self._request(
            "DELETE",
            "/calendars/"
            + quote(self.calendar_id, safe="")
            + "/events/"
            + quote(event_id, safe=""),
        )
        if response.status_code not in {204, 404, 410}:
            raise CalendarUnavailable(
                "Calendar event cancellation could not be verified"
            )
