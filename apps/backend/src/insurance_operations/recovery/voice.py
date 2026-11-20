from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.conversations.spoken import require_spoken_confirmation
from insurance_operations.database.models.lead import AgencyLead, LeadHandoffRequest
from insurance_operations.database.models.recovery import RecoveryAttempt, RecoveryCase, RecoveryGrant
from insurance_operations.errors import ApiError
from insurance_operations.hvac.locking import lock_business_schedule
from insurance_operations.recovery.continuation import RecoveryContinuation
from insurance_operations.recovery.domain import TERMINAL, audit, cancel_scheduled, revoke_continuations
from insurance_operations.recovery.grants import authenticate, scope, unavailable
from insurance_operations.recovery.inbox import suppress_destination
from insurance_operations.recovery.providers import VOICE_FIRST_MESSAGE
from insurance_operations.recovery.transports import ElevenLabsRecoveryVoice, TransportFailure
from insurance_operations.settings import DatabaseSettings


@dataclass(frozen=True)
class SpokenTurn:
    speaker: str
    text: str


class FinishInput(BaseModel):
    action: Literal["DECLINED", "STOP", "STAFF_REQUEST", "HAZARD"]


class RecoveryVoice:
    def __init__(self, sessions: sessionmaker[Session], settings: DatabaseSettings) -> None:
        self.sessions, self.settings = sessions, settings
        self.provider = ElevenLabsRecoveryVoice(settings)

    def bind(self, token: str, conversation_id: str) -> None:
        with self.sessions() as session:
            grant = authenticate(session, self.settings, token)
            attempt = session.get(RecoveryAttempt, grant.attempt_id)
            if grant.channel != "VOICE" or attempt is None or attempt.agency_id != grant.agency_id or attempt.provider != "ELEVENLABS_RECOVERY":
                raise unavailable()
            if attempt.provider_reference and attempt.provider_reference != conversation_id:
                raise unavailable()
            needs_binding = attempt.provider_reference is None
        if needs_binding:
            remote = self.provider.conversation(conversation_id)
            variables = (remote.get("conversation_initiation_client_data") or {}).get("dynamic_variables") or {}
            if variables.get("recovery_attempt_id") != str(attempt.id):
                raise unavailable()
        with self.sessions() as session, session.begin():
            lock_business_schedule(session, grant.agency_id)
            grant = authenticate(session, self.settings, token, lock=True)
            attempt = session.get(RecoveryAttempt, grant.attempt_id, with_for_update=True)
            if attempt is None or attempt.provider_reference not in {None, conversation_id} or grant.provider_conversation_id not in {None, conversation_id}:
                raise unavailable()
            if attempt.status not in {"STARTED", "QUEUED", "UNKNOWN", "SENT", "DELIVERED"}:
                raise unavailable()
            attempt.provider_reference, grant.provider_conversation_id = conversation_id, conversation_id
            if attempt.status in {"STARTED", "QUEUED", "UNKNOWN"}:
                attempt.status, attempt.failure_code = "SENT", None
            scope(session, self.settings, grant, allow_consumed=True)

    def turns(self, token: str, conversation_id: str) -> list[SpokenTurn]:
        self.bind(token, conversation_id)
        remote = self.provider.conversation(conversation_id)
        transcript = remote.get("transcript")
        if not isinstance(transcript, list) or len(transcript) > 120:
            raise unavailable()
        turns: list[SpokenTurn] = []
        for item in transcript:
            if not isinstance(item, dict):
                raise unavailable()
            message = item.get("message")
            if item.get("role") not in {"user", "agent"} or message is None:
                continue
            if not isinstance(message, str) or len(message) > 8000:
                raise unavailable()
            if message.strip():
                turns.append(SpokenTurn("USER" if item["role"] == "user" else "AGENT", message))
        while turns and turns[-1].speaker == "AGENT":
            turns.pop()
        return turns

    def continue_scheduling(self, token: str, conversation_id: str) -> dict[str, object]:
        turns = self.turns(token, conversation_id)
        with self.sessions() as session, session.begin():
            seed = authenticate(session, self.settings, token)
            lock_business_schedule(session, seed.agency_id)
            grant = authenticate(session, self.settings, token, lock=True)
            case, attempt, _ = scope(session, self.settings, grant)
            if grant.status == "WAITING":
                business = str((attempt.dispatch_configuration or {}).get("business_name") or "")
                introduction = VOICE_FIRST_MESSAGE.replace("{{recovery_business_name}}", business)
                try:
                    require_spoken_confirmation(turns, introduction, "continue scheduling")
                except ValueError:
                    raise ApiError(status_code=409, code="RECOVERY_VOICE_PERMISSION_REQUIRED", message="Repeat the AI disclosure and purpose, then wait for a clear customer yes before continuing.") from None
                grant.status = "ACTIVE"
                case.status, case.paused, case.reason = "AWAITING_RESPONSE", True, "CUSTOMER_CONTINUING_BOOKING"
                cancel_scheduled(session, case)
                audit(session, case.agency_id, "LEAD_RECOVERY_VOICE_CONTINUED", {"case_id": str(case.id), "attempt_id": str(attempt.id)})
        return RecoveryContinuation(self.sessions, self.settings).context(token)

    def verify_confirmation(self, token: str, conversation_id: str, nonce: UUID) -> None:
        with self.sessions() as session:
            grant = authenticate(session, self.settings, token)
            if grant.approved_at and grant.readback_nonce == nonce:
                return
        readback = RecoveryContinuation(self.sessions, self.settings).current_readback(token, nonce)
        try:
            require_spoken_confirmation(self.turns(token, conversation_id), readback, "confirm the appointment")
        except ValueError:
            raise ApiError(status_code=409, code="RECOVERY_VOICE_CONFIRMATION_REQUIRED", message="Speak the complete current readback and wait for a clear customer confirmation. No booking was confirmed.") from None

    def finish(self, token: str, conversation_id: str, data: FinishInput) -> dict[str, bool]:
        self.bind(token, conversation_id)
        if data.action == "HAZARD":
            with self.sessions() as session:
                grant = authenticate(session, self.settings, token)
                case = session.get(RecoveryCase, grant.recovery_case_id)
                if case is None:
                    raise unavailable()
                agency_id, request_id = case.agency_id, case.service_request_id
            from insurance_operations.hvac.service import SchedulingService
            from uuid import uuid4

            SchedulingService(self.sessions).flag_hazard(agency_id, request_id, uuid4())
        with self.sessions() as session, session.begin():
            seed = authenticate(session, self.settings, token)
            lock_business_schedule(session, seed.agency_id)
            grant = authenticate(session, self.settings, token, lock=True)
            case = session.get(RecoveryCase, grant.recovery_case_id, with_for_update=True)
            attempt = session.get(RecoveryAttempt, grant.attempt_id)
            if case is None or attempt is None or case.agency_id != grant.agency_id:
                raise unavailable()
            if data.action == "STOP":
                from insurance_operations.database.models.hvac import HvacServiceRequest

                request = session.get(HvacServiceRequest, case.service_request_id)
                suppress_destination(session, case.agency_id, str(attempt.recipient_digest), str(attempt.id), str(request.customer_details.get("phone")) if request else None)
            elif case.status not in TERMINAL:
                case.status = "CLOSED" if data.action == "DECLINED" else "NEEDS_REVIEW"
                case.paused, case.reason = True, "CUSTOMER_DECLINED" if data.action == "DECLINED" else "STAFF_ATTENTION_REQUIRED"
                cancel_scheduled(session, case)
                revoke_continuations(session, case)
                if data.action != "DECLINED":
                    request_staff(session, case)
            audit(session, case.agency_id, "LEAD_RECOVERY_VOICE_FINISHED", {"case_id": str(case.id), "action": data.action})
        return {"recorded": True}


def request_staff(session: Session, case: RecoveryCase) -> None:
    lead = session.get(AgencyLead, case.lead_id) if case.lead_id else None
    if lead and lead.agency_id == case.agency_id and not session.scalar(select(LeadHandoffRequest.id).where(
        LeadHandoffRequest.agency_id == case.agency_id, LeadHandoffRequest.lead_id == lead.id,
        LeadHandoffRequest.status.in_(["REQUESTED", "ACKNOWLEDGED"]))):
        session.add(LeadHandoffRequest(agency_id=case.agency_id, lead_id=lead.id,
            request_kind="CALLBACK", preferred_contact_method="PHONE", reason="Customer requested staff scheduling assistance during recovery.",
            transfer_attempted=False, status="REQUESTED", created_by=lead.created_by, updated_by=lead.created_by))
