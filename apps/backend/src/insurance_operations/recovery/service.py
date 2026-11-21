import hashlib
import json
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.actors import ActorContext
from insurance_operations.database.models.hvac import Appointment, BusinessSchedule, HvacServiceRequest
from insurance_operations.database.models.identity import Agency, AgencyMembership
from insurance_operations.database.models.operations import IdempotencyRecord
from insurance_operations.database.models.recovery import RecoveryAttempt, RecoveryCase, RecoveryPermission, RecoveryPolicy, RecoveryAiConnection, RecoveryGrant
from insurance_operations.errors import ApiError
from insurance_operations.hvac.locking import lock_business_schedule
from insurance_operations.hvac.schemas import AppointmentView
from insurance_operations.recovery.domain import TERMINAL, audit, cancel_scheduled, destination_digest, permission_rows, policy_for
from insurance_operations.recovery.jobs import eligibility, schedule_case
from insurance_operations.recovery.transports import ConfiguredRecoveryProvider
from insurance_operations.recovery.configuration import channel_configured, provider_status
from insurance_operations.recovery.domain import revoke_continuations
from insurance_operations.recovery.errors import conflict
from insurance_operations.recovery.schemas import AttemptView, CaseAction, CaseView, PermissionInput, PolicyInput, RecoveryStatus, ContinuationView, OutcomeInput
from insurance_operations.settings import DatabaseSettings


def owned_case(session: Session, agency_id: UUID, identifier: UUID, *, lock: bool = False) -> RecoveryCase:
    query = select(RecoveryCase).where(RecoveryCase.agency_id == agency_id, RecoveryCase.id == identifier)
    case = session.scalar(query.with_for_update() if lock else query)
    if case is None:
        raise ApiError(status_code=404, code="RECOVERY_CASE_NOT_FOUND", message="Recovery case not found.")
    return case


class RecoveryService:
    def __init__(self, sessions: sessionmaker[Session], settings: DatabaseSettings) -> None:
        self.sessions, self.settings = sessions, settings

    def view(self, session: Session, case: RecoveryCase) -> CaseView:
        request = session.scalar(select(HvacServiceRequest).where(HvacServiceRequest.agency_id == case.agency_id, HvacServiceRequest.id == case.service_request_id))
        if request is None:
            raise conflict("The original request is unavailable.")
        attempts = list(session.scalars(select(RecoveryAttempt).where(RecoveryAttempt.agency_id == case.agency_id, RecoveryAttempt.recovery_case_id == case.id).order_by(RecoveryAttempt.attempt_number)))
        permissions = permission_rows(session, self.settings, request)
        grants = list(session.scalars(select(RecoveryGrant).where(RecoveryGrant.agency_id == case.agency_id,
            RecoveryGrant.recovery_case_id == case.id).order_by(RecoveryGrant.created_at)))
        booking = session.scalar(select(Appointment).where(Appointment.agency_id == case.agency_id, Appointment.service_request_id == request.id,
            Appointment.id == case.recovered_appointment_id if case.recovered_appointment_id else Appointment.status == "CONFIRMED").order_by(Appointment.starts_at.desc()).limit(1))
        return CaseView(id=case.id, row_version=case.row_version, service_request_id=case.service_request_id, lead_id=case.lead_id,
            inbound_call_id=request.inbound_call_id, conversation_session_id=request.conversation_session_id,
            customer=str(request.customer_details.get("full_name") or "Confirmed customer"), summary=str(request.service_details.get("equipment_issue") or "HVAC service"),
            source_type=case.source_type, source_reference=case.source_reference, status=RecoveryStatus(case.status), eligible_at=case.eligible_at, last_activity_at=case.last_activity_at,
            recovered_appointment_id=case.recovered_appointment_id, booking=AppointmentView.model_validate(booking) if booking else None, paused=case.paused, assigned_to=case.assigned_to, reason=case.reason,
            next_attempt=next((attempt.scheduled_at for attempt in attempts if attempt.status == "SCHEDULED"), None), attempts=[AttemptView.model_validate(row) for row in attempts],
            continuations=[ContinuationView(id=grant.id, attempt_id=grant.attempt_id, channel=grant.channel, status=grant.status,
                expires_at=grant.expires_at, reply_status=grant.reply_status, failure_code=grant.failure_code) for grant in grants],
            permissions=[{"channel": row.channel, "scope": row.scope, "source": row.source, "evidence_reference": row.evidence_reference, "granted_at": row.granted_at.isoformat() if row.granted_at else None,
                "revoked_at": row.revoked_at.isoformat() if row.revoked_at else None, "row_version": row.row_version} for row in permissions])

    def cases(self, actor: ActorContext, status: RecoveryStatus | None, limit: int, offset: int) -> dict[str, object]:
        with self.sessions() as session:
            filters = [RecoveryCase.agency_id == actor.agency_id]
            if status:
                filters.append(RecoveryCase.status == status.value)
            rows = list(session.scalars(select(RecoveryCase).where(*filters).order_by(RecoveryCase.last_activity_at.desc(), RecoveryCase.id).limit(limit).offset(offset)))
            total = session.scalar(select(func.count()).select_from(RecoveryCase).where(*filters)) or 0
            return {"items": [self.view(session, row).model_dump(mode="json") for row in rows], "total": total, "limit": limit, "offset": offset}

    def detail(self, actor: ActorContext, identifier: UUID) -> CaseView:
        with self.sessions() as session:
            return self.view(session, owned_case(session, actor.agency_id, identifier))

    def summary(self, actor: ActorContext) -> dict[str, object]:
        with self.sessions() as session:
            counts = dict(session.execute(select(RecoveryCase.status, func.count()).where(RecoveryCase.agency_id == actor.agency_id).group_by(RecoveryCase.status)).all())
            total, recovered = sum(counts.values()), counts.get("RECOVERED", 0)
            attempted = session.scalar(select(func.count()).select_from(RecoveryAttempt).where(RecoveryAttempt.agency_id == actor.agency_id, RecoveryAttempt.started_at.is_not(None))) or 0
            recent = list(session.scalars(select(RecoveryCase).where(RecoveryCase.agency_id == actor.agency_id).order_by(RecoveryCase.updated_at.desc()).limit(3)))
            return {"total": total, "recoverable": sum(value for key, value in counts.items() if key not in TERMINAL), "scheduled": counts.get("SCHEDULED", 0), "attempted": attempted,
                "recovered": recovered, "conversion_rate": recovered / total if total else 0, "recent": [{"id": str(row.id), "status": row.status, "at": row.updated_at.isoformat()} for row in recent]}

    def settings_view(self, actor: ActorContext) -> dict[str, object]:
        with self.sessions() as session:
            policy = policy_for(session, actor.agency_id)
            return {"policy": policy.model_dump(mode="json"), "runtime_enabled": self.settings.recovery_enabled,
                "providers": provider_status(self.settings, actor.agency_id),
                "identity_gate": "Existing administrator/development identity; production onboarding is not enabled."}

    def save_policy(self, actor: ActorContext, data: PolicyInput) -> dict[str, object]:
        with self.sessions() as session, session.begin():
            session.scalar(select(Agency.id).where(Agency.id == actor.agency_id).with_for_update())
            row = session.get(RecoveryPolicy, actor.agency_id, with_for_update=True)
            if data.expected_row_version != (row.row_version if row else 0):
                raise conflict()
            schedule = session.get(BusinessSchedule, actor.agency_id)
            if schedule and data.timezone != schedule.configuration.get("timezone"):
                raise conflict("Use the agency timezone configured in Scheduling before saving recovery rules.")
            if data.enabled:
                if not self.settings.recovery_enabled or not data.channels or any(not channel_configured(self.settings, actor.agency_id, channel) for channel in data.channels):
                    raise conflict("Enable the server recovery gate and configure every selected delivery channel before activating automation.")
                ai = session.get(RecoveryAiConnection, actor.agency_id)
                if "SMS" in data.channels and (ai is None or ai.status != "CONNECTED"):
                    raise conflict("Connect and test the agency text model before enabling SMS recovery. Voice uses its dedicated ElevenLabs agent.")
            if row is None:
                row = RecoveryPolicy(agency_id=actor.agency_id, capture_from=datetime.now(UTC))
                session.add(row)
            row.enabled = data.enabled
            row.configuration = data.model_dump(mode="json", exclude={"expected_row_version", "enabled"})
            session.flush()
            audit(session, actor.agency_id, "LEAD_RECOVERY_POLICY_SAVED", {"enabled": row.enabled}, actor.app_user_id)
        return self.settings_view(actor)

    def action(self, actor: ActorContext, identifier: UUID, data: CaseAction, key: str) -> CaseView:
        with self.sessions() as session, session.begin():
            lock_business_schedule(session, actor.agency_id)
            case = owned_case(session, actor.agency_id, identifier, lock=True)
            route = f"recovery/{identifier}/action"
            fingerprint = hashlib.sha256(json.dumps(data.model_dump(mode="json"), sort_keys=True).encode()).hexdigest()
            previous = session.scalar(select(IdempotencyRecord).where(IdempotencyRecord.agency_id == actor.agency_id, IdempotencyRecord.actor_scope_id == actor.app_user_id, IdempotencyRecord.route_key == route, IdempotencyRecord.idempotency_key == key))
            if previous:
                if previous.request_fingerprint != fingerprint:
                    raise conflict("Idempotency key was already used for another action.")
                return self.view(session, case)
            if case.row_version != data.expected_row_version:
                raise conflict()
            if case.status in TERMINAL:
                raise conflict("This recovery case is terminal.")
            if data.action in {"RESUME", "RETRY"}:
                if any(attempt.status in {"STARTED", "UNKNOWN", "QUEUED"} for attempt in session.scalars(select(RecoveryAttempt).where(RecoveryAttempt.agency_id == actor.agency_id, RecoveryAttempt.recovery_case_id == case.id))):
                    raise conflict("Resolve the provider outcome before any further contact.")
                case.paused = False
                _, _, reason = eligibility(session, self.settings, case, ConfiguredRecoveryProvider(self.settings), datetime.now(UTC))
                if reason:
                    raise conflict(reason.replace("_", " ").capitalize())
                schedule_case(session, self.settings, case, ConfiguredRecoveryProvider(self.settings), datetime.now(UTC))
            elif data.action == "PAUSE":
                case.paused, case.reason = True, "MANUALLY_PAUSED"
                revoke_continuations(session, case)
            elif data.action == "CLOSE":
                case.status, case.reason = "CLOSED", "MANUALLY_CLOSED"
                cancel_scheduled(session, case)
                revoke_continuations(session, case)
            elif data.action == "ASSIGN":
                membership = session.scalar(select(AgencyMembership).where(AgencyMembership.agency_id == actor.agency_id, AgencyMembership.app_user_id == data.assigned_to, AgencyMembership.status == "ACTIVE", AgencyMembership.deactivated_at.is_(None)))
                if membership is None:
                    raise conflict("Assign an active staff member in this agency.")
                case.assigned_to, case.paused, case.reason = data.assigned_to, True, "ASSIGNED_TO_STAFF"
                case.status = "NEEDS_REVIEW"
                revoke_continuations(session, case)
            session.flush()
            session.refresh(case)
            audit(session, actor.agency_id, "LEAD_RECOVERY_ADMIN_ACTION", {"case_id": str(case.id), "action": data.action, "status": case.status}, actor.app_user_id)
            session.add(IdempotencyRecord(agency_id=actor.agency_id, actor_scope_type="STAFF", actor_scope_id=actor.app_user_id, route_key=route, idempotency_key=key,
                request_fingerprint=fingerprint, status="COMPLETED", response_status=200, response_body={"case_id": str(case.id)}, resource_type="lead_recovery_case", resource_id=case.id, expires_at=datetime.now(UTC) + timedelta(days=7)))
            return self.view(session, case)

    def resolve_outcome(self, actor: ActorContext, identifier: UUID, attempt_id: UUID, data: OutcomeInput) -> CaseView:
        from insurance_operations.recovery.delivery_jobs import read_provider_outcome
        from insurance_operations.recovery.inbox import enqueue, process_event
        from insurance_operations.recovery.transports import TransportFailure

        with self.sessions() as session:
            case = owned_case(session, actor.agency_id, identifier)
            attempt = session.scalar(select(RecoveryAttempt).where(RecoveryAttempt.id == attempt_id,
                RecoveryAttempt.agency_id == actor.agency_id, RecoveryAttempt.recovery_case_id == case.id))
            if attempt is None or case.row_version != data.expected_row_version:
                raise conflict()
            grant = session.scalar(select(RecoveryGrant).where(RecoveryGrant.id == data.grant_id,
                RecoveryGrant.agency_id == actor.agency_id, RecoveryGrant.attempt_id == attempt.id)) if data.grant_id else None
            if data.grant_id and grant is None:
                raise conflict("Continuation not found for this attempt.")
            current = grant.reply_provider_reference if grant else attempt.provider_reference
            reference = data.provider_reference or current
            if current and reference != current:
                raise conflict("The provider reference is already bound. It cannot be replaced.")
        if reference:
            try:
                receipt = read_provider_outcome(self.settings, attempt, reference, grant=grant)
            except TransportFailure:
                raise conflict("The provider could not verify this original destination and request. No retry was authorized.") from None
            with self.sessions() as session, session.begin():
                lock_business_schedule(session, actor.agency_id)
                case = owned_case(session, actor.agency_id, identifier, lock=True)
                if case.row_version != data.expected_row_version:
                    raise conflict()
                case.updated_at = datetime.now(UTC)
                audit(session, actor.agency_id, "LEAD_RECOVERY_PROVIDER_RECONCILED", {"case_id": str(case.id), "attempt_id": str(attempt.id), "reply": bool(grant)}, actor.app_user_id)
            event = enqueue(self.sessions, self.settings, agency_id=actor.agency_id, provider=str(attempt.provider),
                attempt_id=attempt.id, key=f"owner-read:{reference}:{receipt['status']}:{receipt['terminal']}", kind="RECEIPT", data=receipt)
            process_event(self.sessions, event)
        elif data.carrier_ended_confirmed and attempt.channel == "VOICE" and attempt.status == "UNKNOWN" and grant is None:
            with self.sessions() as session, session.begin():
                lock_business_schedule(session, actor.agency_id)
                case = owned_case(session, actor.agency_id, identifier, lock=True)
                if case.row_version != data.expected_row_version:
                    raise conflict()
                attempt = session.get(RecoveryAttempt, attempt_id, with_for_update=True)
                if attempt is None or attempt.status != "UNKNOWN" or attempt.provider_reference:
                    raise conflict()
                attempt.provider_terminal_at = datetime.now(UTC)
                case.updated_at = datetime.now(UTC)
                audit(session, actor.agency_id, "LEAD_RECOVERY_CARRIER_ENDED_ATTESTED", {"case_id": str(case.id), "attempt_id": str(attempt.id), "status": "UNKNOWN"}, actor.app_user_id)
        else:
            raise conflict("Supply the original provider reference. An unknown write can never be blindly retried.")
        return self.detail(actor, identifier)

    def permission(self, actor: ActorContext, identifier: UUID, data: PermissionInput) -> CaseView:
        if data.observed_at > datetime.now(UTC) or data.observed_at < datetime.now(UTC) - timedelta(days=7):
            raise conflict("Permission evidence must be observed within the last seven days, without a future timestamp.")
        with self.sessions() as session, session.begin():
            lock_business_schedule(session, actor.agency_id)
            case = owned_case(session, actor.agency_id, identifier, lock=True)
            request = session.get(HvacServiceRequest, case.service_request_id)
            if request is None or request.agency_id != actor.agency_id:
                raise conflict()
            digest = destination_digest(self.settings, actor.agency_id, str(request.customer_details.get("phone") or ""))
            row = session.scalar(select(RecoveryPermission).where(RecoveryPermission.agency_id == actor.agency_id, RecoveryPermission.destination_digest == digest, RecoveryPermission.channel == data.channel).with_for_update())
            if data.expected_row_version != (row.row_version if row else 0):
                raise conflict()
            if row and row.revoked_at and data.granted:
                raise conflict("Opt-outs require a separately reviewed re-permission process; administrator retry cannot override suppression.")
            if row is None:
                row = RecoveryPermission(agency_id=actor.agency_id, destination_digest=digest, channel=data.channel)
                session.add(row)
            row.source, row.evidence_reference = data.source, data.evidence_reference
            if data.granted:
                row.granted_at = data.observed_at
            else:
                row.revoked_at = data.observed_at
                for other in session.scalars(select(RecoveryCase).join(HvacServiceRequest, (HvacServiceRequest.agency_id == RecoveryCase.agency_id) & (HvacServiceRequest.id == RecoveryCase.service_request_id)).where(RecoveryCase.agency_id == actor.agency_id, RecoveryCase.status.not_in(list(TERMINAL)), HvacServiceRequest.customer_details["phone"].astext == str(request.customer_details["phone"])).with_for_update(of=RecoveryCase)):
                    other.status, other.reason = "SUPPRESSED", "OPTED_OUT"
                    cancel_scheduled(session, other)
                    revoke_continuations(session, other)
            session.flush()
            session.refresh(case)
            audit(session, actor.agency_id, "LEAD_RECOVERY_PERMISSION_UPDATED", {"case_id": str(case.id), "permission_id": str(row.id), "channel": data.channel, "scope": "LEAD_RECOVERY", "granted": data.granted,
                "source": data.source, "evidence_reference": data.evidence_reference, "observed_at": data.observed_at.isoformat()}, actor.app_user_id)
            return self.view(session, case)
