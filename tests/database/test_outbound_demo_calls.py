from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import Any
from uuid import UUID, uuid4

import pytest
from pydantic import SecretStr
from sqlalchemy import delete, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.database.models.identity import (
    Agency,
    AgencyMembership,
    AppUser,
)
from insurance_operations.database.models.outbound_demo import OutboundDemoCall
from insurance_operations.errors import ApiError
from insurance_operations.settings import ApiSettings
from insurance_operations.telephony.outbound.provider import (
    ElevenLabsOutboundProvider,
    OutboundCallReceipt,
    OutboundProviderError,
)
from insurance_operations.telephony.outbound.schemas import (
    DemoCallInput,
    DemoCallStatus,
)
from insurance_operations.telephony.outbound.service import OutboundDemoService
from insurance_operations.telephony.outbound.settings import OutboundDemoSettings

NUMBER = "+15559990002"
HUMAN = "+15559990003"
OWNER = "synthetic-visitor"


class FakeProvider(ElevenLabsOutboundProvider):
    def __init__(self, settings: OutboundDemoSettings) -> None:
        super().__init__(settings)
        self.dial_count = 0
        self.lock = Lock()
        self.unknown = False
        self.fail_preflight = False

    def preflight(self) -> None:
        if self.fail_preflight:
            raise OutboundProviderError(outcome_unknown=False)

    def dial(self, data: DemoCallInput, call_id: str) -> OutboundCallReceipt:
        with self.lock:
            self.dial_count += 1
        if self.unknown:
            raise OutboundProviderError(outcome_unknown=True)
        return OutboundCallReceipt(f"conv-{call_id}", f"sip-{call_id}")


@dataclass
class Context:
    service: OutboundDemoService
    provider: FakeProvider
    sessions: sessionmaker[Session]
    agency_id: UUID


@pytest.fixture
def context(
    migrated_database: Engine, monkeypatch: pytest.MonkeyPatch
) -> Iterator[Context]:
    for field in OutboundDemoSettings.model_fields:
        monkeypatch.delenv(field.upper(), raising=False)
    sessions = sessionmaker(bind=migrated_database, expire_on_commit=False)
    with sessions() as session, session.begin():
        agency = Agency(
            name="Synthetic outbound HVAC",
            slug=f"outbound-{uuid4()}",
            environment_kind="DEVELOPMENT",
        )
        user = AppUser(auth_subject=uuid4(), display_name="Synthetic demo operator")
        session.add_all([agency, user])
        session.flush()
        session.add(AgencyMembership(agency_id=agency.id, app_user_id=user.id))
    api = ApiSettings(
        _env_file=None,
        app_environment="development",
        api_host="localhost",
        api_port=8000,
        database_url="postgresql://synthetic:synthetic@localhost/synthetic",
        development_actor_user_id=user.id,
        conversation_ai_enabled=False,
        demo_sandbox_enabled=False,
        customer_portal_enabled=False,
        google_calendar_enabled=False,
        booking_email_enabled=False,
    )
    settings = OutboundDemoSettings(
        _env_file=None,
        app_environment="development",
        outbound_demo_enabled=True,
        outbound_demo_agent_id="synthetic-outbound-agent",
        outbound_demo_phone_number_id="synthetic-number-id",
        outbound_demo_allowed_numbers=NUMBER,
        outbound_demo_human_number=HUMAN,
        outbound_demo_secret="synthetic-secret-for-outbound-at-least-32-characters",
        outbound_demo_webhook_secret="synthetic-webhook-for-outbound-at-least-32-characters",
        elevenlabs_api_key="synthetic-api-key",
    )
    provider = FakeProvider(settings)
    try:
        yield Context(
            OutboundDemoService(sessions, api, settings, provider),
            provider,
            sessions,
            agency.id,
        )
    finally:
        # Only this fixture's synthetic call rows; the migration retains real evidence.
        with sessions() as session, session.begin():
            session.execute(
                delete(OutboundDemoCall).where(OutboundDemoCall.agency_id == agency.id)
            )


def data(**overrides: Any) -> DemoCallInput:
    return DemoCallInput(
        **{
            "request_id": uuid4(),
            "phone_number": NUMBER,
            "scenario": "cooling",
            "consent": True,
            "consent_version": "outbound-demo-v1",
            **overrides,
        }
    )


def final_event(call_id: UUID, **overrides: Any) -> dict[str, Any]:
    return {
        "type": "post_call_transcription",
        "data": {
            "agent_id": "synthetic-outbound-agent",
            "conversation_id": f"conv-{call_id}",
            "status": "done",
            "metadata": {"call_duration_secs": 20},
            "transcript": [],
            **overrides,
        },
    }


def test_parallel_duplicate_requests_dial_once(context: Context) -> None:
    request = data()
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(lambda _: context.service.create(request, OWNER), range(2))
        )
    assert results[0].id == results[1].id
    assert context.provider.dial_count == 1
    with context.sessions() as session:
        row = session.get(OutboundDemoCall, results[0].id)
        assert row is not None
        assert row.destination_hash != NUMBER
        assert row.consent_version == "outbound-demo-v1"
        assert row.consent_at is not None


def test_conflicting_idempotency_keys_and_visitor_access_are_rejected(
    context: Context,
) -> None:
    request = data()
    result = context.service.create(request, OWNER)
    with pytest.raises(ApiError) as conflict:
        context.service.create(
            data(request_id=request.request_id, scenario="heating"), OWNER
        )
    assert conflict.value.status_code == 409
    with pytest.raises(ApiError) as ownership:
        context.service.get(result.id, "other-visitor")
    assert ownership.value.status_code == 404
    with pytest.raises(ApiError):
        context.service.get_request(request.request_id, "other-visitor")
    assert context.provider.dial_count == 1


def test_non_allowlisted_number_never_reaches_provider(context: Context) -> None:
    with pytest.raises(ApiError) as caught:
        context.service.create(data(phone_number="+15559990004"), OWNER)
    assert caught.value.status_code == 403
    assert context.provider.dial_count == 0


def test_distinct_parallel_requests_share_one_active_slot(context: Context) -> None:
    def attempt(_: int) -> str:
        try:
            return context.service.create(data(), OWNER).status.value
        except ApiError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(attempt, range(2)))
    assert sorted(outcomes) == ["DEMO_CALL_LIMIT", "dialing"]
    assert context.provider.dial_count == 1


def test_unknown_outcome_is_replayed_and_blocks_new_dial(context: Context) -> None:
    context.provider.unknown = True
    request = data()
    result = context.service.create(request, OWNER)
    assert result.status is DemoCallStatus.UNKNOWN
    assert context.service.create(request, OWNER).id == result.id
    with pytest.raises(ApiError) as caught:
        context.service.create(data(), OWNER)
    assert caught.value.status_code == 429
    assert context.provider.dial_count == 1


def test_preflight_failure_never_dials(context: Context) -> None:
    context.provider.fail_preflight = True
    result = context.service.create(data(), OWNER)
    assert result.status is DemoCallStatus.FAILED
    assert context.provider.dial_count == 0


@pytest.mark.parametrize(
    "code,status",
    [
        (486, "rejected"),
        (603, "rejected"),
        (408, "unanswered"),
        (480, "unanswered"),
        (503, "failed"),
    ],
)
def test_failure_events_and_late_replay_cannot_revive_call(
    context: Context, code: int, status: str
) -> None:
    result = context.service.create(data(), OWNER)
    event = {
        "type": "call_initiation_failure",
        "data": {
            "agent_id": "synthetic-outbound-agent",
            "conversation_id": f"conv-{result.id}",
            "metadata": {"type": "sip", "body": {"sip_status_code": code}},
        },
    }
    context.service.webhook(event)
    context.service.webhook(event)
    context.service.webhook(final_event(result.id))
    assert context.service.get(result.id, OWNER).status == status
    assert context.provider.dial_count == 1


@pytest.mark.parametrize(
    "metadata,status",
    [
        ({"call_duration_secs": 20}, "completed"),
        (
            {"call_duration_secs": 20, "termination_reason": "Client disconnected"},
            "disconnected",
        ),
        ({"call_duration_secs": 20, "error": {"code": 1}}, "disconnected"),
    ],
)
def test_terminal_lifecycle(
    context: Context, metadata: dict[str, Any], status: str
) -> None:
    result = context.service.create(data(), OWNER)
    context.service.webhook(final_event(result.id, metadata=metadata))
    response = context.service.get(result.id, OWNER)
    assert response.status == status
    assert response.terminal is True


def test_sip_transfer_keeps_slot_until_carrier_end_confirmation(
    context: Context,
) -> None:
    result = context.service.create(data(), OWNER)
    context.service.webhook(
        final_event(
            result.id,
            transcript=[
                {
                    "tool_results": [
                        {
                            "tool_name": "transfer_to_number",
                            "result": {
                                "result_type": "transfer_to_number_sip_success",
                                "transfer_number": HUMAN,
                            },
                        }
                    ]
                }
            ],
        )
    )
    response = context.service.get(result.id, OWNER)
    assert response.transfer_status == "refer_accepted"
    assert response.status is DemoCallStatus.UNKNOWN
    assert "human answer is unconfirmed" in response.message
    context.service.webhook(final_event(result.id))
    assert context.service.get(result.id, OWNER).transfer_status == "refer_accepted"
    assert context.service.get(result.id, OWNER).status is DemoCallStatus.UNKNOWN
    context.service.webhook(
        {
            "type": "call_initiation_failure",
            "data": {
                "agent_id": "synthetic-outbound-agent",
                "conversation_id": f"conv-{result.id}",
                "metadata": {"type": "sip", "body": {"sip_status_code": 503}},
            },
        }
    )
    assert context.service.get(result.id, OWNER).status is DemoCallStatus.UNKNOWN
    assert context.service.carrier_ended(result.id).terminal is True


@pytest.mark.parametrize("outcome_unknown", [False, True])
def test_dial_error_does_not_erase_early_transfer_evidence(
    context: Context, monkeypatch: pytest.MonkeyPatch, outcome_unknown: bool
) -> None:
    def dial(data: DemoCallInput, call_id: str) -> OutboundCallReceipt:
        context.provider.dial_count += 1
        context.service.webhook(
            final_event(
                UUID(call_id),
                conversation_initiation_client_data={
                    "dynamic_variables": {"outbound_demo_call_id": call_id}
                },
                transcript=[{"tool_calls": [{"tool_name": "transfer_to_number"}]}],
            )
        )
        raise OutboundProviderError(outcome_unknown=outcome_unknown)

    monkeypatch.setattr(context.provider, "dial", dial)
    response = context.service.create(data(), OWNER)
    assert response.status is DemoCallStatus.UNKNOWN
    assert response.transfer_status == "unconfirmed"
    with pytest.raises(ApiError) as caught:
        context.service.create(data(), OWNER)
    assert caught.value.code == "DEMO_CALL_LIMIT"
    assert context.provider.dial_count == 1


def test_malformed_webhook_does_not_release_active_slot(context: Context) -> None:
    result = context.service.create(data(), OWNER)
    with pytest.raises(ApiError) as caught:
        context.service.webhook(
            final_event(result.id, transcript=[{"tool_results": True}])
        )
    assert caught.value.status_code == 422
    assert context.service.get(result.id, OWNER).status is DemoCallStatus.DIALING


def test_number_limit_survives_cookies_terminal_calls_and_new_keys(
    context: Context,
) -> None:
    result = context.service.create(data(), OWNER)
    context.service.webhook(final_event(result.id))
    with context.sessions() as session, session.begin():
        row = session.get(OutboundDemoCall, result.id)
        assert row is not None
        row.created_at = datetime.now(UTC) - timedelta(minutes=10)
    with pytest.raises(ApiError) as caught:
        context.service.create(data(), "fresh-cookie")
    assert caught.value.status_code == 429
    assert context.provider.dial_count == 1


def test_daily_budget_counts_failed_calls_across_destinations(context: Context) -> None:
    other_number = "+15559990004"
    context.service.settings.outbound_demo_allowed_numbers = SecretStr(
        f"{NUMBER},{other_number}"
    )
    context.service.settings.outbound_demo_daily_limit = 1
    context.provider.fail_preflight = True
    result = context.service.create(data(), OWNER)
    with context.sessions() as session, session.begin():
        row = session.get(OutboundDemoCall, result.id)
        assert row is not None
        row.created_at = datetime.now(UTC) - timedelta(minutes=10)
    with pytest.raises(ApiError) as caught:
        context.service.create(data(phone_number=other_number), "fresh-cookie")
    assert caught.value.status_code == 429
    assert context.provider.dial_count == 0


def test_webhook_before_http_receipt_can_bind_reserved_call(context: Context) -> None:
    call_id, _ = context.service._reserve(data(), OWNER)
    event = final_event(
        call_id,
        conversation_initiation_client_data={
            "dynamic_variables": {"outbound_demo_call_id": str(call_id)}
        },
    )
    context.service.webhook(event)
    assert context.service.get(call_id, OWNER).status is DemoCallStatus.COMPLETED


def test_unbound_failure_is_retryable_and_never_guesses_a_destination(
    context: Context,
) -> None:
    with pytest.raises(ApiError) as caught:
        context.service.webhook(
            {
                "type": "call_initiation_failure",
                "data": {
                    "agent_id": "synthetic-outbound-agent",
                    "conversation_id": "unknown-conversation",
                },
            }
        )
    assert caught.value.status_code == 503
    with context.sessions() as session:
        assert (
            session.scalar(
                select(OutboundDemoCall).where(
                    OutboundDemoCall.agency_id == context.agency_id
                )
            )
            is None
        )
