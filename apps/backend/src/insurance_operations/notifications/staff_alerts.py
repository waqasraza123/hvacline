from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from functools import partial
from uuid import UUID

import httpx
from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.actors import ActorContext
from insurance_operations.database.models.hvac import HvacServiceRequest
from insurance_operations.database.models.identity import Agency
from insurance_operations.database.models.operations import AuditActorType, AuditEvent
from insurance_operations.database.models.lead import LeadHandoffRequest
from insurance_operations.database.models.staff_alert import StaffAlert, StaffAlertPolicy
from insurance_operations.errors import ApiError
from insurance_operations.hvac.google_connection import integration_settings
from insurance_operations.job_execution import provider_client
from insurance_operations.settings import ApiSettings, DatabaseSettings


class StaffAlertPolicyInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    enabled: bool
    recipients: list[EmailStr] = Field(max_length=5)
    expected_row_version: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_recipients(self) -> "StaffAlertPolicyInput":
        if self.enabled and not self.recipients:
            raise ValueError("Add an approved staff email address before enabling alerts")
        if len({str(value).casefold() for value in self.recipients}) != len(self.recipients):
            raise ValueError("Staff email addresses must be distinct")
        return self


def policy_view(session: Session, agency_id: UUID, settings: ApiSettings) -> dict[str, object]:
    policy = session.get(StaffAlertPolicy, agency_id)
    return {
        "enabled": policy.enabled if policy else False,
        "recipients": policy.recipients if policy else [],
        "row_version": policy.row_version if policy else 0,
        "runtime_enabled": settings.staff_alert_email_enabled,
        "sender": str(settings.booking_email_from) if settings.booking_email_from else None,
    }


def save_policy(sessions: sessionmaker[Session], settings: ApiSettings, actor: ActorContext, data: StaffAlertPolicyInput, correlation_id: UUID) -> dict[str, object]:
    if data.enabled and not settings.staff_alert_email_enabled:
        raise ApiError(status_code=409, code="STAFF_ALERTS_DISABLED", message="Staff email delivery is not enabled on the API and job worker.")
    with sessions() as session, session.begin():
        session.scalar(select(Agency).where(Agency.id == actor.agency_id).with_for_update())
        policy = session.get(StaffAlertPolicy, actor.agency_id)
        if (policy.row_version if policy else 0) != data.expected_row_version:
            raise ApiError(status_code=409, code="STAFF_ALERT_POLICY_CHANGED", message="Staff alert settings changed. Reload before saving.")
        if policy is None:
            policy = StaffAlertPolicy(agency_id=actor.agency_id)
            session.add(policy)
        policy.enabled = data.enabled
        policy.recipients = [str(value) for value in data.recipients]
        policy.sender = str(settings.booking_email_from) if settings.booking_email_from else None
        session.flush()
        session.refresh(policy)
        session.add(AuditEvent(
            agency_id=actor.agency_id, actor_type=AuditActorType.STAFF.value, actor_user_id=actor.app_user_id,
            occurred_at=datetime.now(UTC), event_version=1, event_type="STAFF_ALERT_POLICY_SAVED",
            summary="Staff alert policy updated", correlation_id=correlation_id,
            details={"enabled": policy.enabled, "recipient_count": len(policy.recipients), "row_version": policy.row_version},
        ))
        return policy_view(session, actor.agency_id, settings)


def ready_for_staff_delivery(session: Session, row: StaffAlert, policy: StaffAlertPolicy | None, now: datetime) -> bool:
    if now - row.created_at >= timedelta(hours=24):
        row.status = "UNKNOWN" if row.first_attempt_at else "SKIPPED"
        row.last_error = "ALERT_EXPIRED"
        return False
    if row.first_attempt_at and (now - row.first_attempt_at >= timedelta(hours=23) or row.attempts >= 8):
        row.status, row.last_error = "UNKNOWN", "PROVIDER_RETRY_WINDOW_ENDED"
        return False
    if not policy or not policy.enabled or policy.row_version != row.policy_version:
        row.status = "UNKNOWN" if row.first_attempt_at else "SKIPPED"
        row.last_error = "POLICY_CHANGED_OR_DISABLED"
        return False
    suppressed = session.scalar(select(StaffAlert.id).where(
        StaffAlert.agency_id == row.agency_id,
        func.lower(StaffAlert.recipient) == row.recipient.casefold(),
        StaffAlert.delivery_status.in_(["BOUNCED", "COMPLAINED", "SUPPRESSED"]),
    ).limit(1))
    if suppressed is not None:
        row.status = "UNKNOWN" if row.first_attempt_at else "SKIPPED"
        row.last_error = "STAFF_EMAIL_SUPPRESSED"
        return False
    source: LeadHandoffRequest | HvacServiceRequest | None
    if row.event_type == "HANDOFF":
        source = session.scalar(select(LeadHandoffRequest).where(LeadHandoffRequest.id == row.source_id, LeadHandoffRequest.agency_id == row.agency_id).with_for_update(read=True))
    else:
        source = session.scalar(select(HvacServiceRequest).where(HvacServiceRequest.id == row.source_id, HvacServiceRequest.agency_id == row.agency_id).with_for_update(read=True))
    open_source = source is not None and source.agency_id == row.agency_id and (
        source.status in {"REQUESTED", "ACKNOWLEDGED"} if row.event_type == "HANDOFF" else source.status == "HANDOFF_REQUESTED"
    )
    if not open_source:
        row.status = "UNKNOWN" if row.first_attempt_at else "SKIPPED"
        row.last_error = "REQUEST_NO_LONGER_OPEN"
        return False
    return True


def send_staff_email(client: httpx.Client, settings: DatabaseSettings, row: StaffAlert) -> tuple[str, str | None]:
    key = settings.resend_api_key
    if key is None:
        return "FAILED", "EMAIL_NOT_CONFIGURED"
    try:
        response = client.post("https://api.resend.com/emails", json=row.payload, headers={
            "Authorization": "Bearer " + key.get_secret_value(),
            "Idempotency-Key": "hvacline-staff-alert-" + str(row.id),
        }, timeout=10)
        if response.status_code == 409:
            data = response.json()
            return ("PENDING", "EMAIL_RETRY") if isinstance(data, dict) and data.get("name") == "concurrent_idempotent_requests" else ("FAILED", "EMAIL_IDEMPOTENCY_CONFLICT")
        if response.status_code == 429 or response.status_code >= 500:
            return "PENDING", "EMAIL_RETRY"
        if not 200 <= response.status_code < 300:
            return "FAILED", "EMAIL_REJECTED"
        data = response.json()
        if not isinstance(data, dict) or not isinstance(data.get("id"), str) or not data["id"] or len(data["id"]) > 256:
            return "PENDING", "EMAIL_RESPONSE_UNKNOWN"
        return "ACCEPTED", data["id"]
    except (httpx.HTTPError, ValueError):
        return "PENDING", "EMAIL_RESPONSE_UNKNOWN"


def deliver_staff_alert(sessions: sessionmaker[Session], identifier: UUID) -> None:
    with sessions() as session:
        candidate = session.get(StaffAlert, identifier)
        if candidate is None:
            return
        agency_id = candidate.agency_id
    # Commit the attempt horizon before a provider request; a lost response must
    # never extend the provider's idempotency window after process recovery.
    for prepare in (True, False):
        with sessions() as session, session.begin():
            policy = session.scalar(select(StaffAlertPolicy).where(StaffAlertPolicy.agency_id == agency_id).with_for_update())
            row = session.scalar(select(StaffAlert).where(StaffAlert.id == identifier, StaffAlert.agency_id == agency_id).with_for_update())
            now = datetime.now(UTC)
            if row is None or row.status != "PENDING" or row.due_at > now:
                return
            settings = integration_settings(session)
            if not ready_for_staff_delivery(session, row, policy, now):
                return
            if not settings.staff_alert_email_enabled:
                row.last_error = "STAFF_ALERTS_DISABLED"
                row.due_at = now + timedelta(minutes=5)
                return
            if prepare:
                if row.first_attempt_at is None:
                    row.first_attempt_at = now
                continue
            row.attempts += 1
            with provider_client() as client:
                outcome, detail = send_staff_email(client, settings, row)
            row.status = outcome
            if outcome == "ACCEPTED":
                row.provider_reference, row.last_error = detail, None
            else:
                row.last_error = detail
                row.due_at = now + timedelta(seconds=min(3600, 30 * 2 ** min(row.attempts, 7)))


def collect_staff_alert_jobs(sessions: sessionmaker[Session], batch_size: int) -> list[Callable[[], None]]:
    with sessions() as session:
        identifiers = list(session.scalars(select(StaffAlert.id).where(StaffAlert.status == "PENDING", StaffAlert.due_at <= datetime.now(UTC)).order_by(StaffAlert.due_at, StaffAlert.id).limit(batch_size)))
    return [partial(deliver_staff_alert, sessions, identifier) for identifier in identifiers]
