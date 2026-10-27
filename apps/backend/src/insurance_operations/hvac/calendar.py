from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, time
from typing import Protocol
from urllib.parse import quote
from uuid import UUID
from zoneinfo import ZoneInfo

import httpx


class CalendarUnavailable(RuntimeError):
    pass


class CalendarConflict(CalendarUnavailable):
    pass


class CalendarAuthorizationRequired(CalendarUnavailable):
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
        self,
        method: str,
        path: str,
        payload: dict[str, object] | None = None,
        *,
        params: dict[str, str] | None = None,
        etag: str | None = None,
    ) -> httpx.Response:
        try:
            headers = {"Authorization": "Bearer " + self.access_token()}
            if etag:
                headers["If-Match"] = etag
            response = self.client.request(
                method,
                "https://www.googleapis.com/calendar/v3" + path,
                headers=headers,
                json=payload,
                params=params,
                timeout=10,
            )
            if response.status_code == 403:
                try:
                    reasons = {
                        row.get("reason")
                        for row in response.json().get("error", {}).get("errors", [])
                    }
                except (ValueError, AttributeError, TypeError):
                    reasons = set()
                if reasons & {
                    "rateLimitExceeded",
                    "userRateLimitExceeded",
                    "quotaExceeded",
                    "dailyLimitExceeded",
                }:
                    raise CalendarUnavailable(
                        "The calendar provider is temporarily rate limited"
                    )
            if response.status_code in {401, 403}:
                raise CalendarAuthorizationRequired("Calendar access must be restored")
            return response
        except httpx.HTTPError as error:
            raise CalendarUnavailable("The calendar provider is unavailable") from error

    def event(self, appointment_id: UUID) -> dict[str, object] | None:
        response = self._request(
            "GET",
            "/calendars/"
            + quote(self.calendar_id, safe="")
            + "/events/"
            + appointment_id.hex,
        )
        if response.status_code in {404, 410}:
            return None
        try:
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict):
                raise ValueError("invalid event")
            return data
        except (httpx.HTTPError, ValueError) as error:
            raise CalendarUnavailable("Calendar event could not be read") from error

    def verify(
        self, appointment_id: UUID, starts_at: datetime, ends_at: datetime
    ) -> None:
        data = self.event(appointment_id)
        if data is None:
            raise CalendarConflict("Calendar event is missing")
        self._verify(data, appointment_id, starts_at, ends_at)

    @staticmethod
    def _verify(
        data: dict[str, object],
        appointment_id: UUID,
        starts_at: datetime,
        ends_at: datetime,
    ) -> None:
        try:
            private = data.get("extendedProperties", {})
            if not isinstance(private, dict):
                raise ValueError("event ownership is unavailable")
            private = private.get("private", {})
            if not isinstance(private, dict):
                raise ValueError("event ownership is unavailable")
            start, end = data["start"], data["end"]
            if not isinstance(start, dict) or not isinstance(end, dict):
                raise ValueError("event times are unavailable")
            if (
                data.get("id") != appointment_id.hex
                or data.get("status") != "confirmed"
                or private.get("hvacline_appointment_id") != str(appointment_id)
                or data.get("transparency", "opaque") != "opaque"
                or datetime.fromisoformat(str(start["dateTime"]).replace("Z", "+00:00"))
                != starts_at
                or datetime.fromisoformat(str(end["dateTime"]).replace("Z", "+00:00"))
                != ends_at
            ):
                raise ValueError("event differs")
        except (ValueError, KeyError, TypeError) as error:
            raise CalendarConflict(
                "Calendar event was changed; staff review is required"
            ) from error

    def busy_events(
        self,
        starts_at: datetime,
        ends_at: datetime,
        exclude_ids: frozenset[str] = frozenset(),
    ) -> list[BusyPeriod]:
        periods: list[BusyPeriod] = []
        params = {
            "timeMin": starts_at.isoformat(),
            "timeMax": ends_at.isoformat(),
            "singleEvents": "true",
            "showDeleted": "false",
            "maxResults": "2500",
        }
        seen: set[str] = set()
        for _ in range(100):
            response = self._request(
                "GET",
                "/calendars/" + quote(self.calendar_id, safe="") + "/events",
                params=params,
            )
            try:
                response.raise_for_status()
                data = response.json()
                rows = data["items"]
                if not isinstance(rows, list):
                    raise ValueError("invalid events")
                timezone = ZoneInfo(data["timeZone"])
                for row in rows:
                    if (
                        row.get("status") == "cancelled"
                        or row.get("transparency") == "transparent"
                        or row.get("id") in exclude_ids
                    ):
                        continue

                    def boundary(value: dict[str, str]) -> datetime:
                        if "dateTime" in value:
                            parsed = datetime.fromisoformat(
                                value["dateTime"].replace("Z", "+00:00")
                            )
                            if parsed.utcoffset() is None:
                                raise ValueError("missing offset")
                            return parsed
                        return datetime.combine(
                            datetime.fromisoformat(value["date"]).date(),
                            time.min,
                            timezone,
                        )

                    start, end = boundary(row["start"]), boundary(row["end"])
                    if start >= end:
                        raise ValueError("invalid period")
                    if start < ends_at and end > starts_at:
                        periods.append(BusyPeriod(start, end))
                token = data.get("nextPageToken")
                if token is None:
                    return periods
                if not isinstance(token, str) or not token or token in seen:
                    raise ValueError("invalid pagination")
                seen.add(token)
                params["pageToken"] = token
            except (
                httpx.HTTPError,
                ValueError,
                KeyError,
                TypeError,
                AttributeError,
            ) as error:
                raise CalendarUnavailable(
                    "Calendar availability could not be verified"
                ) from error
        raise CalendarUnavailable("Calendar availability exceeded the safe page limit")

    def cancel_owned(
        self, appointment_id: UUID, starts_at: datetime, ends_at: datetime
    ) -> None:
        data = self.event(appointment_id)
        if data is None or data.get("status") == "cancelled":
            return
        self._verify(data, appointment_id, starts_at, ends_at)
        properties = data.get("extendedProperties")
        private = properties.get("private") if isinstance(properties, dict) else None
        if (
            data.get("id") != appointment_id.hex
            or not isinstance(private, dict)
            or private.get("hvacline_appointment_id") != str(appointment_id)
        ):
            raise CalendarConflict(
                "Calendar event ownership differs; staff review is required"
            )
        etag = data.get("etag")
        if not isinstance(etag, str) or not etag:
            raise CalendarUnavailable("Calendar event version is unavailable")
        response = self._request(
            "DELETE",
            "/calendars/"
            + quote(self.calendar_id, safe="")
            + "/events/"
            + appointment_id.hex,
            etag=etag,
        )
        if response.status_code == 412:
            raise CalendarConflict("Calendar event changed during cancellation")
        if response.status_code not in {204, 404, 410}:
            raise CalendarUnavailable("Calendar cancellation could not be verified")

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
