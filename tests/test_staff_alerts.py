import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock
from uuid import uuid4

import httpx
import pytest
from pydantic import ValidationError
from fastapi import FastAPI

from insurance_operations.database.models.lead import LeadHandoffRequest
from insurance_operations.database.models.staff_alert import StaffAlert, StaffAlertPolicy
from insurance_operations.notifications.staff_alerts import StaffAlertPolicyInput, ready_for_staff_delivery, send_staff_email
from insurance_operations.settings import DatabaseSettings
from insurance_operations.settings import ApiSettings
from insurance_operations.actors import ActorContext
from insurance_operations.notifications.staff_routes import create_staff_alert_router


@pytest.fixture(autouse=True)
def isolated_staff_email_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    for field in DatabaseSettings.model_fields:
        monkeypatch.delenv(field.upper(), raising=False)


def alert() -> StaffAlert:
    now = datetime.now(UTC)
    return StaffAlert(
        id=uuid4(), agency_id=uuid4(), event_type="HANDOFF", source_id=uuid4(),
        recipient="staff@example.com", policy_version=1,
        payload={"from": "alerts@example.com", "to": ["staff@example.com"], "subject": "Staff follow-up", "text": "Protected request reference"},
        status="PENDING", created_at=now, due_at=now, attempts=0,
    )


def test_staff_policy_requires_valid_distinct_recipients() -> None:
    for recipients in ([], ["invalid"], ["staff@example.com", "STAFF@example.com"]):
        with pytest.raises(ValidationError):
            StaffAlertPolicyInput(enabled=True, recipients=recipients, expected_row_version=0)
    assert StaffAlertPolicyInput(enabled=False, recipients=[], expected_row_version=0).enabled is False


@pytest.mark.parametrize("status,expected", [(202, "ACCEPTED"), (429, "PENDING"), (503, "PENDING"), (403, "FAILED")])
def test_resend_staff_delivery_uses_stable_key_and_frozen_payload(status: int, expected: str) -> None:
    row = alert()
    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(status, json={"id": "fictional-email-reference"})

    settings = DatabaseSettings(_env_file=None, app_environment="development", database_url="postgresql://synthetic:synthetic@localhost/dev", resend_api_key="synthetic-key")
    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        assert send_staff_email(client, settings, row)[0] == expected
        assert send_staff_email(client, settings, row)[0] == expected
    assert requests[0].headers["Idempotency-Key"] == requests[1].headers["Idempotency-Key"]
    assert requests[0].content == requests[1].content
    assert requests[0].url == "https://api.resend.com/emails"


def test_uncertain_staff_delivery_preserves_pending_for_same_key_retry() -> None:
    row = alert()
    settings = DatabaseSettings(_env_file=None, app_environment="development", database_url="postgresql://synthetic:synthetic@localhost/dev", resend_api_key="synthetic-key")

    def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("fictional timeout", request=request)

    with httpx.Client(transport=httpx.MockTransport(timeout)) as client:
        assert send_staff_email(client, settings, row) == ("PENDING", "EMAIL_RESPONSE_UNKNOWN")


def test_policy_changes_and_expired_retry_windows_never_create_a_fresh_send() -> None:
    session = MagicMock()
    row = alert()
    policy = StaffAlertPolicy(agency_id=row.agency_id, enabled=False, recipients=[], row_version=2)
    assert ready_for_staff_delivery(session, row, policy, datetime.now(UTC)) is False
    assert row.status == "SKIPPED"
    row.first_attempt_at = datetime.now(UTC) - timedelta(minutes=1)
    row.status = "PENDING"
    assert ready_for_staff_delivery(session, row, policy, datetime.now(UTC)) is False
    assert row.status == "UNKNOWN"
    policy.enabled, policy.row_version = True, 1
    row.first_attempt_at = datetime.now(UTC) - timedelta(hours=23)
    row.status = "PENDING"
    assert ready_for_staff_delivery(session, row, policy, datetime.now(UTC)) is False
    assert row.status == "UNKNOWN"
    assert row.last_error == "PROVIDER_RETRY_WINDOW_ENDED"


def test_closed_or_foreign_sources_are_suppressed_before_contact() -> None:
    for source in (
        LeadHandoffRequest(agency_id=uuid4(), status="REQUESTED"),
        LeadHandoffRequest(agency_id=uuid4(), status="COMPLETED"),
        None,
    ):
        row = alert()
        policy = StaffAlertPolicy(agency_id=row.agency_id, enabled=True, recipients=[row.recipient], row_version=1)
        session = MagicMock()
        session.scalar.side_effect = [None, source]
        assert ready_for_staff_delivery(session, row, policy, datetime.now(UTC)) is False
        assert row.status == "SKIPPED"


def test_bounced_staff_recipient_is_suppressed_for_future_alerts() -> None:
    row = alert()
    policy = StaffAlertPolicy(agency_id=row.agency_id, enabled=True, recipients=[row.recipient], row_version=1)
    session = MagicMock()
    session.scalar.return_value = uuid4()
    assert ready_for_staff_delivery(session, row, policy, datetime.now(UTC)) is False
    assert row.last_error == "STAFF_EMAIL_SUPPRESSED"
    assert row.status == "SKIPPED"


def test_staff_alert_flag_validates_email_configuration_independently() -> None:
    with pytest.raises(ValidationError, match="RESEND_API_KEY"):
        DatabaseSettings(_env_file=None, app_environment="development", database_url="postgresql://synthetic:synthetic@localhost/dev", staff_alert_email_enabled=True)


def test_staff_settings_reject_missing_or_incorrect_admin_token_before_reading_records() -> None:
    actor = ActorContext(app_user_id=uuid4(), display_name="Fictional operator", agency_id=uuid4(), agency_name="Fictional business", agency_environment="DEVELOPMENT")
    settings = ApiSettings(_env_file=None, app_environment="development", database_url="postgresql://synthetic:synthetic@localhost/dev", demo_admin_token="fictional-admin-secret-at-least-32-characters")
    sessions = MagicMock()
    app = FastAPI()
    app.include_router(create_staff_alert_router(settings, sessions, lambda: actor))

    async def denied() -> None:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://example.com") as client:
            for headers in ({}, {"X-Demo-Admin-Token": "incorrect"}):
                response = await client.get("/api/v1/development/staff-alerts", headers=headers)
                assert response.status_code == 401

    asyncio.run(denied())
    sessions.assert_not_called()
