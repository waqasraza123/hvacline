import asyncio
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select, update
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from insurance_operations.application import create_app
from insurance_operations.conversations.contracts import (
    ConnectionGrant,
    ProviderSessionMetadata,
)
from insurance_operations.database.models.conversation import (
    ConversationIntake,
    ConversationSession,
    ConversationSessionStatus,
)
from insurance_operations.database.models.customer import Customer
from insurance_operations.database.models.hvac import Appointment, HvacServiceRequest
from insurance_operations.database.models.identity import (
    Agency,
    AgencyEnvironment,
    AgencyMembership,
    AppUser,
)
from insurance_operations.database.models.lead import AgencyLead
from insurance_operations.database.models.operations import AuditEvent
from insurance_operations.settings import (
    ApiSettings,
    DatabaseSettings,
    RuntimeEnvironment,
)

type JsonValue = (
    bool | int | float | str | list[JsonValue] | dict[str, JsonValue] | None
)
type JsonObject = dict[str, JsonValue]


class FakeConversationProvider:
    def authorize_session(self) -> ConnectionGrant:
        return ConnectionGrant(
            transport="webrtc",
            credential="short-lived-test-credential",
            metadata=ProviderSessionMetadata(
                adapter="test_adapter",
                adapter_version="1",
                external_session_reference=f"external-{uuid4()}",
            ),
        )

    def close(self) -> None:
        return None


@dataclass(frozen=True)
class DevelopmentConversationApi:
    application: FastAPI
    agency_id: UUID
    app_user_id: UUID


@pytest.fixture
def development_conversation_api(
    migrated_database: Engine,
    database_settings: DatabaseSettings,
) -> Iterator[DevelopmentConversationApi]:
    agency = Agency(
        name="Synthetic Voice Test Agency",
        slug=f"synthetic-voice-{uuid4()}",
        environment_kind=AgencyEnvironment.DEVELOPMENT.value,
    )
    app_user = AppUser(
        auth_subject=uuid4(),
        display_name="Synthetic Voice Tester",
    )
    with Session(migrated_database) as session, session.begin():
        session.add_all([agency, app_user])
        session.flush()
        session.add(
            AgencyMembership(
                agency_id=agency.id,
                app_user_id=app_user.id,
            )
        )
        agency_id = agency.id
        app_user_id = app_user.id

    settings = ApiSettings(
        app_environment=RuntimeEnvironment.DEVELOPMENT,
        api_host="127.0.0.1",
        api_port=8000,
        database_url=database_settings.runtime_database_url,
        database_ssl_mode=database_settings.database_ssl_mode,
        conversation_ai_enabled=True,
        development_actor_user_id=app_user_id,
        elevenlabs_api_key="test-secret",
        elevenlabs_agent_id="agent_test",
        elevenlabs_privacy_confirmed=True,
    )
    yield DevelopmentConversationApi(
        create_app(settings, migrated_database, FakeConversationProvider()),
        agency_id,
        app_user_id,
    )


async def post_json(
    application: FastAPI,
    path: str,
    body: JsonObject,
    *,
    idempotency_key: str | None = None,
) -> tuple[int, dict[str, object], dict[str, str]]:
    headers = {"Idempotency-Key": idempotency_key} if idempotency_key else {}
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(path, headers=headers, json=body)
    response_body = response.json()
    assert isinstance(response_body, dict)
    return response.status_code, response_body, dict(response.headers)


async def request_json(
    application: FastAPI,
    method: str,
    path: str,
    body: JsonObject | None = None,
    *,
    idempotency_key: str | None = None,
) -> tuple[int, dict[str, object], dict[str, str]]:
    headers = {"Idempotency-Key": idempotency_key} if idempotency_key else {}
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.request(method, path, headers=headers, json=body)
    response_body = response.json()
    assert isinstance(response_body, dict)
    return response.status_code, response_body, dict(response.headers)


def authorize_session(
    api: DevelopmentConversationApi,
) -> tuple[int, dict[str, object], dict[str, str]]:
    return asyncio.run(
        post_json(
            api.application,
            "/api/v1/development/conversation-sessions",
            {
                "ai_disclosure_accepted": True,
                "microphone_consent_granted": True,
                "synthetic_data_acknowledged": True,
            },
        )
    )


def test_session_authorization_requires_all_acknowledgements(
    development_conversation_api: DevelopmentConversationApi,
) -> None:
    status_code, body, _headers = asyncio.run(
        post_json(
            development_conversation_api.application,
            "/api/v1/development/conversation-sessions",
            {
                "ai_disclosure_accepted": True,
                "microphone_consent_granted": True,
                "synthetic_data_acknowledged": False,
            },
        )
    )

    assert status_code == 422
    error = body["error"]
    assert isinstance(error, dict)
    assert error["code"] == "SYNTHETIC_DATA_ACKNOWLEDGEMENT_REQUIRED"


def test_confirmed_intake_is_owned_audited_transactional_and_idempotent(
    development_conversation_api: DevelopmentConversationApi,
    migrated_database: Engine,
) -> None:
    status_code, authorization, _headers = authorize_session(
        development_conversation_api
    )
    assert status_code == 201
    session_id = authorization["session_id"]
    assert isinstance(session_id, str)
    connection = authorization["connection"]
    assert isinstance(connection, dict)
    assert connection["credential"] == "short-lived-test-credential"

    end_status, _end_body, _headers = asyncio.run(
        post_json(
            development_conversation_api.application,
            f"/api/v1/development/conversation-sessions/{session_id}/end",
            {"outcome": "COMPLETED"},
        )
    )
    assert end_status == 200

    confirmation: JsonObject = {
        "conversation_session_id": session_id,
        "customer": {
            "full_name": "Synthetic Sample Customer",
            "email": "synthetic@example.com",
        },
        "intake_intent": "Explore a synthetic renters insurance scenario.",
        "transcript": [
            {"speaker": "AGENT", "text": "How may I help with insurance?"},
            {"speaker": "USER", "text": "I want to discuss renters coverage."},
        ],
    }
    first = asyncio.run(
        post_json(
            development_conversation_api.application,
            "/api/v1/development/conversation-intakes",
            confirmation,
            idempotency_key="confirm-synthetic-intake",
        )
    )
    second = asyncio.run(
        post_json(
            development_conversation_api.application,
            "/api/v1/development/conversation-intakes",
            confirmation,
            idempotency_key="confirm-synthetic-intake",
        )
    )

    assert first[0] == 201
    assert second[0] == 201
    assert second[1] == first[1]
    assert second[2]["idempotent-replayed"] == "true"
    lead_id = first[1]["lead_id"]
    assert isinstance(lead_id, str)
    with Session(migrated_database) as session:
        customer_count = session.scalar(
            select(func.count())
            .select_from(Customer)
            .where(Customer.agency_id == development_conversation_api.agency_id)
        )
        intake_count = session.scalar(
            select(func.count())
            .select_from(ConversationIntake)
            .where(
                ConversationIntake.agency_id == development_conversation_api.agency_id
            )
        )
        lead_count = session.scalar(
            select(func.count())
            .select_from(AgencyLead)
            .where(AgencyLead.agency_id == development_conversation_api.agency_id)
        )
        audit_events = session.scalars(
            select(AuditEvent).where(
                AuditEvent.agency_id == development_conversation_api.agency_id
            )
        ).all()
        conversation_session = session.get(ConversationSession, UUID(session_id))

    assert customer_count == 1
    assert intake_count == 1
    assert lead_count == 1
    assert len(audit_events) == 3
    assert conversation_session is not None
    assert conversation_session.status == ConversationSessionStatus.CONFIRMED.value
    assert all(
        "synthetic@example.com" not in str(event.details) for event in audit_events
    )

    with pytest.raises(DBAPIError), migrated_database.begin() as connection:
        connection.execute(
            update(ConversationIntake)
            .where(
                ConversationIntake.agency_id == development_conversation_api.agency_id
            )
            .values(intake_intent="Mutated intent")
        )


def test_active_session_concurrency_is_limited_to_one(
    development_conversation_api: DevelopmentConversationApi,
) -> None:
    first_status, _body, _headers = authorize_session(development_conversation_api)
    second_status, second_body, _headers = authorize_session(
        development_conversation_api
    )

    assert first_status == 201
    assert second_status == 409
    error = second_body["error"]
    assert isinstance(error, dict)
    assert error["code"] == "CONVERSATION_ALREADY_ACTIVE"


def test_session_over_duration_limit_cannot_enter_review(
    development_conversation_api: DevelopmentConversationApi,
    migrated_database: Engine,
) -> None:
    status_code, body, _headers = authorize_session(development_conversation_api)
    assert status_code == 201
    session_id = body["session_id"]
    assert isinstance(session_id, str)
    with migrated_database.begin() as connection:
        connection.execute(
            update(ConversationSession)
            .where(ConversationSession.id == UUID(session_id))
            .values(authorized_at=datetime.now(UTC) - timedelta(seconds=181))
        )

    end_status, end_body, _headers = asyncio.run(
        post_json(
            development_conversation_api.application,
            f"/api/v1/development/conversation-sessions/{session_id}/end",
            {"outcome": "COMPLETED"},
        )
    )

    assert end_status == 200
    assert end_body["status"] == "EXPIRED"
    assert end_body["review_available"] is False


def test_session_authorizations_are_limited_to_ten_per_utc_day(
    development_conversation_api: DevelopmentConversationApi,
) -> None:
    for _index in range(10):
        status_code, body, _headers = authorize_session(development_conversation_api)
        assert status_code == 201
        session_id = body["session_id"]
        assert isinstance(session_id, str)
        end_status, _end_body, _headers = asyncio.run(
            post_json(
                development_conversation_api.application,
                f"/api/v1/development/conversation-sessions/{session_id}/end",
                {"outcome": "INTERRUPTED"},
            )
        )
        assert end_status == 200

    status_code, body, _headers = authorize_session(development_conversation_api)

    assert status_code == 429
    error = body["error"]
    assert isinstance(error, dict)
    assert error["code"] == "CONVERSATION_DAILY_LIMIT_REACHED"


def test_lead_lifecycle_detail_and_handoff_are_versioned_and_idempotent(
    development_conversation_api: DevelopmentConversationApi,
) -> None:
    authorization_status, authorization, _headers = authorize_session(
        development_conversation_api
    )
    assert authorization_status == 201
    session_id = authorization["session_id"]
    assert isinstance(session_id, str)
    end_status, _end_body, _headers = asyncio.run(
        post_json(
            development_conversation_api.application,
            f"/api/v1/development/conversation-sessions/{session_id}/end",
            {"outcome": "COMPLETED"},
        )
    )
    assert end_status == 200
    confirmation_status, confirmation, _headers = asyncio.run(
        post_json(
            development_conversation_api.application,
            "/api/v1/development/conversation-intakes",
            {
                "conversation_session_id": session_id,
                "customer": {
                    "full_name": "Synthetic Handoff Customer",
                    "email": "handoff@example.com",
                    "phone": "+1 555 010 0199",
                },
                "intake_intent": "Request a synthetic auto insurance follow-up.",
                "urgency": "HIGH",
                "transcript": [
                    {"speaker": "AGENT", "text": "How may I help?"},
                    {"speaker": "USER", "text": "Please have someone call me."},
                ],
            },
            idempotency_key="create-lead-for-handoff",
        )
    )
    assert confirmation_status == 201
    lead_id = confirmation["lead_id"]
    assert isinstance(lead_id, str)

    list_status, lead_list, _headers = asyncio.run(
        request_json(
            development_conversation_api.application,
            "GET",
            "/api/v1/development/leads?status=NEW&limit=10&offset=0",
        )
    )
    assert list_status == 200
    items = lead_list["items"]
    assert isinstance(items, list)
    assert len(items) == 1
    assert lead_list["total"] == 1
    listed_lead = items[0]
    assert isinstance(listed_lead, dict)
    assert listed_lead["urgency"] == "HIGH"

    detail_status, detail, _headers = asyncio.run(
        request_json(
            development_conversation_api.application,
            "GET",
            f"/api/v1/development/leads/{lead_id}",
        )
    )
    assert detail_status == 200
    intake = detail["intake"]
    assert isinstance(intake, dict)
    transcript = intake["transcript"]
    assert isinstance(transcript, list)
    assert len(transcript) == 2
    audit_history = detail["audit_history"]
    assert isinstance(audit_history, list)
    assert any(
        isinstance(event, dict) and event["event_type"] == "LEAD_CREATED"
        for event in audit_history
    )

    update_status, updated, _headers = asyncio.run(
        request_json(
            development_conversation_api.application,
            "PUT",
            f"/api/v1/development/leads/{lead_id}",
            {
                "summary": "Synthetic auto inquiry requiring prompt follow-up.",
                "urgency": "NORMAL",
                "expected_row_version": 1,
            },
        )
    )
    assert update_status == 200
    assert updated["row_version"] == 2

    stale_status, stale, _headers = asyncio.run(
        request_json(
            development_conversation_api.application,
            "PUT",
            f"/api/v1/development/leads/{lead_id}",
            {
                "summary": "Stale synthetic update.",
                "urgency": "LOW",
                "expected_row_version": 1,
            },
        )
    )
    assert stale_status == 409
    stale_error = stale["error"]
    assert isinstance(stale_error, dict)
    assert stale_error["code"] == "LEAD_VERSION_CONFLICT"

    transition_status, transitioned, _headers = asyncio.run(
        post_json(
            development_conversation_api.application,
            f"/api/v1/development/leads/{lead_id}/status",
            {"status": "CONTACTED", "expected_row_version": 2},
        )
    )
    assert transition_status == 200
    assert transitioned["status"] == "CONTACTED"
    assert transitioned["row_version"] == 3

    handoff_body: JsonObject = {
        "request_kind": "CALLBACK",
        "preferred_contact_method": "PHONE",
        "reason": "Caller requested a licensed team member.",
        "availability": "Weekday afternoon",
    }
    first_handoff = asyncio.run(
        request_json(
            development_conversation_api.application,
            "POST",
            f"/api/v1/development/leads/{lead_id}/handoff-requests",
            handoff_body,
            idempotency_key="synthetic-handoff-request",
        )
    )
    replayed_handoff = asyncio.run(
        request_json(
            development_conversation_api.application,
            "POST",
            f"/api/v1/development/leads/{lead_id}/handoff-requests",
            handoff_body,
            idempotency_key="synthetic-handoff-request",
        )
    )
    assert first_handoff[0] == 201
    assert replayed_handoff[0] == 201
    assert replayed_handoff[1] == first_handoff[1]
    assert replayed_handoff[2]["idempotent-replayed"] == "true"
    changed_handoff_body = dict(handoff_body)
    changed_handoff_body["availability"] = "Weekend morning"
    changed_handoff = asyncio.run(
        request_json(
            development_conversation_api.application,
            "POST",
            f"/api/v1/development/leads/{lead_id}/handoff-requests",
            changed_handoff_body,
            idempotency_key="synthetic-handoff-request",
        )
    )
    assert changed_handoff[0] == 409
    changed_error = changed_handoff[1]["error"]
    assert isinstance(changed_error, dict)
    assert changed_error["code"] == "IDEMPOTENCY_KEY_REUSED"
    handoff_id = first_handoff[1]["id"]
    assert isinstance(handoff_id, str)

    handoff_status, acknowledged, _headers = asyncio.run(
        post_json(
            development_conversation_api.application,
            f"/api/v1/development/handoff-requests/{handoff_id}/status",
            {"status": "ACKNOWLEDGED", "expected_row_version": 1},
        )
    )
    assert handoff_status == 200
    assert acknowledged["status"] == "ACKNOWLEDGED"
    assert acknowledged["row_version"] == 2

    invalid_status, invalid, _headers = asyncio.run(
        post_json(
            development_conversation_api.application,
            f"/api/v1/development/leads/{lead_id}/status",
            {"status": "NEW", "expected_row_version": 3},
        )
    )
    assert invalid_status == 409
    error = invalid["error"]
    assert isinstance(error, dict)
    assert error["code"] == "LEAD_STATUS_TRANSITION_INVALID"


@pytest.mark.parametrize("hazardous", [False, True])
def test_browser_confirmation_creates_one_hvac_request_on_retry(
    development_conversation_api: DevelopmentConversationApi,
    migrated_database: Engine,
    hazardous: bool,
) -> None:
    api = development_conversation_api
    status_code, authorization, _ = authorize_session(api)
    assert status_code == 201
    session_id = authorization["session_id"]
    assert isinstance(session_id, str)
    ended, _, _ = asyncio.run(post_json(
        api.application,
        f"/api/v1/development/conversation-sessions/{session_id}/end",
        {"outcome": "COMPLETED"},
    ))
    assert ended == 200
    payload: JsonObject = {
        "conversation_session_id": session_id,
        "customer": {
            "full_name": "Fictional HVAC Caller", "phone": "+12025550123",
            "address": {
                "line1": "123 Example Street", "city": "New York",
                "state_code": "NY", "postal_code": "10001",
            },
        },
        "intake_intent": "AC stopped cooling",
        "service": {
            "kind": "AC_REPAIR", "equipment_issue": "AC stopped cooling",
            "preferred_window": "Tomorrow morning", "hazardous_condition": hazardous,
        },
        "transcript": [
            {"speaker": "AGENT", "text": "Please review your fictional details."},
            {"speaker": "USER", "text": "I confirm these fictional details."},
        ],
    }
    first = asyncio.run(post_json(api.application,
        "/api/v1/development/conversation-intakes", payload,
        idempotency_key="browser-hvac-confirm"))
    replay = asyncio.run(post_json(api.application,
        "/api/v1/development/conversation-intakes", payload,
        idempotency_key="browser-hvac-confirm"))
    assert first[0] == 201
    assert replay[1] == first[1]
    assert replay[2]["idempotent-replayed"] == "true"
    request_id = first[1]["service_request_id"]
    assert isinstance(request_id, str)
    with Session(migrated_database) as session:
        row = session.get(HvacServiceRequest, UUID(request_id))
        assert row is not None
        assert row.agency_id == api.agency_id
        assert row.status == ("HANDOFF_REQUESTED" if hazardous else "OPEN")
        assert row.customer_details["phone"] == "+12025550123"
        assert session.scalar(select(func.count()).select_from(HvacServiceRequest)
            .where(HvacServiceRequest.agency_id == api.agency_id)) == 1


def test_browser_voice_books_only_after_two_spoken_confirmations(
    development_conversation_api: DevelopmentConversationApi,
    migrated_database: Engine,
) -> None:
    api = development_conversation_api
    day = (datetime.now(UTC) + timedelta(days=2)).date()
    windows: list[JsonValue] = [
        {"weekday": day.weekday(), "start": "08:00", "end": "17:00"}
    ]
    configured, _, _ = asyncio.run(request_json(
        api.application, "PUT", "/api/v1/development/hvac/schedule",
        {
            "expected_version": 0, "enabled": True,
            "timezone": "America/New_York", "postal_codes": ["10001"],
            "windows": windows,
            "teams": [{"key": "team-a", "name": "Service team", "windows": windows}],
            "notice_minutes": 0,
        },
    ))
    assert configured == 200
    status_code, authorization, _ = authorize_session(api)
    assert status_code == 201
    session_id = authorization["session_id"]
    assert isinstance(session_id, str)
    base = f"/api/v1/development/conversation-sessions/{session_id}/booking"

    def post(path: str, body: JsonObject) -> tuple[int, dict[str, object], dict[str, str]]:
        return asyncio.run(post_json(api.application, base + path, body))

    assert post("/availability", {"day": day.isoformat()})[0] == 409
    payload: JsonObject = {
        "conversation_session_id": session_id,
        "customer": {
            "full_name": "Fictional Browser Caller", "phone": "+12025550123",
            "address": {
                "line1": "123 Example Street", "city": "New York",
                "state_code": "NY", "postal_code": "10001",
            },
        },
        "intake_intent": "AC stopped cooling",
        "service": {
            "kind": "AC_REPAIR", "equipment_issue": "AC stopped cooling",
            "preferred_window": day.isoformat(), "hazardous_condition": False,
        },
        "spoken_confirmation": True,
    }
    prepared_status, prepared, _ = post("/intake-readback", {
        "customer": payload["customer"], "service": payload["service"],
    })
    assert prepared_status == 200
    readback = prepared["readback"]
    assert isinstance(readback, str)
    payload["transcript"] = [
        {"speaker": "AGENT", "text": readback},
        {"speaker": "USER", "text": "Yes, but change the address."},
    ]
    denied = asyncio.run(post_json(api.application,
        "/api/v1/development/conversation-intakes", payload,
        idempotency_key="spoken-browser-intake"))
    assert denied[0] == 422
    with Session(migrated_database) as session:
        assert session.scalar(select(func.count()).select_from(HvacServiceRequest)
            .where(HvacServiceRequest.agency_id == api.agency_id)) == 0
    payload["transcript"] = [
        {"speaker": "AGENT", "text": readback},
        {"speaker": "USER", "text": "Yes, save my request."},
    ]
    saved = asyncio.run(post_json(api.application,
        "/api/v1/development/conversation-intakes", payload,
        idempotency_key="spoken-browser-intake"))
    replay = asyncio.run(post_json(api.application,
        "/api/v1/development/conversation-intakes", payload,
        idempotency_key="spoken-browser-intake"))
    assert saved[0] == 201
    assert replay[1] == saved[1]
    assert authorize_session(api)[0] == 409
    available_status, available, _ = post("/availability", {"day": day.isoformat()})
    assert available_status == 200
    slots = available["slots"]
    assert isinstance(slots, list) and slots
    slot = slots[0]
    reservation: JsonObject = {
        "team_key": slot["team_key"], "starts_at": slot["starts_at"],
        "idempotency_key": "spoken-browser-reservation",
    }
    held_status, held, _ = post("/reservations", reservation)
    assert held_status == 200
    appointment = held["appointment"]
    assert isinstance(appointment, dict)
    assert appointment["status"] == "HELD"
    assert post("/reservations", reservation)[1]["appointment"] == appointment
    appointment_id = appointment["id"]
    booking_readback = held["readback"]
    assert isinstance(booking_readback, str)
    confirmation: JsonObject = {
        "explicit_confirmation": True,
        "transcript": [
            {"speaker": "AGENT", "text": booking_readback},
            {"speaker": "USER", "text": "No, that time does not work."},
        ],
    }
    assert post(f"/appointments/{appointment_id}/confirm", confirmation)[0] == 409
    confirmation["transcript"] = [
        {"speaker": "AGENT", "text": booking_readback},
        {"speaker": "USER", "text": "Yes, confirm my appointment."},
    ]
    confirmed_status, confirmed, _ = post(f"/appointments/{appointment_id}/confirm", confirmation)
    assert confirmed_status == 200
    confirmed_appointment = confirmed["appointment"]
    assert isinstance(confirmed_appointment, dict)
    assert confirmed_appointment["status"] == "CONFIRMED"
    assert post(f"/appointments/{appointment_id}/release", {})[0] == 409
    with Session(migrated_database) as session:
        assert session.scalar(select(func.count()).select_from(Appointment)
            .where(Appointment.agency_id == api.agency_id)) == 1
    ended = asyncio.run(post_json(api.application,
        f"/api/v1/development/conversation-sessions/{session_id}/end",
        {"outcome": "INTERRUPTED"}))
    assert ended[0] == 200
    assert ended[1]["status"] == "CONFIRMED"
    assert post("/availability", {"day": day.isoformat()})[0] == 409
    assert authorize_session(api)[0] == 201
