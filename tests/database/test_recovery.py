from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import cast
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr
from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.actors import ActorContext
from insurance_operations.database.models.hvac import Appointment, HvacServiceRequest
from insurance_operations.database.models.identity import Agency, AgencyMembership, AppUser
from insurance_operations.database.models.operations import AuditEvent
from insurance_operations.database.models.recovery import RecoveryAiConnection, RecoveryAttempt, RecoveryCase, RecoveryPermission, RecoveryPolicy
from insurance_operations.errors import ApiError
from insurance_operations.recovery.ai import RecoveryAiService
from insurance_operations.recovery.domain import detect_request, destination_digest, stop_for_booking
from insurance_operations.recovery.events import VerifiedRecoveryEvent, apply_verified_event
from insurance_operations.recovery.jobs import process_case
from insurance_operations.recovery.providers import DeliveryOutcome, RecoveryContact
from insurance_operations.recovery.schemas import AiInput, CaseAction, PermissionInput, PolicyInput
from insurance_operations.recovery.service import RecoveryService
from insurance_operations.settings import DatabaseSettings
from tests.database.test_hvac_scheduling import configure, service_request


@dataclass
class RecoveryContext:
    sessions: sessionmaker[Session]
    settings: DatabaseSettings
    actor: ActorContext
    case_id: UUID
    request_id: UUID
    now: datetime


@pytest.fixture
def recovery_context(migrated_database: Engine, database_settings: DatabaseSettings) -> RecoveryContext:
    _, agency_id, reservation = configure(migrated_database)
    settings = database_settings.model_copy(update={"recovery_enabled": True, "recovery_token_encryption_key": SecretStr(Fernet.generate_key().decode())})
    sessions = sessionmaker(bind=migrated_database, expire_on_commit=False, info={"integration_settings": settings})
    now = datetime.now(UTC).replace(hour=16, minute=0, second=0, microsecond=0)
    with sessions() as session, session.begin():
        user = AppUser(auth_subject=uuid4(), display_name="Synthetic recovery owner", status="ACTIVE")
        session.add(user)
        session.flush()
        session.add(AgencyMembership(agency_id=agency_id, app_user_id=user.id, status="ACTIVE"))
        case = session.scalar(select(RecoveryCase).where(RecoveryCase.agency_id == agency_id, RecoveryCase.service_request_id == reservation.service_request_id))
        assert case is not None
        case.created_at, case.eligible_at, case.last_activity_at = now - timedelta(hours=1), now - timedelta(minutes=30), now - timedelta(hours=1)
        policy = PolicyInput(expected_row_version=0, enabled=True, channels=["SMS"], timezone="America/New_York")
        stored_policy = session.get(RecoveryPolicy, agency_id)
        assert stored_policy is not None
        stored_policy.enabled = True
        stored_policy.configuration = policy.model_dump(mode="json", exclude={"expected_row_version", "enabled"})
        ai = RecoveryAiService(sessions, settings)
        session.add(RecoveryAiConnection(agency_id=agency_id, provider="OPENAI", model="synthetic-model", endpoint="https://api.openai.com/v1", status="CONNECTED", credential_ciphertext=ai.encrypt(agency_id, "OPENAI", "https://api.openai.com/v1", "synthetic-key")))
        request = session.get(HvacServiceRequest, case.service_request_id)
        assert request is not None
        session.add(RecoveryPermission(agency_id=agency_id, destination_digest=destination_digest(settings, agency_id, str(request.customer_details["phone"])), channel="SMS", scope="LEAD_RECOVERY", source="SIGNED_FORM", evidence_reference="synthetic-form", granted_at=now - timedelta(days=1)))
        context = RecoveryContext(sessions, settings, ActorContext(user.id, user.display_name, agency_id, "Synthetic HVAC", "DEVELOPMENT"), case.id, request.id, now)
    return context


@dataclass
class SyntheticDelivery:
    sessions: sessionmaker[Session]
    uncertain: bool = False
    contacts: list[RecoveryContact] = field(default_factory=list)

    def available(self, agency_id: UUID, channel: str) -> bool:
        return channel == "SMS"

    def send(self, contact: RecoveryContact, channel: str) -> DeliveryOutcome:
        with self.sessions() as session:
            attempt = session.scalar(select(RecoveryAttempt).where(RecoveryAttempt.idempotency_key == contact.idempotency_key))
            assert attempt is not None and attempt.status == "STARTED"
        self.contacts.append(contact)
        if self.uncertain:
            raise TimeoutError("synthetic provider timeout")
        return DeliveryOutcome("SENT", f"synthetic-provider-{len(self.contacts)}")


def tick(context: RecoveryContext, provider: SyntheticDelivery) -> None:
    with patch("insurance_operations.recovery.jobs.datetime") as clock:
        clock.now.return_value = context.now
        process_case(context.sessions, context.case_id, provider)


def test_prospective_detection_is_deduplicated_under_concurrency(recovery_context: RecoveryContext) -> None:
    context = recovery_context

    def detect(_: int) -> None:
        with context.sessions() as session, session.begin():
            request = session.get(HvacServiceRequest, context.request_id)
            assert request is not None
            detect_request(session, request)

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(detect, [1, 2]))
    with context.sessions() as session:
        assert session.scalar(select(func.count()).select_from(RecoveryCase).where(RecoveryCase.agency_id == context.actor.agency_id)) == 1


def test_hazardous_requests_never_create_recovery_cases(migrated_database: Engine) -> None:
    service, agency_id, _ = configure(migrated_database)
    identifier = service.create_request(agency_id, service_request(hazardous=True), uuid4())
    with Session(migrated_database) as session:
        assert session.scalar(select(RecoveryCase.id).where(RecoveryCase.service_request_id == identifier)) is None


def test_delayed_historical_activity_cannot_enroll_a_request(recovery_context: RecoveryContext) -> None:
    context = recovery_context
    with context.sessions() as session, session.begin():
        case = session.get(RecoveryCase, context.case_id)
        request = session.get(HvacServiceRequest, context.request_id)
        policy = session.get(RecoveryPolicy, context.actor.agency_id)
        assert case is not None and request is not None and policy is not None
        session.delete(case)
        request.confirmed_at = policy.capture_from - timedelta(days=1)
        session.flush()
        detect_request(session, request)
        assert session.scalar(select(RecoveryCase.id).where(RecoveryCase.service_request_id == request.id)) is None


def test_concurrent_ticks_checkpoint_one_attempt_and_never_double_send(recovery_context: RecoveryContext) -> None:
    context = recovery_context
    provider = SyntheticDelivery(context.sessions)
    tick(context, provider)
    with patch("insurance_operations.recovery.jobs.datetime") as clock:
        clock.now.return_value = context.now
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(lambda _: process_case(context.sessions, context.case_id, provider), [1, 2]))
    assert len(provider.contacts) == 1
    with context.sessions() as session:
        assert session.get(RecoveryCase, context.case_id).status == "AWAITING_RESPONSE"
        attempts = list(session.scalars(select(RecoveryAttempt).where(RecoveryAttempt.recovery_case_id == context.case_id)))
        assert len(attempts) == 1 and attempts[0].status == "SENT"
    tick(context, provider)
    with context.sessions() as session:
        second = session.scalar(select(RecoveryAttempt).where(RecoveryAttempt.recovery_case_id == context.case_id, RecoveryAttempt.attempt_number == 2))
        assert second is not None and second.scheduled_at >= context.now + timedelta(hours=24)
    assert len(provider.contacts) == 1


def test_unknown_outcomes_block_worker_and_administrator_retries(recovery_context: RecoveryContext) -> None:
    context = recovery_context
    provider = SyntheticDelivery(context.sessions, uncertain=True)
    tick(context, provider)
    tick(context, provider)
    tick(context, provider)
    assert len(provider.contacts) == 1
    service = RecoveryService(context.sessions, context.settings)
    case = service.detail(context.actor, context.case_id)
    assert case.status == "NEEDS_REVIEW"
    assert case.attempts[0].status == "UNKNOWN"
    with pytest.raises(ApiError, match="Resolve the provider outcome"):
        service.action(context.actor, case.id, CaseAction(expected_row_version=case.row_version, action="RETRY"), str(uuid4()))


def test_revocation_between_scheduling_and_execution_stops_all_contact(recovery_context: RecoveryContext) -> None:
    context = recovery_context
    provider = SyntheticDelivery(context.sessions)
    tick(context, provider)
    service = RecoveryService(context.sessions, context.settings)
    service.permission(context.actor, context.case_id, PermissionInput(expected_row_version=0, channel="ALL", granted=False, source="CUSTOMER_REVOCATION", evidence_reference="synthetic-opt-out", observed_at=datetime.now(UTC)))
    tick(context, provider)
    assert not provider.contacts
    case = service.detail(context.actor, context.case_id)
    assert case.status == "SUPPRESSED"
    assert case.attempts[0].status == "CANCELLED"


def test_receipt_is_not_engagement_and_yes_creates_staff_continuation(recovery_context: RecoveryContext) -> None:
    context = recovery_context
    provider = SyntheticDelivery(context.sessions)
    tick(context, provider)
    tick(context, provider)
    event = VerifiedRecoveryEvent(agency_id=context.actor.agency_id, provider_reference="synthetic-provider-1", event_key="delivered-1", kind="DELIVERED", occurred_at=datetime.now(UTC))
    apply_verified_event(context.sessions, context.settings, event)
    apply_verified_event(context.sessions, context.settings, event)
    service = RecoveryService(context.sessions, context.settings)
    assert service.detail(context.actor, context.case_id).status == "AWAITING_RESPONSE"
    apply_verified_event(context.sessions, context.settings, event.model_copy(update={"event_key": "yes-1", "kind": "YES", "sender_phone": "+15559991002"}))
    case = service.detail(context.actor, context.case_id)
    assert case.status == "NEEDS_REVIEW" and case.paused
    assert case.reason == "CUSTOMER_REQUESTED_SCHEDULING"
    assert case.recovered_appointment_id is None


def test_independent_booking_stops_recovery_without_false_attribution(recovery_context: RecoveryContext) -> None:
    context = recovery_context
    with context.sessions() as session, session.begin():
        appointment = Appointment(agency_id=context.actor.agency_id, service_request_id=context.request_id, team_key="team-a", starts_at=context.now + timedelta(days=1), ends_at=context.now + timedelta(days=1, hours=1), status="CONFIRMED", hold_expires_at=context.now, idempotency_key=str(uuid4()), fingerprint="synthetic")
        session.add(appointment)
        session.flush()
        stop_for_booking(session, appointment)
    case = RecoveryService(context.sessions, context.settings).detail(context.actor, context.case_id)
    assert case.status == "CLOSED" and case.reason == "BOOKED_INDEPENDENTLY"
    assert case.recovered_appointment_id is None


def test_existing_booking_confirmation_stops_recovery(migrated_database: Engine) -> None:
    scheduling, agency_id, reservation = configure(migrated_database)
    held = scheduling.reserve(agency_id, reservation, uuid4())
    scheduling.confirm(agency_id, held.id, True, uuid4())
    with Session(migrated_database) as session:
        case = session.scalar(select(RecoveryCase).where(RecoveryCase.agency_id == agency_id, RecoveryCase.service_request_id == reservation.service_request_id))
        assert case is not None and case.status == "CLOSED"
        assert case.reason == "BOOKED_INDEPENDENTLY"
        assert case.recovered_appointment_id is None


def test_trusted_attribution_requires_a_sent_attempt_and_confirmed_same_request(recovery_context: RecoveryContext) -> None:
    context = recovery_context
    provider = SyntheticDelivery(context.sessions)
    tick(context, provider)
    tick(context, provider)
    tick(context, provider)
    with context.sessions() as session, session.begin():
        attempt = session.scalar(select(RecoveryAttempt).where(RecoveryAttempt.recovery_case_id == context.case_id, RecoveryAttempt.attempt_number == 1))
        assert attempt is not None
        appointment = Appointment(agency_id=context.actor.agency_id, service_request_id=context.request_id, team_key="team-a", starts_at=context.now + timedelta(days=1), ends_at=context.now + timedelta(days=1, hours=1), status="HELD", hold_expires_at=context.now + timedelta(minutes=5), idempotency_key=str(uuid4()), fingerprint="synthetic")
        session.add(appointment)
        session.flush()
        stop_for_booking(session, appointment, attributable_attempt_id=attempt.id)
        assert session.get(RecoveryCase, context.case_id).status != "RECOVERED"
        appointment.status = "CONFIRMED"
        stop_for_booking(session, appointment, attributable_attempt_id=attempt.id)
    case = RecoveryService(context.sessions, context.settings).detail(context.actor, context.case_id)
    assert case.status == "RECOVERED" and case.recovered_appointment_id is not None
    assert case.attempts[1].status == "CANCELLED"
    with context.sessions() as session:
        details = str(list(session.scalars(select(AuditEvent.details).where(AuditEvent.agency_id == context.actor.agency_id, AuditEvent.event_type.like("LEAD_RECOVERY%")))))
        assert "+15559991002" not in details and "Synthetic Caller" not in details


def test_case_writes_are_versioned_idempotent_and_agency_scoped(recovery_context: RecoveryContext) -> None:
    context = recovery_context
    service = RecoveryService(context.sessions, context.settings)
    initial = service.detail(context.actor, context.case_id)
    action, key = CaseAction(expected_row_version=initial.row_version, action="PAUSE"), str(uuid4())
    first = service.action(context.actor, initial.id, action, key)
    assert first.paused
    assert service.action(context.actor, initial.id, action, key).row_version == first.row_version
    with pytest.raises(ApiError):
        service.action(context.actor, initial.id, action, str(uuid4()))
    foreign = ActorContext(context.actor.app_user_id, "Other owner", uuid4(), "Other HVAC", "DEVELOPMENT")
    with pytest.raises(ApiError) as error:
        service.detail(foreign, initial.id)
    assert error.value.status_code == 404


def test_database_rejects_foreign_request_ownership_and_terminal_reopening(recovery_context: RecoveryContext) -> None:
    context = recovery_context
    with pytest.raises(IntegrityError), context.sessions() as session, session.begin():
        agency = Agency(name="Other synthetic business", slug=str(uuid4()), environment_kind="DEVELOPMENT")
        session.add(agency)
        session.flush()
        session.add(RecoveryCase(agency_id=agency.id, service_request_id=context.request_id, source_type="UNCONFIRMED_BOOKING", source_reference=uuid4(), status="PENDING", eligible_at=context.now, last_activity_at=context.now))
        session.flush()
    service = RecoveryService(context.sessions, context.settings)
    case = service.detail(context.actor, context.case_id)
    service.action(context.actor, case.id, CaseAction(expected_row_version=case.row_version, action="CLOSE"), str(uuid4()))
    with pytest.raises(DBAPIError), context.sessions() as session, session.begin():
        session.get(RecoveryCase, context.case_id).status = "PENDING"
        session.flush()


def test_saved_ai_connection_is_encrypted_and_test_uses_only_mock_provider(recovery_context: RecoveryContext) -> None:
    context = recovery_context
    ai = RecoveryAiService(context.sessions, context.settings)
    current = ai.status(context.actor)
    saved = ai.save(context.actor, AiInput(expected_row_version=cast(int, current["row_version"]), provider="OPENAI", model="synthetic-model", api_key=SecretStr("new-synthetic-key")))
    assert saved["status"] == "UNTESTED" and "new-synthetic-key" not in str(saved)
    with patch("insurance_operations.recovery.ai.chat_completion", return_value="OK") as completion:
        result = ai.generate(context.actor, cast(int, saved["row_version"]), "Synthetic connection test", test=True)
        completion.assert_called_once()
    connection = cast(dict[str, object], result["connection"])
    assert connection["status"] == "CONNECTED"
    ai.revoke(context.actor, cast(int, connection["row_version"]))
    with context.sessions() as session:
        assert session.get(RecoveryAiConnection, context.actor.agency_id).credential_ciphertext is None
