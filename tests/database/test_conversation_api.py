import asyncio
from concurrent.futures import ThreadPoolExecutor
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, func, select, update
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.application import create_app
from insurance_operations.conversations.contracts import (
    ConnectionGrant,
    ConversationInputMode,
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
from insurance_operations.hvac.schemas import (
    AvailabilityInput,
    ReservationInput,
    ScheduleInput,
)
from insurance_operations.hvac.service import SchedulingService
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
    def authorize_session(
        self, *, input_mode: ConversationInputMode = "VOICE"
    ) -> ConnectionGrant:
        return ConnectionGrant(
            transport="websocket" if input_mode == "TEXT" else "webrtc",
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


@pytest.mark.parametrize("input_mode", ["VOICE", "TEXT"])
def test_session_authorization_requires_all_acknowledgements(
    development_conversation_api: DevelopmentConversationApi,
    input_mode: str,
) -> None:
    status_code, body, _headers = asyncio.run(
        post_json(
            development_conversation_api.application,
            "/api/v1/development/conversation-sessions",
            {
                "input_mode": input_mode,
                "ai_disclosure_accepted": True,
                "microphone_consent_granted": input_mode == "VOICE",
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
    first_status, first_body, _headers = authorize_session(development_conversation_api)
    second_status, second_body, headers = authorize_session(
        development_conversation_api
    )

    assert first_status == 201
    assert second_status == 409
    error = second_body["error"]
    assert isinstance(error, dict)
    assert error["code"] == "CONVERSATION_ALREADY_ACTIVE"
    details = error["details"]
    assert isinstance(details, dict)
    assert details["previous_session_id"] == first_body["session_id"]
    assert int(headers["retry-after"]) > 0


def test_repeated_failed_session_cleanup_releases_the_slot(
    development_conversation_api: DevelopmentConversationApi,
) -> None:
    api = development_conversation_api
    status_code, body, _ = authorize_session(api)
    assert status_code == 201
    path = f"/api/v1/development/conversation-sessions/{body['session_id']}/end"
    for outcome in ["FAILED", "INTERRUPTED", "FAILED"]:
        status_code, ended, _ = asyncio.run(
            post_json(api.application, path, {"outcome": outcome})
        )
        assert status_code == 200
        assert ended["status"] == "FAILED"
    assert authorize_session(api)[0] == 201


def test_text_session_has_no_microphone_consent_and_shares_voice_quota(
    development_conversation_api: DevelopmentConversationApi,
    migrated_database: Engine,
) -> None:
    api = development_conversation_api
    try:
        status_code, body, _ = asyncio.run(
            post_json(
                api.application,
                "/api/v1/development/conversation-sessions",
                {
                    "input_mode": "TEXT",
                    "ai_disclosure_accepted": True,
                    "microphone_consent_granted": False,
                    "synthetic_data_acknowledged": True,
                },
            )
        )
        assert status_code == 201
        assert body["input_mode"] == "TEXT"
        connection = body["connection"]
        assert isinstance(connection, dict)
        assert connection["transport"] == "websocket"
        with Session(migrated_database) as session:
            row = session.get(ConversationSession, UUID(str(body["session_id"])))
            assert row is not None
            assert row.input_mode == "TEXT"
            assert row.microphone_consent_at is None
            assert row.disclosure_accepted_at is not None
        assert authorize_session(api)[0] == 409
        with pytest.raises(DBAPIError), migrated_database.begin() as connection:
            connection.execute(
                update(ConversationSession)
                .where(ConversationSession.id == UUID(str(body["session_id"])))
                .values(microphone_consent_at=datetime.now(UTC))
            )
    finally:
        with migrated_database.begin() as connection:
            connection.execute(
                delete(ConversationSession).where(
                    ConversationSession.agency_id == api.agency_id,
                    ConversationSession.input_mode == "TEXT",
                )
            )


@pytest.mark.parametrize("input_mode", ["TEXT", "VOICE"])
def test_browser_modes_still_require_ai_disclosure(
    development_conversation_api: DevelopmentConversationApi,
    input_mode: str,
) -> None:
    status_code, body, _ = asyncio.run(
        post_json(
            development_conversation_api.application,
            "/api/v1/development/conversation-sessions",
            {
                "input_mode": input_mode,
                "ai_disclosure_accepted": False,
                "microphone_consent_granted": input_mode == "VOICE",
                "synthetic_data_acknowledged": True,
            },
        )
    )
    assert status_code == 422
    error = body["error"]
    assert isinstance(error, dict)
    assert error["code"] == "AI_DISCLOSURE_REQUIRED"


@pytest.mark.parametrize(
    ("input_mode", "microphone_consent", "error_code"),
    [
        ("VOICE", False, "MICROPHONE_CONSENT_REQUIRED"),
        ("TEXT", True, "TEXT_SESSION_MICROPHONE_CONSENT_INVALID"),
    ],
)
def test_browser_modes_require_accurate_microphone_consent(
    development_conversation_api: DevelopmentConversationApi,
    input_mode: str,
    microphone_consent: bool,
    error_code: str,
) -> None:
    status_code, body, _ = asyncio.run(
        post_json(
            development_conversation_api.application,
            "/api/v1/development/conversation-sessions",
            {
                "input_mode": input_mode,
                "ai_disclosure_accepted": True,
                "microphone_consent_granted": microphone_consent,
                "synthetic_data_acknowledged": True,
            },
        )
    )
    assert status_code == 422
    error = body["error"]
    assert isinstance(error, dict)
    assert error["code"] == error_code


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
    ended, _, _ = asyncio.run(
        post_json(
            api.application,
            f"/api/v1/development/conversation-sessions/{session_id}/end",
            {"outcome": "COMPLETED"},
        )
    )
    assert ended == 200
    payload: JsonObject = {
        "conversation_session_id": session_id,
        "customer": {
            "full_name": "Fictional HVAC Caller",
            "phone": "+12025550123",
            "address": {
                "line1": "123 Example Street",
                "city": "New York",
                "state_code": "NY",
                "postal_code": "10001",
            },
        },
        "intake_intent": "AC stopped cooling",
        "service": {
            "kind": "AC_REPAIR",
            "equipment_issue": "AC stopped cooling",
            "preferred_window": "Tomorrow morning",
            "hazardous_condition": hazardous,
        },
        "transcript": [
            {"speaker": "AGENT", "text": "Please review your fictional details."},
            {"speaker": "USER", "text": "I confirm these fictional details."},
        ],
    }
    first = asyncio.run(
        post_json(
            api.application,
            "/api/v1/development/conversation-intakes",
            payload,
            idempotency_key="browser-hvac-confirm",
        )
    )
    replay = asyncio.run(
        post_json(
            api.application,
            "/api/v1/development/conversation-intakes",
            payload,
            idempotency_key="browser-hvac-confirm",
        )
    )
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
        assert (
            session.scalar(
                select(func.count())
                .select_from(HvacServiceRequest)
                .where(HvacServiceRequest.agency_id == api.agency_id)
            )
            == 1
        )


def test_browser_voice_books_only_after_two_spoken_confirmations(
    development_conversation_api: DevelopmentConversationApi,
    migrated_database: Engine,
) -> None:
    api = development_conversation_api
    day = (datetime.now(UTC) + timedelta(days=2)).date()
    windows: list[JsonValue] = [
        {"weekday": day.weekday(), "start": "08:00", "end": "17:00"}
    ]
    configured, _, _ = asyncio.run(
        request_json(
            api.application,
            "PUT",
            "/api/v1/development/hvac/schedule",
            {
                "expected_version": 0,
                "enabled": True,
                "timezone": "America/New_York",
                "postal_codes": ["10001"],
                "windows": windows,
                "teams": [
                    {"key": "team-a", "name": "Service team", "windows": windows}
                ],
                "notice_minutes": 0,
            },
        )
    )
    assert configured == 200
    status_code, authorization, _ = authorize_session(api)
    assert status_code == 201
    session_id = authorization["session_id"]
    assert isinstance(session_id, str)
    base = f"/api/v1/development/conversation-sessions/{session_id}/booking"

    def post(
        path: str, body: JsonObject
    ) -> tuple[int, dict[str, object], dict[str, str]]:
        return asyncio.run(post_json(api.application, base + path, body))

    assert post("/availability", {"day": day.isoformat()})[0] == 409
    payload: JsonObject = {
        "conversation_session_id": session_id,
        "customer": {
            "full_name": "Fictional Browser Caller",
            "phone": "+12025550123",
            "address": {
                "line1": "123 Example Street",
                "city": "New York",
                "state_code": "NY",
                "postal_code": "10001",
            },
        },
        "intake_intent": "AC stopped cooling",
        "service": {
            "kind": "AC_REPAIR",
            "equipment_issue": "AC stopped cooling",
            "preferred_window": day.isoformat(),
            "hazardous_condition": False,
        },
        "spoken_confirmation": True,
    }
    prepared_status, prepared, _ = post(
        "/intake-readback",
        {
            "customer": payload["customer"],
            "service": payload["service"],
        },
    )
    assert prepared_status == 200
    readback = prepared["readback"]
    assert isinstance(readback, str)
    payload["transcript"] = [
        {"speaker": "AGENT", "text": readback},
        {"speaker": "USER", "text": "Yes, but change the address."},
    ]
    denied = asyncio.run(
        post_json(
            api.application,
            "/api/v1/development/conversation-intakes",
            payload,
            idempotency_key="spoken-browser-intake",
        )
    )
    assert denied[0] == 422
    with Session(migrated_database) as session:
        assert (
            session.scalar(
                select(func.count())
                .select_from(HvacServiceRequest)
                .where(HvacServiceRequest.agency_id == api.agency_id)
            )
            == 0
        )
    payload["transcript"] = [
        {"speaker": "AGENT", "text": readback},
        {"speaker": "USER", "text": "Yes, save my request."},
    ]
    saved = asyncio.run(
        post_json(
            api.application,
            "/api/v1/development/conversation-intakes",
            payload,
            idempotency_key="spoken-browser-intake",
        )
    )
    replay = asyncio.run(
        post_json(
            api.application,
            "/api/v1/development/conversation-intakes",
            payload,
            idempotency_key="spoken-browser-intake",
        )
    )
    assert saved[0] == 201
    assert replay[1] == saved[1]
    assert authorize_session(api)[0] == 409
    available_status, available, _ = post("/availability", {"day": day.isoformat()})
    assert available_status == 200
    slots = available["slots"]
    assert isinstance(slots, list) and slots
    slot = slots[0]
    reservation: JsonObject = {
        "team_key": slot["team_key"],
        "starts_at": slot["starts_at"],
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
    confirmed_status, confirmed, _ = post(
        f"/appointments/{appointment_id}/confirm", confirmation
    )
    assert confirmed_status == 200
    confirmed_appointment = confirmed["appointment"]
    assert isinstance(confirmed_appointment, dict)
    assert confirmed_appointment["status"] == "CONFIRMED"
    assert post(f"/appointments/{appointment_id}/release", {})[0] == 409
    with Session(migrated_database) as session:
        assert (
            session.scalar(
                select(func.count())
                .select_from(Appointment)
                .where(Appointment.agency_id == api.agency_id)
            )
            == 1
        )
    ended = asyncio.run(
        post_json(
            api.application,
            f"/api/v1/development/conversation-sessions/{session_id}/end",
            {"outcome": "INTERRUPTED"},
        )
    )
    assert ended[0] == 200
    assert ended[1]["status"] == "CONFIRMED"
    assert post("/availability", {"day": day.isoformat()})[0] == 409
    assert authorize_session(api)[0] == 201


def test_customer_accounts_cannot_access_another_customers_booking(
    development_conversation_api: DevelopmentConversationApi,
    migrated_database: Engine,
    database_settings: DatabaseSettings,
) -> None:
    settings = ApiSettings(
        _env_file=None,
        app_environment=RuntimeEnvironment.DEVELOPMENT,
        api_host="127.0.0.1",
        api_port=8000,
        database_url=database_settings.runtime_database_url,
        database_ssl_mode=database_settings.database_ssl_mode,
        development_actor_user_id=development_conversation_api.app_user_id,
        conversation_ai_enabled=True,
        elevenlabs_api_key="fictional-provider-key",
        elevenlabs_agent_id="agent_test",
        elevenlabs_privacy_confirmed=True,
        demo_sandbox_enabled=True,
        demo_admin_token="fictional-administrator-token-for-tests-only",
        customer_portal_enabled=True,
        customer_portal_secret="fictional-customer-portal-key-for-tests-only",
    )
    application = create_app(settings, migrated_database, FakeConversationProvider())

    async def send(
        path: str,
        body: JsonObject | None = None,
        token: str | None = None,
        method: str = "POST",
    ) -> tuple[int, dict[str, object]]:
        headers = {
            "X-Customer-Portal-Key": "fictional-customer-portal-key-for-tests-only"
        }
        if token:
            headers["Authorization"] = "Bearer " + token
        if path == "conversation-intakes":
            headers["Idempotency-Key"] = "fictional-customer-intake"
        async with AsyncClient(
            transport=ASGITransport(app=application), base_url="http://test"
        ) as client:
            response = await client.request(
                method, "/api/v1/customer/" + path, headers=headers, json=body
            )
        return response.status_code, response.json() if response.content else {}

    def signup(email: str) -> str:
        status_code, body = asyncio.run(
            send(
                "auth/signup",
                {
                    "full_name": "Fictional Customer",
                    "email": email,
                    "password": "fictional account passphrase",
                    "fictional_data_acknowledged": True,
                },
            )
        )
        assert status_code == 201
        token = body["session_token"]
        assert isinstance(token, str)
        return token

    first = signup("fictional-alpha@example.com")
    second = signup("fictional-beta@example.com")
    assert asyncio.run(send("auth/me", token=first, method="GET"))[0] == 200
    assert asyncio.run(send("auth/me", method="GET"))[0] == 401
    authorized, grant = asyncio.run(
        send(
            "conversation-sessions",
            {
                "ai_disclosure_accepted": True,
                "microphone_consent_granted": True,
                "synthetic_data_acknowledged": True,
            },
            first,
        )
    )
    assert authorized == 201
    session_id = grant["session_id"]
    assert isinstance(session_id, str)
    blocked_status, blocked = asyncio.run(
        send(
            "conversation-sessions",
            {
                "ai_disclosure_accepted": True,
                "microphone_consent_granted": True,
                "synthetic_data_acknowledged": True,
            },
            second,
        )
    )
    assert blocked_status == 409
    blocked_error = blocked["error"]
    assert isinstance(blocked_error, dict)
    blocked_details = blocked_error["details"]
    assert isinstance(blocked_details, dict)
    assert "previous_session_id" not in blocked_details
    assert (
        asyncio.run(
            send(
                f"conversation-sessions/{session_id}/end",
                {"outcome": "COMPLETED"},
                second,
            )
        )[0]
        == 404
    )
    assert (
        asyncio.run(
            send(
                f"conversation-sessions/{session_id}/end",
                {"outcome": "COMPLETED"},
                first,
            )
        )[0]
        == 200
    )
    saved_status, saved = asyncio.run(
        send(
            "conversation-intakes",
            {
                "conversation_session_id": session_id,
                "customer": {
                    "full_name": "Fictional Customer",
                    "phone": "+12025550123",
                    "address": {
                        "line1": "123 Example Street",
                        "city": "New York",
                        "state_code": "NY",
                        "postal_code": "10001",
                    },
                },
                "intake_intent": "AC is not cooling",
                "service": {
                    "kind": "AC_REPAIR",
                    "equipment_issue": "AC is not cooling",
                    "preferred_window": "Morning",
                    "hazardous_condition": False,
                },
                "transcript": [
                    {
                        "speaker": "AGENT",
                        "text": "Please review your fictional details.",
                    },
                    {"speaker": "USER", "text": "I confirm these fictional details."},
                ],
            },
            first,
        )
    )
    assert saved_status == 201
    request_id = saved["service_request_id"]
    assert isinstance(request_id, str)
    assert (
        asyncio.run(
            send(
                "hvac/reservations",
                {
                    "service_request_id": request_id,
                    "team_key": "team-a",
                    "starts_at": "2030-01-01T12:00:00Z",
                    "idempotency_key": "fictional-cross-account-booking",
                },
                second,
            )
        )[0]
        == 404
    )
    assert (
        asyncio.run(send("appointments", token=second, method="GET"))[1]["appointments"]
        == []
    )
    scheduling = SchedulingService(
        sessionmaker(
            bind=migrated_database,
            expire_on_commit=False,
            info={"integration_settings": settings},
        )
    )
    day = (datetime.now(UTC) + timedelta(days=2)).date()
    windows = [{"weekday": day.weekday(), "start": "09:00", "end": "17:00"}]
    scheduling.configure(
        development_conversation_api.agency_id,
        ScheduleInput(
            expected_version=0,
            enabled=True,
            timezone="America/New_York",
            postal_codes=["10001"],
            windows=windows,
            teams=[{"key": "team-a", "name": "Synthetic team", "windows": windows}],
            notice_minutes=0,
            cancellation_notice_minutes=0,
        ),
        uuid4(),
    )
    slot = scheduling.availability(
        development_conversation_api.agency_id,
        AvailabilityInput(postal_code="10001", day=day),
    ).slots[0]
    with Session(migrated_database) as session, session.begin():
        original_session = session.get(ConversationSession, UUID(session_id))
        original_request = session.get(HvacServiceRequest, UUID(request_id))
        assert original_session is not None and original_request is not None
        now = datetime.now(UTC)
        other_session = ConversationSession(
            agency_id=original_session.agency_id,
            initiated_by=original_session.initiated_by,
            channel="BROWSER",
            input_mode="VOICE",
            status="REVIEW_PENDING",
            disclosure_accepted_at=now,
            microphone_consent_at=now,
            synthetic_data_acknowledged_at=now,
            maximum_duration_seconds=180,
            authorization_expires_at=now + timedelta(minutes=3),
            confirmation_expires_at=now + timedelta(minutes=30),
            ended_at=now,
        )
        session.add(other_session)
        session.flush()
        other_request = HvacServiceRequest(
            agency_id=original_request.agency_id,
            conversation_session_id=other_session.id,
            customer_details=original_request.customer_details,
            service_details=original_request.service_details,
            status="OPEN",
            fingerprint="b" * 64,
            confirmed_at=now,
        )
        session.add(other_request)
        session.flush()
        other_request_id = str(other_request.id)
    held = scheduling.reserve(
        development_conversation_api.agency_id,
        ReservationInput(
            service_request_id=UUID(request_id),
            team_key=slot.team_key,
            starts_at=slot.starts_at,
            idempotency_key="fictional-owned-booking",
        ),
        uuid4(),
    )
    first_limits = asyncio.run(send("booking-limits", token=first, method="GET"))[1]
    assert first_limits["active_appointments"] == 1
    assert first_limits["appointments_remaining"] == 0
    assert first_limits["max_booking_changes"] == 1
    assert (
        asyncio.run(send("booking-limits", token=second, method="GET"))[1][
            "active_appointments"
        ]
        == 0
    )
    retry = scheduling.reserve(
        development_conversation_api.agency_id,
        ReservationInput(
            service_request_id=UUID(request_id),
            team_key=slot.team_key,
            starts_at=slot.starts_at,
            idempotency_key="fictional-owned-booking",
        ),
        uuid4(),
    )
    assert retry.id == held.id
    other_slot = scheduling.availability(
        development_conversation_api.agency_id,
        AvailabilityInput(postal_code="10001", day=day),
    ).slots[-1]
    another: JsonObject = {
        "service_request_id": other_request_id,
        "team_key": other_slot.team_key,
        "starts_at": other_slot.starts_at.isoformat(),
        "idempotency_key": "fictional-extra-booking",
    }
    limited_status, limited = asyncio.run(send("hvac/reservations", another, first))
    assert limited_status == 409
    limited_error = limited["error"]
    assert (
        isinstance(limited_error, dict)
        and limited_error["code"] == "CUSTOMER_APPOINTMENT_LIMIT_REACHED"
    )
    settings.customer_max_active_appointments = 2
    extra_status, extra = asyncio.run(send("hvac/reservations", another, first))
    assert extra_status == 200
    assert (
        asyncio.run(send(f"hvac/appointments/{extra['id']}/release", {}, first))[0]
        == 200
    )
    settings.customer_max_active_appointments = 1
    appointment = scheduling.confirm(
        development_conversation_api.agency_id, held.id, True, uuid4()
    )
    detail_path = f"appointments/{appointment.id}"
    assert asyncio.run(send(detail_path, token=second, method="GET"))[0] == 404
    detail_status, detail = asyncio.run(send(detail_path, token=first, method="GET"))
    assert detail_status == 200
    assert detail["can_reschedule"] is True
    assert "transcript" not in detail
    assert (
        asyncio.run(
            send(f"{detail_path}/availability", {"day": day.isoformat()}, second)
        )[0]
        == 404
    )
    available_status, available = asyncio.run(
        send(f"{detail_path}/availability", {"day": day.isoformat()}, first)
    )
    assert available_status == 200
    slots = available["slots"]
    assert isinstance(slots, list) and len(slots) > 1
    replacement = slots[1]
    assert isinstance(replacement, dict)
    change: JsonObject = {
        "service_request_id": request_id,
        "team_key": replacement["team_key"],
        "starts_at": replacement["starts_at"],
        "idempotency_key": "fictional-owned-reschedule",
        "explicit_confirmation": True,
    }
    assert asyncio.run(send(f"{detail_path}/reschedule", change, second))[0] == 404
    declined: JsonObject = {**change, "explicit_confirmation": False}
    assert asyncio.run(send(f"{detail_path}/reschedule", declined, first))[0] == 409
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda _: asyncio.run(send(f"{detail_path}/reschedule", change, first)),
                range(2),
            )
        )
    changed_status, changed = results[0]
    assert results[1][0] == 200 and results[1][1]["id"] == changed["id"]
    assert changed_status == 200 and changed["status"] == "CONFIRMED"
    assert changed["id"] != str(appointment.id)
    assert (
        asyncio.run(send(f"{detail_path}/reschedule", change, first))[1]["id"]
        == changed["id"]
    )
    old_status, old = asyncio.run(send(detail_path, token=first, method="GET"))
    assert old_status == 200
    old_appointment = old["appointment"]
    assert (
        isinstance(old_appointment, dict) and old_appointment["status"] == "CANCELLED"
    )
    next_path = f"appointments/{changed['id']}"
    _, next_details = asyncio.run(send(next_path, token=first, method="GET"))
    assert next_details["change_allowance"] == {"maximum": 1, "used": 1, "remaining": 0}
    assert next_details["can_reschedule"] is False
    next_change: JsonObject = {
        **change,
        "idempotency_key": "fictional-another-change",
        "starts_at": slot.starts_at.isoformat(),
    }
    exhausted_status, exhausted = asyncio.run(
        send(f"{next_path}/reschedule", next_change, first)
    )
    assert exhausted_status == 409
    exhausted_error = exhausted["error"]
    assert (
        isinstance(exhausted_error, dict)
        and exhausted_error["code"] == "CUSTOMER_BOOKING_CHANGE_LIMIT_REACHED"
    )
    settings.customer_max_booking_changes = 2
    assert (
        asyncio.run(send(next_path, token=first, method="GET"))[1]["can_reschedule"]
        is True
    )
    increased_status, increased = asyncio.run(
        send(f"{next_path}/reschedule", next_change, first)
    )
    assert increased_status == 200 and increased["status"] == "CONFIRMED"
    settings.customer_max_booking_changes = 1
    _, increased_details = asyncio.run(
        send(f"appointments/{increased['id']}", token=first, method="GET")
    )
    assert increased_details["change_allowance"] == {
        "maximum": 1,
        "used": 2,
        "remaining": 0,
    }
    with Session(migrated_database) as session, session.begin():
        session.execute(
            update(Appointment)
            .where(Appointment.id == UUID(str(increased["id"])))
            .values(
                starts_at=datetime.now(UTC) - timedelta(hours=2),
                ends_at=datetime.now(UTC) - timedelta(hours=1),
            )
        )
    assert (
        asyncio.run(send("booking-limits", token=first, method="GET"))[1][
            "appointments_remaining"
        ]
        == 1
    )
    assert (
        asyncio.run(
            send(
                "hvac/reservations",
                {**another, "idempotency_key": "fictional-next-booking"},
                first,
            )
        )[0]
        == 200
    )
    assert asyncio.run(send("auth/logout", {}, first))[0] == 204
    assert asyncio.run(send("auth/me", token=first, method="GET"))[0] == 401
    assert (
        asyncio.run(
            send(
                "auth/login",
                {
                    "email": "fictional-alpha@example.com",
                    "password": "wrong fictional password",
                },
            )
        )[0]
        == 401
    )
    assert (
        asyncio.run(
            send(
                "auth/login",
                {
                    "email": "fictional-alpha@example.com",
                    "password": "fictional account passphrase",
                },
            )
        )[0]
        == 200
    )
