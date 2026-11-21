"""Trusted adapter boundary; never mount this as an unsigned webhook route."""

import hashlib
import json
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.database.models.hvac import HvacServiceRequest
from insurance_operations.database.models.lead import AgencyLead, LeadHandoffRequest
from insurance_operations.database.models.recovery import RecoveryAttempt, RecoveryCase, RecoveryPermission, RecoveryProviderEvent
from insurance_operations.hvac.locking import lock_business_schedule
from insurance_operations.recovery.domain import TERMINAL, audit, cancel_scheduled, destination_digest
from insurance_operations.recovery.errors import conflict
from insurance_operations.settings import DatabaseSettings


class VerifiedRecoveryEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    agency_id: UUID
    provider_reference: str = Field(min_length=1, max_length=255)
    event_key: str = Field(min_length=1, max_length=255)
    occurred_at: AwareDatetime
    kind: Literal["QUEUED", "SENT", "DELIVERED", "FAILED", "YES", "STOP", "OTHER_REPLY"]
    sender_phone: str | None = Field(default=None, pattern=r"^\+[1-9][0-9]{7,14}$")


def apply_verified_event(sessions: sessionmaker[Session], settings: DatabaseSettings, event: VerifiedRecoveryEvent) -> None:
    """A concrete adapter must authenticate signature, account, timestamp and raw body first."""
    fingerprint = hashlib.sha256(json.dumps(event.model_dump(mode="json"), sort_keys=True).encode()).hexdigest()
    with sessions() as session, session.begin():
        lock_business_schedule(session, event.agency_id)
        attempt = session.scalar(select(RecoveryAttempt).where(RecoveryAttempt.agency_id == event.agency_id, RecoveryAttempt.provider_reference == event.provider_reference))
        if attempt is None:
            raise conflict("Provider reference is not bound to this agency's recovery attempt.")
        case = session.scalar(select(RecoveryCase).where(RecoveryCase.agency_id == event.agency_id, RecoveryCase.id == attempt.recovery_case_id).with_for_update())
        attempt = session.get(RecoveryAttempt, attempt.id, with_for_update=True)
        if case is None or attempt is None:
            raise conflict()
        previous = session.scalar(select(RecoveryProviderEvent).where(RecoveryProviderEvent.attempt_id == attempt.id, RecoveryProviderEvent.event_key == event.event_key))
        if previous:
            if previous.fingerprint != fingerprint:
                raise conflict("Provider event key was reused with different data.")
            return
        request = session.get(HvacServiceRequest, case.service_request_id)
        is_reply = event.kind in {"YES", "STOP", "OTHER_REPLY"}
        if request is None or request.agency_id != event.agency_id or (is_reply and (not event.sender_phone or event.sender_phone != request.customer_details.get("phone"))):
            raise conflict("The reply sender does not match the original confirmed recipient.")
        session.add(RecoveryProviderEvent(agency_id=event.agency_id, attempt_id=attempt.id, event_key=event.event_key, fingerprint=fingerprint, kind=event.kind, occurred_at=event.occurred_at))
        if event.kind == "STOP":
            digest = destination_digest(settings, case.agency_id, event.sender_phone or "")
            permission = session.scalar(select(RecoveryPermission).where(RecoveryPermission.agency_id == case.agency_id, RecoveryPermission.destination_digest == digest, RecoveryPermission.channel == "ALL").with_for_update())
            if permission is None:
                permission = RecoveryPermission(agency_id=case.agency_id, destination_digest=digest, channel="ALL")
                session.add(permission)
            permission.source, permission.evidence_reference, permission.revoked_at = "VERIFIED_PROVIDER_STOP", str(attempt.id), event.occurred_at
            for other in session.scalars(select(RecoveryCase).join(HvacServiceRequest, (HvacServiceRequest.id == RecoveryCase.service_request_id) & (HvacServiceRequest.agency_id == RecoveryCase.agency_id)).where(RecoveryCase.agency_id == case.agency_id, RecoveryCase.status.not_in(list(TERMINAL)), HvacServiceRequest.customer_details["phone"].astext == event.sender_phone).with_for_update(of=RecoveryCase)):
                other.status, other.reason = "SUPPRESSED", "OPTED_OUT"
                cancel_scheduled(session, other)
        elif event.kind in {"YES", "OTHER_REPLY"}:
            if case.status not in TERMINAL:
                case.status, case.reason, case.paused = "NEEDS_REVIEW", "CUSTOMER_REQUESTED_SCHEDULING" if event.kind == "YES" else "CUSTOMER_REPLY_REQUIRES_STAFF", True
                cancel_scheduled(session, case)
                lead = session.get(AgencyLead, case.lead_id) if case.lead_id else None
                if lead and lead.agency_id == case.agency_id and not session.scalar(select(LeadHandoffRequest.id).where(LeadHandoffRequest.agency_id == case.agency_id, LeadHandoffRequest.lead_id == lead.id, LeadHandoffRequest.status.in_(["REQUESTED", "ACKNOWLEDGED"]))):
                    session.add(LeadHandoffRequest(agency_id=case.agency_id, lead_id=lead.id, request_kind="CALLBACK", preferred_contact_method="PHONE", reason="Customer requested scheduling assistance after a recovery follow-up.", transfer_attempted=False, status="REQUESTED", created_by=lead.created_by, updated_by=lead.created_by))
        elif event.kind == "FAILED":
            attempt.status, attempt.failure_code = "FAILED", "PROVIDER_REPORTED_FAILURE"
            if case.status not in TERMINAL:
                case.status, case.reason = "NEEDS_REVIEW", "PROVIDER_REPORTED_FAILURE"
        else:
            order = {"STARTED": 0, "UNKNOWN": 0, "QUEUED": 1, "SENT": 2, "DELIVERED": 3}
            if attempt.status in order and order.get(event.kind, -1) > order[attempt.status]:
                attempt.status = event.kind
        # Delivery receipts never imply engagement or a recovered booking.
        audit(session, case.agency_id, "LEAD_RECOVERY_PROVIDER_EVENT", {"case_id": str(case.id), "attempt_id": str(attempt.id), "kind": event.kind})
