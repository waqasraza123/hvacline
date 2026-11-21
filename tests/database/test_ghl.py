import json
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4
from unittest.mock import patch

import httpx
import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.actors import ActorContext
from insurance_operations.customers import CustomerInput, customer_from_input
from insurance_operations.database.models.conversation import (
    ConversationIntake,
    ConversationSession,
)
from insurance_operations.database.models.ghl import GhlConnection, GhlDelivery
from insurance_operations.database.models.hvac import Appointment, HvacServiceRequest
from insurance_operations.database.models.identity import Agency, AppUser
from insurance_operations.database.models.lead import AgencyLead, LeadHandoffRequest
from insurance_operations.database.models.operations import AuditEvent
from insurance_operations.errors import ApiError
from insurance_operations.ghl.jobs import collect_ghl_jobs, deliver_ghl
from insurance_operations.ghl.provider import GhlClient
from insurance_operations.ghl.schemas import (
    ConnectionInput,
    CredentialInput,
    RetryInput,
)
from insurance_operations.ghl.service import GhlBusy, GhlService, agency_lock
from insurance_operations.settings import DatabaseSettings


@dataclass
class Remote:
    contacts: dict[str, dict[str, object]] = field(default_factory=dict)
    opportunities: dict[str, dict[str, object]] = field(default_factory=dict)
    requests: list[tuple[str, str]] = field(default_factory=list)
    failure: str = ""

    def handle(self, request: httpx.Request) -> httpx.Response:
        path, method = request.url.path, request.method
        self.requests.append((method, path))
        if self.failure == "unauthorized":
            return httpx.Response(401)
        if self.failure == "rate-limit":
            self.failure = ""
            return httpx.Response(429, headers={"Retry-After": "120"})
        if path == "/opportunities/pipelines":
            return httpx.Response(
                200,
                json={
                    "pipelines": [
                        {
                            "id": "pipeline",
                            "name": "Synthetic pipeline",
                            "locationId": "location",
                            "stages": [
                                {"id": key, "name": key}
                                for key in ("new", "booked", "cancelled", "attention")
                            ],
                        }
                    ]
                },
            )
        if path.endswith("customFields"):
            return httpx.Response(
                200,
                json={
                    "customFields": [
                        {
                            "id": key,
                            "name": key,
                            "locationId": "location",
                            "model": "opportunity",
                            "dataType": "LARGE_TEXT",
                        }
                        for key in ("reference", "summary", "booking")
                    ]
                },
            )
        if path == "/contacts/lookup":
            key = "email" if "email" in request.url.params else "phone"
            value = request.url.params[key]
            return httpx.Response(
                200,
                json={
                    "contacts": [
                        record
                        for record in self.contacts.values()
                        if record.get(key) == value
                    ]
                },
            )
        if path == "/contacts/" and method == "POST":
            identifier = f"contact-{len(self.contacts) + 1}"
            record = {**json.loads(request.content), "id": identifier}
            self.contacts[identifier] = record
            if self.failure == "lost-contact":
                self.failure = ""
                return httpx.Response(503)
            return httpx.Response(201, json={"contact": record})
        if path == "/opportunities/" and method == "POST":
            identifier = f"opportunity-{len(self.opportunities) + 1}"
            record = {**json.loads(request.content), "id": identifier}
            self.opportunities[identifier] = record
            if self.failure == "lost-opportunity":
                self.failure = ""
                return httpx.Response(503)
            return httpx.Response(201, json={"opportunity": record})
        if path == "/opportunities/search":
            reference = request.url.params["query"]
            return httpx.Response(
                200,
                json={
                    "opportunities": [
                        record
                        for record in self.opportunities.values()
                        if record["name"] == reference
                    ],
                    "meta": {"nextPage": ""},
                },
            )
        if path.startswith("/opportunities/"):
            identifier = path.rsplit("/", 1)[1]
            record = self.opportunities.get(identifier)
            if record is None:
                return httpx.Response(404)
            if method == "PUT":
                record.update(json.loads(request.content))
            return httpx.Response(200, json={"opportunity": record})
        raise AssertionError(f"Unexpected synthetic route: {method} {path}")

    @contextmanager
    def factory(self, token: str, location_id: str) -> Iterator[GhlClient]:
        with httpx.Client(transport=httpx.MockTransport(self.handle)) as client:
            yield GhlClient(client, token, location_id)


def configuration() -> ConnectionInput:
    return ConnectionInput.model_validate(
        {
            "location_id": "location",
            "token": "synthetic-private-token",
            "pipeline_id": "pipeline",
            "stages": {key: key for key in ("new", "booked", "cancelled", "attention")},
            "fields": {key: key for key in ("reference", "summary", "booking")},
            "multiple_opportunities_confirmed": True,
        }
    )


@dataclass
class Harness:
    sessions: sessionmaker[Session]
    service: GhlService
    owner: ActorContext
    foreign: ActorContext
    remote: Remote

    def lead(self) -> UUID:
        with self.sessions() as session, session.begin():
            return persist_lead(session, self.owner)

    def delivery(self, lead_id: UUID) -> GhlDelivery:
        with self.sessions() as session:
            row = session.scalar(
                select(GhlDelivery).where(GhlDelivery.lead_id == lead_id)
            )
            assert row is not None
            return row

    def deliver(self, lead_id: UUID) -> GhlDelivery:
        identifier = self.delivery(lead_id).id
        deliver_ghl(self.sessions, identifier, self.remote.factory)
        return self.delivery(lead_id)

    def due(self, lead_id: UUID) -> None:
        with self.sessions() as session, session.begin():
            delivery = session.get(GhlDelivery, self.delivery(lead_id).id)
            assert delivery is not None
            delivery.next_attempt_at = datetime.now(UTC) - timedelta(seconds=1)


@pytest.fixture
def harness(
    migrated_database: Engine, database_settings: DatabaseSettings
) -> Iterator[Harness]:
    with migrated_database.connect() as connection:
        transaction = connection.begin()
        settings = database_settings.model_copy(
            update={
                "ghl_enabled": True,
                "ghl_token_encryption_key": SecretStr(Fernet.generate_key().decode()),
            }
        )
        sessions = sessionmaker(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
            info={"integration_settings": settings},
        )
        actors = []
        with sessions() as session, session.begin():
            for _ in range(2):
                agency = Agency(
                    name="Synthetic GHL business",
                    slug=f"ghl-{uuid4()}",
                    environment_kind="DEVELOPMENT",
                )
                user = AppUser(auth_subject=uuid4(), display_name="Synthetic owner")
                session.add_all([agency, user])
                session.flush()
                actors.append(
                    ActorContext(
                        user.id,
                        user.display_name,
                        agency.id,
                        agency.name,
                        agency.environment_kind,
                    )
                )
        remote = Remote()
        service = GhlService(sessions, settings, remote.factory)
        try:
            yield Harness(sessions, service, actors[0], actors[1], remote)
        finally:
            transaction.rollback()


def persist_lead(session: Session, actor: ActorContext) -> UUID:
    now = datetime.now(UTC)
    customer = customer_from_input(
        CustomerInput(full_name="Synthetic caller", email="synthetic@example.com"),
        actor,
    )
    session.add(customer)
    session.flush()
    conversation = ConversationSession(
        agency_id=actor.agency_id,
        initiated_by=actor.app_user_id,
        channel="BROWSER",
        input_mode="TEXT",
        status="CONFIRMED",
        disclosure_accepted_at=now,
        maximum_duration_seconds=180,
        authorization_expires_at=now + timedelta(minutes=3),
        confirmation_expires_at=now + timedelta(minutes=30),
        confirmed_at=now,
        provider_metadata={},
    )
    session.add(conversation)
    session.flush()
    intake = ConversationIntake(
        agency_id=actor.agency_id,
        customer_id=customer.id,
        conversation_session_id=conversation.id,
        created_by=actor.app_user_id,
        intake_intent="Synthetic HVAC request",
        confirmed_at=now,
        confirmed_transcript=[
            {"speaker": "USER", "text": "Synthetic request"},
            {"speaker": "USER", "text": "yes"},
        ],
    )
    session.add(intake)
    session.flush()
    lead = AgencyLead(
        agency_id=actor.agency_id,
        customer_id=customer.id,
        conversation_intake_id=intake.id,
        summary="Synthetic HVAC request",
        urgency="NORMAL",
        status="NEW",
        created_by=actor.app_user_id,
        updated_by=actor.app_user_id,
    )
    session.add(lead)
    session.flush()
    return lead.id


def request_and_hold(harness: Harness, lead_id: UUID) -> tuple[UUID, UUID]:
    with harness.sessions() as session, session.begin():
        lead = session.get(AgencyLead, lead_id)
        assert lead is not None
        intake = session.get(ConversationIntake, lead.conversation_intake_id)
        assert intake is not None
        request = HvacServiceRequest(
            agency_id=harness.owner.agency_id,
            conversation_session_id=intake.conversation_session_id,
            customer_details={},
            service_details={"hazardous_condition": False},
            status="OPEN",
            fingerprint="synthetic",
            confirmed_at=datetime.now(UTC),
        )
        session.add(request)
        session.flush()
        now = datetime.now(UTC)
        appointment = Appointment(
            agency_id=harness.owner.agency_id,
            service_request_id=request.id,
            team_key="synthetic-team",
            starts_at=now + timedelta(days=1),
            ends_at=now + timedelta(days=1, hours=1),
            status="HELD",
            hold_expires_at=now + timedelta(minutes=5),
            idempotency_key=str(uuid4()),
            fingerprint="synthetic",
        )
        session.add(appointment)
        session.flush()
        return request.id, appointment.id


def test_transactional_capture_rolls_back_and_does_not_backfill(
    harness: Harness,
) -> None:
    historical = harness.lead()
    harness.service.connect(harness.owner, configuration())
    with harness.sessions() as session, session.begin():
        lead = session.get(AgencyLead, historical)
        assert lead is not None
        lead.summary = "Synthetic historical edit"
    with harness.sessions() as session:
        assert session.scalar(select(GhlDelivery.id)) is None
    identifier = uuid4()
    with pytest.raises(RuntimeError, match="rollback"):
        with harness.sessions() as session, session.begin():
            identifier = persist_lead(session, harness.owner)
            assert session.scalar(
                select(GhlDelivery.id).where(GhlDelivery.lead_id == identifier)
            )
            raise RuntimeError("rollback")
    with harness.sessions() as session:
        assert session.get(AgencyLead, identifier) is None
        assert session.scalar(select(GhlDelivery.id)) is None


def test_repeat_requests_share_contact_but_have_separate_opportunities(
    harness: Harness,
) -> None:
    harness.service.connect(harness.owner, configuration())
    first, second = harness.lead(), harness.lead()
    assert harness.deliver(first).status == "SYNCED"
    assert harness.deliver(second).status == "SYNCED"
    assert len(harness.remote.contacts) == 1
    assert len(harness.remote.opportunities) == 2
    assert harness.delivery(first).contact_id == harness.delivery(second).contact_id
    assert (
        harness.delivery(first).opportunity_id
        != harness.delivery(second).opportunity_id
    )
    before = len(harness.remote.requests)
    harness.deliver(first)
    assert len(harness.remote.requests) == before


@pytest.mark.parametrize("failure", ["lost-contact", "lost-opportunity"])
def test_lost_response_recovers_completed_step_without_duplicate(
    harness: Harness, failure: str
) -> None:
    harness.service.connect(harness.owner, configuration())
    lead_id = harness.lead()
    harness.remote.failure = failure
    assert harness.deliver(lead_id).status == "RETRYING"
    harness.due(lead_id)
    assert harness.deliver(lead_id).status == "SYNCED"
    assert len(harness.remote.contacts) == len(harness.remote.opportunities) == 1


def test_missing_ambiguous_creation_requires_explicit_absence_review(
    harness: Harness,
) -> None:
    harness.service.connect(harness.owner, configuration())
    lead_id = harness.lead()
    harness.remote.failure = "lost-opportunity"
    harness.deliver(lead_id)
    harness.remote.opportunities.clear()
    harness.due(lead_id)
    delivery = harness.deliver(lead_id)
    assert delivery.status == "NEEDS_REVIEW" and delivery.opportunity_unknown
    before = harness.remote.requests.count(("POST", "/opportunities/"))
    harness.deliver(lead_id)
    assert harness.remote.requests.count(("POST", "/opportunities/")) == before
    harness.service.retry(
        harness.owner, delivery.id, RetryInput(confirm_remote_absent=True)
    )
    assert harness.deliver(lead_id).status == "SYNCED"
    assert harness.remote.requests.count(("POST", "/opportunities/")) == before + 1


def test_stage_changes_follow_confirmed_bookings_and_handoffs(harness: Harness) -> None:
    harness.service.connect(harness.owner, configuration())
    lead_id = harness.lead()
    request_id, appointment_id = request_and_hold(harness, lead_id)
    first = harness.deliver(lead_id)
    assert first.last_stage_id == "new"
    with harness.sessions() as session, session.begin():
        appointment = session.get(Appointment, appointment_id)
        assert appointment is not None
        appointment.status = "CONFIRMED"
        session.add(
            AuditEvent(
                agency_id=harness.owner.agency_id,
                actor_type="STAFF",
                actor_user_id=harness.owner.app_user_id,
                event_type="HVAC_APPOINTMENT_CONFIRMED",
                occurred_at=datetime.now(UTC),
                summary="Synthetic confirmation",
                details={"appointment_id": str(appointment_id)},
                correlation_id=uuid4(),
                event_version=1,
            )
        )
    assert harness.deliver(lead_id).last_stage_id == "booked"
    with harness.sessions() as session, session.begin():
        appointment = session.get(Appointment, appointment_id)
        assert appointment is not None
        appointment.status = "CANCELLED"
    assert harness.deliver(lead_id).last_stage_id == "cancelled"
    with harness.sessions() as session, session.begin():
        request = session.get(HvacServiceRequest, request_id)
        assert request is not None
        request.service_details = {"hazardous_condition": True}
        request.status = "HANDOFF_REQUESTED"
    assert harness.deliver(lead_id).last_stage_id == "attention"


def test_stage_changed_by_ghl_user_is_not_overwritten(harness: Harness) -> None:
    harness.service.connect(harness.owner, configuration())
    lead_id = harness.lead()
    delivery = harness.deliver(lead_id)
    assert delivery.opportunity_id is not None
    harness.remote.opportunities[delivery.opportunity_id]["status"] = "won"
    with harness.sessions() as session, session.begin():
        lead = session.get(AgencyLead, lead_id)
        assert lead is not None
        lead.summary = "Synthetic updated request"
    assert harness.deliver(lead_id).status == "NEEDS_REVIEW"
    assert harness.remote.opportunities[delivery.opportunity_id]["status"] == "won"


def test_released_hold_is_not_reported_as_a_cancelled_booking(harness: Harness) -> None:
    harness.service.connect(harness.owner, configuration())
    lead_id = harness.lead()
    _, appointment_id = request_and_hold(harness, lead_id)
    assert harness.deliver(lead_id).last_stage_id == "new"
    before = harness.delivery(lead_id).desired_version
    with harness.sessions() as session, session.begin():
        appointment = session.get(Appointment, appointment_id)
        assert appointment is not None
        appointment.status = "CANCELLED"
    assert harness.delivery(lead_id).desired_version == before


def test_handoff_lifecycle_coalesces_and_preserves_retryable_state(
    harness: Harness,
) -> None:
    harness.service.connect(harness.owner, configuration())
    lead_id = harness.lead()
    assert harness.deliver(lead_id).last_stage_id == "new"
    with harness.sessions() as session, session.begin():
        handoff = LeadHandoffRequest(
            agency_id=harness.owner.agency_id,
            lead_id=lead_id,
            request_kind="CALLBACK",
            preferred_contact_method="EMAIL",
            reason="Synthetic callback",
            status="REQUESTED",
            transfer_attempted=False,
            created_by=harness.owner.app_user_id,
            updated_by=harness.owner.app_user_id,
        )
        session.add(handoff)
        session.flush()
        handoff_id = handoff.id
    assert harness.deliver(lead_id).last_stage_id == "attention"
    with harness.sessions() as session, session.begin():
        row = session.get(LeadHandoffRequest, handoff_id)
        assert row is not None
        row.status, row.completed_at = "COMPLETED", datetime.now(UTC)
    assert harness.deliver(lead_id).last_stage_id == "new"


def test_token_failure_pauses_connection_and_rate_limit_is_business_wide(
    harness: Harness,
) -> None:
    harness.service.connect(harness.owner, configuration())
    lead_id = harness.lead()
    harness.remote.failure = "rate-limit"
    assert harness.deliver(lead_id).status == "RETRYING"
    assert collect_ghl_jobs(harness.sessions, 10) == []
    with harness.sessions() as session, session.begin():
        connection = session.scalar(select(GhlConnection))
        assert connection is not None
        connection.blocked_until = datetime.now(UTC) - timedelta(seconds=1)
    harness.due(lead_id)
    harness.remote.failure = "unauthorized"
    assert harness.deliver(lead_id).last_error == "GHL_AUTH_REQUIRED"
    current = harness.service.status(harness.owner)["connection"]
    assert isinstance(current, dict) and current["status"] == "ERROR"
    assert collect_ghl_jobs(harness.sessions, 10) == []


def test_reschedule_updates_original_opportunity(harness: Harness) -> None:
    harness.service.connect(harness.owner, configuration())
    lead_id = harness.lead()
    request_id, appointment_id = request_and_hold(harness, lead_id)
    with harness.sessions() as session, session.begin():
        old = session.get(Appointment, appointment_id)
        assert old is not None
        old.status = "CONFIRMED"
    original = harness.deliver(lead_id)
    with harness.sessions() as session, session.begin():
        old = session.get(Appointment, appointment_id)
        assert old is not None
        old.status = "CANCELLED"
        replacement = Appointment(
            agency_id=harness.owner.agency_id,
            service_request_id=request_id,
            team_key=old.team_key,
            starts_at=old.starts_at + timedelta(days=1),
            ends_at=old.ends_at + timedelta(days=1),
            status="CONFIRMED",
            hold_expires_at=datetime.now(UTC),
            idempotency_key=str(uuid4()),
            fingerprint="replacement",
        )
        session.add(replacement)
        session.flush()
        replacement_id = replacement.id
    delivery = harness.deliver(lead_id)
    assert delivery.status == "SYNCED" and delivery.last_stage_id == "booked"
    assert delivery.opportunity_id == original.opportunity_id
    assert len(harness.remote.opportunities) == 1
    record = next(iter(harness.remote.opportunities.values()))
    assert str(replacement_id) in json.dumps(record)


def test_changes_arriving_during_delivery_remain_pending(harness: Harness) -> None:
    harness.service.connect(harness.owner, configuration())
    lead_id = harness.lead()
    original_handle = harness.remote.handle

    def change_during_create(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/opportunities/":
            with harness.sessions() as session, session.begin():
                lead = session.get(AgencyLead, lead_id)
                assert lead is not None
                lead.summary = "Synthetic newer confirmed details"
        return original_handle(request)

    with patch.object(harness.remote, "handle", side_effect=change_during_create):
        first = harness.deliver(lead_id)
    assert first.status == "PENDING" and first.delivered_version < first.desired_version
    assert harness.deliver(lead_id).status == "SYNCED"
    assert len(harness.remote.opportunities) == 1
    assert "Synthetic newer confirmed details" in json.dumps(
        harness.remote.opportunities
    )


def test_pause_rotation_disconnect_and_business_isolation(harness: Harness) -> None:
    harness.service.connect(harness.owner, configuration())
    harness.service.action(harness.owner, "pause")
    lead_id = harness.lead()
    assert collect_ghl_jobs(harness.sessions, 10) == []
    harness.service.rotate(
        harness.owner,
        CredentialInput(location_id="location", token="synthetic-replacement-token"),
    )
    current = harness.service.status(harness.owner)["connection"]
    assert isinstance(current, dict) and current["status"] == "PAUSED"
    harness.service.action(harness.owner, "resume")
    assert harness.deliver(lead_id).status == "SYNCED"
    assert harness.service.deliveries(harness.foreign, 0, 25)["items"] == []
    with pytest.raises(ApiError) as error:
        harness.service.retry(
            harness.foreign, harness.delivery(lead_id).id, RetryInput()
        )
    assert error.value.status_code == 404
    harness.service.action(harness.owner, "disconnect")
    with harness.sessions() as session:
        row = session.scalar(select(GhlConnection))
        assert row is not None and row.token_ciphertext is None
    assert collect_ghl_jobs(harness.sessions, 10) == []


def test_cross_business_delivery_foreign_keys_reject_mixed_ownership(
    harness: Harness,
) -> None:
    connection = harness.service.connect(harness.owner, configuration())
    lead_id = harness.lead()
    with pytest.raises(IntegrityError):
        with harness.sessions() as session, session.begin():
            session.add(
                GhlDelivery(
                    agency_id=harness.foreign.agency_id,
                    connection_id=UUID(str(connection["id"])),
                    lead_id=lead_id,
                )
            )
            session.flush()


def test_independent_sessions_exclude_concurrent_ghl_operations(
    migrated_database: Engine,
) -> None:
    sessions = sessionmaker(bind=migrated_database)
    identifier = uuid4()
    with agency_lock(sessions, identifier):
        with pytest.raises(GhlBusy):
            with agency_lock(sessions, identifier):
                pytest.fail("Concurrent coordinator acquired the same business lock")
    with agency_lock(sessions, identifier):
        pass
