from datetime import date, datetime, time
from enum import StrEnum
from typing import Self
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from insurance_operations.customers import CustomerInput
from insurance_operations.telephony.phone_schemas import PhoneCallContext


class ServiceKind(StrEnum):
    AC_REPAIR = "AC_REPAIR"
    HEATING_REPAIR = "HEATING_REPAIR"
    INSTALLATION = "INSTALLATION"
    MAINTENANCE = "MAINTENANCE"


class WorkingWindow(BaseModel):
    weekday: int = Field(ge=0, le=6)
    start: time
    end: time

    @model_validator(mode="after")
    def valid_window(self) -> Self:
        if self.start.tzinfo or self.end.tzinfo or self.start >= self.end:
            raise ValueError("working windows must start and end on the same local day")
        return self


class Team(BaseModel):
    key: str = Field(pattern=r"^[a-z0-9-]{1,40}$")
    name: str = Field(min_length=1, max_length=100)
    windows: list[WorkingWindow] = Field(min_length=1, max_length=28)
    unavailable_dates: list[date] = Field(default_factory=list, max_length=366)


class ScheduleInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    expected_version: int = Field(ge=0)
    enabled: bool = False
    timezone: str
    postal_codes: list[str] = Field(min_length=1, max_length=500)
    windows: list[WorkingWindow] = Field(min_length=1, max_length=28)
    teams: list[Team] = Field(min_length=1, max_length=50)
    duration_minutes: int = Field(default=60, ge=15, le=480, multiple_of=15)
    notice_minutes: int = Field(default=120, ge=0, le=10080)
    horizon_days: int = Field(default=30, ge=1, le=90)
    cancellation_notice_minutes: int = Field(default=120, ge=0, le=10080)

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as error:
            raise ValueError("a valid IANA timezone is required") from error
        if not value.startswith("America/") and value != "Pacific/Honolulu":
            raise ValueError("configure a U.S. business timezone")
        return value

    @field_validator("postal_codes")
    @classmethod
    def validate_postal_codes(cls, values: list[str]) -> list[str]:
        if any(
            len(value) != 5 or not value.isascii() or not value.isdigit()
            for value in values
        ):
            raise ValueError("service areas require five-digit U.S. ZIP codes")
        return sorted(set(values))

    @model_validator(mode="after")
    def unique_teams(self) -> Self:
        if len({team.key for team in self.teams}) != len(self.teams):
            raise ValueError("team keys must be unique")
        return self


class ServiceDetails(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    kind: ServiceKind
    equipment_issue: str = Field(min_length=1, max_length=2000)
    preferred_window: str = Field(min_length=1, max_length=300)
    hazardous_condition: bool = False


class ServiceRequestInput(BaseModel):
    customer: CustomerInput
    service: ServiceDetails
    explicit_confirmation: bool

    @model_validator(mode="after")
    def complete_request(self) -> Self:
        address = self.customer.address
        if not self.explicit_confirmation or not self.customer.phone:
            raise ValueError(
                "caller confirmation and a callback phone number are required"
            )
        if address is None or not all(
            (address.line1, address.city, address.state_code, address.postal_code)
        ):
            raise ValueError("a complete service address is required")
        if address.country_code != "US":
            raise ValueError("only U.S. service addresses are supported")
        return self


class PhoneServiceRequestInput(PhoneCallContext, ServiceRequestInput):
    pass


class AvailabilityInput(BaseModel):
    postal_code: str = Field(pattern=r"^[0-9]{5}$")
    day: date


class PhoneAvailabilityInput(PhoneCallContext, AvailabilityInput):
    pass


class Slot(BaseModel):
    team_key: str
    starts_at: datetime
    ends_at: datetime


class AvailabilityResponse(BaseModel):
    configured: bool
    in_service_area: bool
    timezone: str | None = None
    slots: list[Slot] = Field(default_factory=list)
    message: str | None = None


class ReservationInput(BaseModel):
    service_request_id: UUID
    team_key: str = Field(min_length=1, max_length=40)
    starts_at: datetime
    idempotency_key: str = Field(
        min_length=8, max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$"
    )

    @field_validator("starts_at")
    @classmethod
    def aware_start(cls, value: datetime) -> datetime:
        if value.utcoffset() is None:
            raise ValueError("appointment timestamps require a timezone offset")
        return value


class PhoneReservationInput(PhoneCallContext, ReservationInput):
    pass


class PhoneAppointmentInput(PhoneCallContext):
    appointment_id: UUID
    explicit_confirmation: bool


class AppointmentView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    service_request_id: UUID
    team_key: str
    starts_at: datetime
    ends_at: datetime
    status: str
    hold_expires_at: datetime


class AppointmentAction(BaseModel):
    explicit_confirmation: bool


class RescheduleInput(ReservationInput):
    explicit_confirmation: bool
