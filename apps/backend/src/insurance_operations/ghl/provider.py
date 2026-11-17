import json
import logging
import math
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from email.utils import parsedate_to_datetime
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

import httpx
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, ValidationError

from insurance_operations.ghl.schemas import ConnectionInput, GhlId

API_ORIGIN = "https://services.leadconnectorhq.com"
API_VERSION = "v3"


class GhlRequestLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return "services.leadconnectorhq.com" not in record.getMessage()


logging.getLogger("httpx").addFilter(GhlRequestLogFilter())


class GhlError(RuntimeError):
    def __init__(
        self,
        code: str,
        *,
        retryable: bool = False,
        connection_error: bool = False,
        ambiguous: bool = False,
        retry_after: int = 0,
    ) -> None:
        super().__init__(code)
        self.code = code
        self.retryable = retryable
        self.connection_error = connection_error
        self.ambiguous = ambiguous
        self.retry_after = retry_after


class RemoteRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: GhlId


class RemoteContact(RemoteRecord):
    locationId: GhlId


class RemoteField(RemoteRecord):
    name: str = Field(max_length=500)
    locationId: GhlId
    model: str
    dataType: str


class RemoteStage(RemoteRecord):
    name: str = Field(max_length=500)


class RemotePipeline(RemoteRecord):
    name: str = Field(max_length=500)
    locationId: GhlId
    stages: list[RemoteStage]


class RemoteOpportunity(RemoteRecord):
    locationId: GhlId
    pipelineId: GhlId
    pipelineStageId: GhlId
    contactId: GhlId
    status: str
    customFields: list[dict[str, Any]] = Field(default_factory=list)

    def field(self, field_id: str) -> object:
        return next(
            (
                item.get("fieldValue")
                for item in self.customFields
                if item.get("id") == field_id
            ),
            None,
        )


class RemoteCalendar(RemoteRecord):
    locationId: GhlId
    name: str = Field(max_length=500)
    isActive: bool
    calendarType: str
    slotDuration: int = Field(gt=0, le=480)
    slotDurationUnit: str
    durationOptions: list[dict[str, Any]] = Field(default_factory=list, max_length=3)

    def require_duration(self, minutes: int) -> None:
        duration = self.slotDuration * (60 if self.slotDurationUnit == "hours" else 1)
        if (
            not self.isActive
            or self.calendarType not in {"personal", "round_robin", "event"}
            or self.slotDurationUnit not in {"mins", "hours"}
            or duration != minutes
            or self.durationOptions
        ):
            raise GhlError("GHL_CALENDAR_CONFIGURATION_INVALID")


class RemoteAppointment(RemoteRecord):
    locationId: GhlId
    calendarId: GhlId
    contactId: GhlId
    title: str
    appointmentStatus: str
    startTime: AwareDatetime
    endTime: AwareDatetime
    deleted: bool = False
    isRecurring: bool = False

    def require_booking(
        self,
        *,
        location_id: str,
        calendar_id: str,
        contact_id: str,
        appointment_id: UUID,
        starts_at: datetime,
        ends_at: datetime,
    ) -> None:
        if (
            self.locationId != location_id
            or self.calendarId != calendar_id
            or self.contactId != contact_id
            or self.title != appointment_title(appointment_id)
            or self.appointmentStatus != "confirmed"
            or self.startTime != starts_at
            or self.endTime != ends_at
            or self.deleted
            or self.isRecurring
        ):
            raise GhlError("GHL_APPOINTMENT_OWNERSHIP_INVALID")


class RemoteNote(RemoteRecord):
    body: str
    userId: GhlId
    contactId: GhlId

    def require_summary(self, contact_id: str, reference: str) -> None:
        if self.contactId != contact_id or not self.body.startswith(reference + "\n"):
            raise GhlError("GHL_NOTE_OWNERSHIP_INVALID")


def appointment_title(identifier: UUID) -> str:
    return f"HVACLine appointment {identifier}"


@dataclass(frozen=True)
class Discovery:
    pipelines: list[RemotePipeline]
    fields: list[RemoteField]


def retry_delay(value: str | None) -> int:
    if not value:
        return 0
    try:
        seconds = float(value)
    except ValueError:
        try:
            parsed = parsedate_to_datetime(value)
            if parsed.tzinfo is None:
                return 60
            seconds = (parsed - datetime.now(UTC)).total_seconds()
        except (ValueError, TypeError, OverflowError):
            return 60
    if not math.isfinite(seconds):
        return 86400
    return max(0, min(86400, math.ceil(seconds)))


class GhlClient:
    def __init__(self, client: httpx.Client, token: str, location_id: str) -> None:
        self.client = client
        self.token = token
        self.location_id = location_id

    def request(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, object] | None = None,
        params: dict[str, str | int] | None = None,
        creating: bool = False,
    ) -> dict[str, Any]:
        try:
            with self.client.stream(
                method,
                API_ORIGIN + path,
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Version": API_VERSION,
                },
                json=body,
                params=params,
                follow_redirects=False,
                timeout=8,
            ) as response:
                status = response.status_code
                if status in {401, 403}:
                    raise GhlError("GHL_AUTH_REQUIRED", connection_error=True)
                if status == 429:
                    raise GhlError(
                        "GHL_RATE_LIMITED",
                        retryable=True,
                        retry_after=retry_delay(response.headers.get("Retry-After")),
                    )
                if status >= 500 or status == 408:
                    raise GhlError(
                        "GHL_TEMPORARILY_UNAVAILABLE",
                        retryable=True,
                        ambiguous=creating,
                    )
                if status == 404:
                    raise GhlError("GHL_RECORD_NOT_FOUND")
                if 300 <= status < 400:
                    raise GhlError(
                        "GHL_RESPONSE_REDIRECTED",
                        ambiguous=creating,
                        connection_error=True,
                    )
                if not 200 <= status < 300:
                    raise GhlError("GHL_REQUEST_REJECTED")
                raw = bytearray()
                for chunk in response.iter_bytes():
                    raw.extend(chunk)
                    if len(raw) > 1_048_576:
                        raise GhlError("GHL_RESPONSE_INVALID", ambiguous=creating)
                try:
                    data = json.loads(raw)
                except (ValueError, UnicodeError):
                    raise GhlError("GHL_RESPONSE_INVALID", ambiguous=creating) from None
                if not isinstance(data, dict):
                    raise GhlError("GHL_RESPONSE_INVALID", ambiguous=creating)
                return data
        except httpx.HTTPError:
            raise GhlError(
                "GHL_NETWORK_UNAVAILABLE", retryable=True, ambiguous=creating
            ) from None

    def discover(self) -> Discovery:
        pipelines = self.request(
            "GET", "/opportunities/pipelines", params={"locationId": self.location_id}
        ).get("pipelines")
        fields = self.request(
            "GET",
            f"/locations/{self.location_id}/customFields",
            params={"model": "opportunity"},
        ).get("customFields")
        try:
            if not isinstance(pipelines, list) or not isinstance(fields, list):
                raise ValueError
            found_pipelines = [RemotePipeline.model_validate(row) for row in pipelines]
            found_fields = [RemoteField.model_validate(row) for row in fields]
        except ValueError:
            raise GhlError("GHL_RESPONSE_INVALID") from None
        if any(row.locationId != self.location_id for row in found_pipelines) or any(
            row.locationId != self.location_id for row in found_fields
        ):
            raise GhlError("GHL_LOCATION_MISMATCH", connection_error=True)
        return Discovery(
            pipelines=found_pipelines,
            fields=[
                row
                for row in found_fields
                if row.model == "opportunity" and row.dataType in {"TEXT", "LARGE_TEXT"}
            ],
        )

    def validate_mapping(self, configuration: ConnectionInput) -> Discovery:
        discovery = self.discover()
        pipeline = next(
            (row for row in discovery.pipelines if row.id == configuration.pipeline_id),
            None,
        )
        if not pipeline or not set(configuration.stages.model_dump().values()) <= {
            row.id for row in pipeline.stages
        }:
            raise GhlError("GHL_STAGE_MAPPING_INVALID", connection_error=True)
        if not set(configuration.fields.model_dump().values()) <= {
            row.id for row in discovery.fields
        }:
            raise GhlError("GHL_FIELD_MAPPING_INVALID", connection_error=True)
        return discovery

    def lookup(self, key: str, value: str) -> list[RemoteContact]:
        data = self.request(
            "GET",
            "/contacts/lookup",
            params={"locationId": self.location_id, key: value, "limit": 2},
        )
        try:
            rows = data["contacts"]
            if not isinstance(rows, list):
                raise ValueError
            contacts = [RemoteContact.model_validate(row) for row in rows]
        except (KeyError, ValueError):
            raise GhlError("GHL_RESPONSE_INVALID") from None
        if data.get("nextCursor") or len(contacts) > 1:
            raise GhlError("GHL_CONTACT_MATCH_AMBIGUOUS")
        if any(row.locationId != self.location_id for row in contacts):
            raise GhlError("GHL_LOCATION_MISMATCH", connection_error=True)
        return contacts

    def match_contact(self, email: str | None, phone: str | None) -> str | None:
        if not email and not phone:
            raise GhlError("GHL_CONTACT_IDENTIFIER_REQUIRED")
        matches: set[str] = set()
        for key, value in (("email", email), ("phone", phone)):
            if value:
                matches.update(row.id for row in self.lookup(key, value))
        if len(matches) > 1:
            raise GhlError("GHL_CONTACT_MATCH_CONFLICT")
        return next(iter(matches), None)

    def create_contact(self, values: dict[str, object]) -> str:
        data = self.request(
            "POST",
            "/contacts/",
            body={**values, "locationId": self.location_id},
            creating=True,
        )
        try:
            contact = RemoteContact.model_validate(data["contact"])
        except (KeyError, ValidationError):
            raise GhlError("GHL_RESPONSE_INVALID", ambiguous=True) from None
        if contact.locationId != self.location_id:
            raise GhlError(
                "GHL_LOCATION_MISMATCH", ambiguous=True, connection_error=True
            )
        return contact.id

    def opportunity(self, identifier: str) -> RemoteOpportunity:
        data = self.request("GET", f"/opportunities/{identifier}")
        try:
            opportunity = RemoteOpportunity.model_validate(data["opportunity"])
        except (KeyError, ValidationError):
            raise GhlError("GHL_RESPONSE_INVALID") from None
        if opportunity.locationId != self.location_id:
            raise GhlError("GHL_LOCATION_MISMATCH", connection_error=True)
        return opportunity

    def find_opportunity(
        self, reference: str, pipeline_id: str, field_id: str
    ) -> RemoteOpportunity | None:
        matches: dict[str, RemoteOpportunity] = {}
        for page in range(1, 21):
            data = self.request(
                "GET",
                "/opportunities/search",
                params={
                    "locationId": self.location_id,
                    "pipelineId": pipeline_id,
                    "query": reference,
                    "status": "all",
                    "limit": 100,
                    "page": page,
                },
            )
            rows = data.get("opportunities")
            if not isinstance(rows, list):
                raise GhlError("GHL_RESPONSE_INVALID")
            try:
                for row in rows:
                    opportunity = RemoteOpportunity.model_validate(row)
                    if opportunity.field(field_id) == reference:
                        if (
                            opportunity.locationId != self.location_id
                            or opportunity.pipelineId != pipeline_id
                        ):
                            raise GhlError("GHL_OPPORTUNITY_OWNERSHIP_INVALID")
                        matches[opportunity.id] = opportunity
            except ValidationError:
                raise GhlError("GHL_RESPONSE_INVALID") from None
            if len(matches) > 1:
                raise GhlError("GHL_OPPORTUNITY_MATCH_AMBIGUOUS")
            meta = data.get("meta")
            if not isinstance(meta, dict):
                raise GhlError("GHL_RESPONSE_INVALID")
            if not meta.get("nextPage") and not meta.get("nextPageUrl"):
                return next(iter(matches.values()), None)
        raise GhlError("GHL_RECONCILIATION_LIMIT")

    def create_opportunity(self, values: dict[str, object]) -> str:
        data = self.request(
            "POST",
            "/opportunities/",
            body={**values, "locationId": self.location_id},
            creating=True,
        )
        try:
            return str(RemoteRecord.model_validate(data["opportunity"]).id)
        except (KeyError, ValidationError):
            raise GhlError("GHL_RESPONSE_INVALID", ambiguous=True) from None

    def update_opportunity(self, identifier: str, values: dict[str, object]) -> None:
        self.request("PUT", f"/opportunities/{identifier}", body=values)

    def calendar(self, identifier: str) -> RemoteCalendar:
        data = self.request("GET", f"/calendars/{identifier}")
        try:
            calendar = RemoteCalendar.model_validate(data["calendar"])
        except (KeyError, ValueError):
            raise GhlError("GHL_RESPONSE_INVALID") from None
        if calendar.id != identifier or calendar.locationId != self.location_id:
            raise GhlError("GHL_LOCATION_MISMATCH", connection_error=True)
        return calendar

    def free_slots(self, calendar_id: str, day: date, timezone: str) -> set[datetime]:
        start = datetime.combine(day, time.min, ZoneInfo(timezone))
        end = datetime.combine(day + timedelta(days=1), time.min, ZoneInfo(timezone))
        data = self.request(
            "GET",
            f"/calendars/{calendar_id}/free-slots",
            params={
                "startDate": int(start.timestamp() * 1000),
                "endDate": int(end.timestamp() * 1000),
                "timezone": timezone,
            },
        )
        slots: set[datetime] = set()
        try:
            for key, value in data.items():
                if key == "traceId":
                    continue
                if date.fromisoformat(key) != day or not isinstance(value, dict):
                    raise ValueError
                values = value["slots"]
                if not isinstance(values, list) or len(values) > 1440:
                    raise ValueError
                for raw in values:
                    if not isinstance(raw, str):
                        raise ValueError
                    parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                    if parsed.utcoffset() is None or not start <= parsed < end:
                        raise ValueError
                    slots.add(parsed.astimezone(UTC))
        except (KeyError, TypeError, ValueError):
            raise GhlError("GHL_RESPONSE_INVALID") from None
        return slots

    def create_appointment(
        self,
        identifier: UUID,
        calendar_id: str,
        contact_id: str,
        starts_at: datetime,
        ends_at: datetime,
    ) -> str:
        data = self.request(
            "POST",
            "/calendars/events/appointments",
            body={
                "locationId": self.location_id,
                "calendarId": calendar_id,
                "contactId": contact_id,
                "title": appointment_title(identifier),
                "startTime": starts_at.isoformat(),
                "endTime": ends_at.isoformat(),
                "appointmentStatus": "confirmed",
                "toNotify": False,
                "ignoreDateRange": False,
                "ignoreFreeSlotValidation": False,
            },
            creating=True,
        )
        try:
            result = RemoteAppointment.model_validate(data)
            result.require_booking(
                location_id=self.location_id,
                calendar_id=calendar_id,
                contact_id=contact_id,
                appointment_id=identifier,
                starts_at=starts_at,
                ends_at=ends_at,
            )
        except ValueError:
            raise GhlError("GHL_RESPONSE_INVALID", ambiguous=True) from None
        except GhlError as error:
            raise GhlError(error.code, ambiguous=True) from None
        return result.id

    def appointment(self, identifier: str) -> RemoteAppointment:
        data = self.request("GET", f"/calendars/events/appointments/{identifier}")
        try:
            result = RemoteAppointment.model_validate(data["event"])
        except (KeyError, ValueError):
            raise GhlError("GHL_RESPONSE_INVALID") from None
        if result.id != identifier or result.locationId != self.location_id:
            raise GhlError("GHL_LOCATION_MISMATCH", connection_error=True)
        return result

    def create_summary(self, contact_id: str, user_id: str, body: str) -> str:
        data = self.request(
            "POST",
            "/notes",
            params={"locationId": self.location_id},
            body={
                "body": body,
                "userId": user_id,
                "relations": [{"objectKey": "contact", "recordId": contact_id}],
            },
            creating=True,
        )
        try:
            note = RemoteNote.model_validate(data["note"])
        except (KeyError, ValueError):
            raise GhlError("GHL_RESPONSE_INVALID", ambiguous=True) from None
        if note.contactId != contact_id or note.body != body or note.userId != user_id:
            raise GhlError("GHL_NOTE_WRITE_UNCONFIRMED", ambiguous=True)
        return note.id

    def note(self, identifier: str) -> RemoteNote:
        data = self.request(
            "GET", f"/notes/{identifier}", params={"locationId": self.location_id}
        )
        try:
            note = RemoteNote.model_validate(data["note"])
        except (KeyError, ValueError):
            raise GhlError("GHL_RESPONSE_INVALID") from None
        if note.id != identifier:
            raise GhlError("GHL_NOTE_OWNERSHIP_INVALID")
        return note
