from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from insurance_operations.billing.catalog import PaidPlanKey, PlanKey


class PlanRead(BaseModel):
    key: PlanKey
    name: str
    amount: int
    included_hours: int
    hourly_amount: int
    currency: Literal["usd"] = "usd"
    interval: Literal["month"] = "month"
    description: str
    features: list[str]


class CatalogRead(BaseModel):
    plans: list[PlanRead]
    checkout_enabled: bool
    draft: bool


class CheckoutCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    plan: PaidPlanKey
    request_id: UUID
    accepted_amount: int = Field(strict=True, ge=1)
    explicit_confirmation: Literal[True]

    @field_validator("explicit_confirmation", mode="before")
    @classmethod
    def explicit_consent(cls, value: object) -> object:
        if value is not True:
            raise ValueError("Explicit confirmation is required")
        return value


class RedirectRead(BaseModel):
    url: str


class BillingRead(BaseModel):
    account_id: UUID
    plan: PlanKey
    subscription_status: str
    period_start: datetime | None
    period_end: datetime | None
    cancel_at_period_end: bool
    last_synced_at: datetime | None
    checkout_enabled: bool
    portal_enabled: bool
    sync_pending: bool
    checkout_pending: bool
    pending_checkout_id: UUID | None = None
    review_required: bool = False
    included_minutes: int = 0
    used_package_minutes: int = 0
    remaining_package_minutes: int = 0
    purchased_minutes: int = 0
    used_purchased_minutes: int = 0
    remaining_purchased_minutes: int = 0
    hourly_amount: int | None = None


class TopUpCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    hours: int = Field(strict=True, ge=1, le=40)
    request_id: UUID
    accepted_amount: int = Field(strict=True, ge=1)
    explicit_confirmation: Literal[True]

    @field_validator("explicit_confirmation", mode="before")
    @classmethod
    def explicit_consent(cls, value: object) -> object:
        if value is not True:
            raise ValueError("Explicit confirmation is required")
        return value


class TopUpRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    plan: PaidPlanKey
    minutes: int
    hourly_amount: int
    amount: int
    status: str
    created_at: datetime
    credited_at: datetime | None


class LaborCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    request_id: UUID
    appointment_id: UUID
    minutes: int = Field(strict=True, ge=1, le=1440)
    work_completed: Literal[True]

    @field_validator("work_completed", mode="before")
    @classmethod
    def completed_work(cls, value: object) -> object:
        if value is not True:
            raise ValueError("Completed work must be explicitly confirmed")
        return value


class LaborRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    appointment_id: UUID
    minutes: int
    package_minutes: int
    purchased_minutes: int
    created_at: datetime
