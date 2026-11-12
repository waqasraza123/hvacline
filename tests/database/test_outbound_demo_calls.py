import asyncio
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import Any
from unittest.mock import Mock
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi import FastAPI
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
from insurance_operations.database.models.outbound_verification import (
    OutboundPhoneVerification,
)
from insurance_operations.errors import ApiError, api_error_handler
from insurance_operations.settings import ApiSettings
from insurance_operations.telephony.outbound.provider import (
    ElevenLabsOutboundProvider,
    OutboundCallReceipt,
    OutboundProviderError,
)
from insurance_operations.telephony.outbound.routes import create_outbound_demo_router
from insurance_operations.telephony.outbound.schemas import (
    DemoCallInput,
    DemoCallResponse,
    DemoCallStatus,
)
from insurance_operations.telephony.outbound.service import OutboundDemoService
from insurance_operations.telephony.outbound.settings import OutboundDemoSettings
from insurance_operations.telephony.outbound.sms_provider import (
    TelnyxVerificationProvider,
    sms_unavailable,
)
from insurance_operations.telephony.outbound.verification_schemas import (
    SmsStartInput,
    SmsVerifyInput,
)

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
        self.last_destination: str | None = None

    def preflight(self, phone_number: str) -> None:
        if self.fail_preflight:
            raise OutboundProviderError(outcome_unknown=False)

    def dial(self, data: DemoCallInput, call_id: str) -> OutboundCallReceipt:
        with self.lock:
            self.dial_count += 1
            self.last_destination = data.phone_number
        if self.unknown:
            raise OutboundProviderError(outcome_unknown=True)
        return OutboundCallReceipt(f"conv-{call_id}", f"sip-{call_id}")


@dataclass
class Context:
    service: OutboundDemoService
    provider: FakeProvider
    sessions: sessionmaker[Session]
    agency_id: UUID

    def verified_input(self, request: DemoCallInput, owner: str) -> DemoCallInput:
        if owner == "admin" or request.phone_verification_id is not None:
            return request
        now = datetime.now(UTC)
        with self.sessions() as session, session.begin():
            proof = OutboundPhoneVerification(
                agency_id=self.agency_id,
                owner_hash=self.service._hash("owner", owner),
                destination_hash=self.service._hash(
                    "destination", request.phone_number
                ),
                consent_version="outbound-sms-v1",
                created_at=now,
                expires_at=now + timedelta(minutes=5),
                attempts=1,
                verified_at=now,
                provider_verification_id=f"synthetic-verification-{uuid4()}",
            )
            session.add(proof)
            session.flush()
        return request.model_copy(update={"phone_verification_id": proof.id})

    def create_verified(self, request: DemoCallInput, owner: str) -> DemoCallResponse:
        return self.service.create(self.verified_input(request, owner), owner)


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
        outbound_demo_website_enabled=True,
        outbound_demo_live_verified=True,
        outbound_demo_agent_id="synthetic-outbound-agent",
        outbound_demo_phone_number_id="synthetic-number-id",
        outbound_demo_allowed_numbers=NUMBER,
        outbound_demo_human_number=HUMAN,
        outbound_demo_secret="synthetic-secret-for-outbound-at-least-32-characters",
        outbound_demo_webhook_secret="synthetic-webhook-for-outbound-at-least-32-characters",
        elevenlabs_api_key="synthetic-api-key",
        telnyx_verify_api_key="synthetic-telnyx-verify-key",
        telnyx_verify_profile_id=uuid4(),
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
            session.execute(
                delete(OutboundPhoneVerification).where(
                    OutboundPhoneVerification.agency_id == agency.id
                )
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


@pytest.fixture
def us_context(context: Context) -> Context:
    config = OutboundDemoSettings(
        _env_file=None,
        **{
            **context.service.settings.model_dump(),
            "outbound_demo_number_policy": "consented_us",
            "outbound_demo_allowed_numbers": "",
        },
    )
    context.service.settings = config
    context.service.verification.settings = config
    context.provider.settings = config
    return context


@pytest.fixture
def sms_provider(us_context: Context) -> Mock:
    provider = Mock(spec=TelnyxVerificationProvider)
    provider.send.side_effect = lambda _: str(uuid4())
    provider.verify.return_value = "+12025550123"
    us_context.service.verification.provider = provider
    return provider


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
            executor.map(lambda _: context.create_verified(request, OWNER), range(2))
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
    result = context.create_verified(request, OWNER)
    with pytest.raises(ApiError) as conflict:
        context.create_verified(
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
        context.create_verified(data(phone_number="+15559990004"), OWNER)
    assert caught.value.status_code == 403
    assert context.provider.dial_count == 0


def test_allowlist_still_accepts_only_the_configured_international_number(
    context: Context,
) -> None:
    context.service.settings.outbound_demo_allowed_numbers = SecretStr("+442079460123")
    result = context.create_verified(data(phone_number="+44 20 7946 0123"), OWNER)
    assert result.status is DemoCallStatus.DIALING
    assert context.provider.last_destination == "+442079460123"
    with pytest.raises(ApiError) as caught:
        context.create_verified(data(phone_number="+12025550123"), OWNER)
    assert caught.value.code == "DEMO_NUMBER_NOT_AUTHORIZED"
    assert context.provider.dial_count == 1


@pytest.mark.parametrize("owner", ["admin", OWNER])
def test_consented_us_normalizes_and_replays_without_allowlisting(
    us_context: Context, owner: str
) -> None:
    request = data(phone_number="(202) 555-0123")
    result = us_context.create_verified(request, owner)
    retry = data(request_id=request.request_id, phone_number="+1 202 555 0123")
    assert us_context.create_verified(retry, owner).id == result.id
    with pytest.raises(ApiError) as caught:
        us_context.create_verified(
            data(request_id=request.request_id, phone_number="+12125550123"), owner
        )
    assert caught.value.code == "DEMO_REQUEST_CONFLICT"
    assert us_context.provider.dial_count == 1
    assert us_context.provider.last_destination == "+12025550123"
    with us_context.sessions() as session:
        row = session.get(OutboundDemoCall, result.id)
        assert row is not None
        assert row.consent_version == "outbound-demo-v1"
        assert row.consent_at is not None
        assert row.destination_hash != request.phone_number
        assert row.owner_hash == us_context.service._hash("owner", owner)


@pytest.mark.parametrize("owner", ["admin", OWNER])
def test_consented_us_formatting_cannot_bypass_number_quota(
    us_context: Context, owner: str
) -> None:
    result = us_context.create_verified(data(phone_number="202-555-0123"), owner)
    us_context.service.webhook(final_event(result.id))
    with us_context.sessions() as session, session.begin():
        row = session.get(OutboundDemoCall, result.id)
        assert row is not None
        row.created_at = datetime.now(UTC) - timedelta(minutes=10)
    with pytest.raises(ApiError) as caught:
        us_context.create_verified(data(phone_number="+1 (202) 555-0123"), owner)
    assert caught.value.code == "DEMO_CALL_LIMIT"
    assert us_context.provider.dial_count == 1


@pytest.mark.parametrize("owner", ["admin", OWNER])
def test_consented_us_unknown_outcome_blocks_all_destinations(
    us_context: Context, owner: str
) -> None:
    us_context.provider.unknown = True
    request = data(phone_number="+12025550123")
    result = us_context.create_verified(request, owner)
    assert result.status is DemoCallStatus.UNKNOWN
    assert us_context.create_verified(request, owner).id == result.id
    with pytest.raises(ApiError) as caught:
        us_context.create_verified(data(phone_number="+12125550123"), owner)
    assert caught.value.code == "DEMO_CALL_LIMIT"
    assert us_context.provider.dial_count == 1


def test_public_us_callback_route_dials_once_and_isolates_status(
    us_context: Context,
) -> None:
    config = us_context.service.settings
    api = us_context.service.api.model_copy(
        update={
            "demo_admin_token": SecretStr(
                "synthetic-admin-token-at-least-32-characters"
            )
        }
    )
    application = FastAPI()
    application.add_exception_handler(ApiError, api_error_handler)  # type: ignore[arg-type]
    application.include_router(
        create_outbound_demo_router(
            api, us_context.sessions, config, us_context.provider
        )
    )
    request = us_context.verified_input(data(phone_number="+12025550123"), "a" * 43)
    payload = {
        **request.model_dump(mode="json"),
        "phone_verification_id": str(request.phone_verification_id),
    }
    assert config.outbound_demo_secret is not None
    headers = {
        "X-Outbound-Demo-Key": config.outbound_demo_secret.get_secret_value(),
        "X-Outbound-Visitor": "a" * 43,
    }

    async def submit() -> None:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=application),
            base_url="http://test",
            headers=headers,
        ) as client:
            response = await client.post("/api/v1/outbound-demo/calls", json=payload)
            assert response.status_code == 200
            assert response.json()["status"] == "dialing"
            replay = await client.post("/api/v1/outbound-demo/calls", json=payload)
            assert replay.json()["id"] == response.json()["id"]
            path = f"/api/v1/outbound-demo/requests/{request.request_id}"
            assert (await client.get(path)).status_code == 200
            foreign = await client.get(path, headers={"X-Outbound-Visitor": "b" * 43})
            assert foreign.status_code == 404

    asyncio.run(submit())
    assert us_context.provider.dial_count == 1
    assert not config.outbound_demo_transfer_enabled


def test_consented_us_daily_budget_includes_failed_preflight(
    us_context: Context,
) -> None:
    us_context.service.settings.outbound_demo_daily_limit = 1
    us_context.provider.fail_preflight = True
    result = us_context.create_verified(data(phone_number="+12025550123"), "admin")
    assert result.status is DemoCallStatus.FAILED
    with us_context.sessions() as session, session.begin():
        row = session.get(OutboundDemoCall, result.id)
        assert row is not None
        row.created_at = datetime.now(UTC) - timedelta(minutes=10)
    with pytest.raises(ApiError) as caught:
        us_context.create_verified(data(phone_number="+12125550123"), "admin")
    assert caught.value.code == "DEMO_CALL_LIMIT"
    assert us_context.provider.dial_count == 0


def test_consented_us_parallel_requests_share_one_slot(us_context: Context) -> None:
    def attempt(number: str) -> str:
        try:
            result = us_context.create_verified(data(phone_number=number), "admin")
            return result.status.value
        except ApiError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(attempt, ["+12025550123", "+12125550123"]))
    assert sorted(outcomes) == ["DEMO_CALL_LIMIT", "dialing"]
    assert us_context.provider.dial_count == 1


def test_distinct_parallel_requests_share_one_active_slot(context: Context) -> None:
    def attempt(_: int) -> str:
        try:
            return context.create_verified(data(), OWNER).status.value
        except ApiError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(attempt, range(2)))
    assert sorted(outcomes) == ["DEMO_CALL_LIMIT", "dialing"]
    assert context.provider.dial_count == 1


def test_unknown_outcome_is_replayed_and_blocks_new_dial(context: Context) -> None:
    context.provider.unknown = True
    request = data()
    result = context.create_verified(request, OWNER)
    assert result.status is DemoCallStatus.UNKNOWN
    assert context.create_verified(request, OWNER).id == result.id
    with pytest.raises(ApiError) as caught:
        context.create_verified(data(), OWNER)
    assert caught.value.status_code == 429
    assert context.provider.dial_count == 1


def test_preflight_failure_never_dials(context: Context) -> None:
    context.provider.fail_preflight = True
    result = context.create_verified(data(), OWNER)
    assert result.status is DemoCallStatus.FAILED
    assert context.provider.dial_count == 0


def test_account_call_limit_survives_changing_destination(us_context: Context) -> None:
    result = us_context.create_verified(data(phone_number="+12025550123"), OWNER)
    us_context.service.webhook(final_event(result.id))
    with us_context.sessions() as session, session.begin():
        row = session.get(OutboundDemoCall, result.id)
        assert row is not None
        row.created_at = datetime.now(UTC) - timedelta(minutes=10)
    with pytest.raises(ApiError) as caught:
        us_context.create_verified(data(phone_number="+12125550123"), OWNER)
    assert caught.value.code == "DEMO_CALL_LIMIT"
    assert us_context.provider.dial_count == 1
    other = us_context.create_verified(
        data(phone_number="+12125550123"), "other-account"
    )
    assert other.status == DemoCallStatus.DIALING


def test_sms_verification_grants_one_account_and_destination_bound_call(
    us_context: Context,
    sms_provider: Mock,
) -> None:
    verification = us_context.service.verification
    challenge = verification.start(
        SmsStartInput(
            phone_number="+12025550123",
            sms_consent=True,
            sms_consent_version="outbound-sms-v1",
        ),
        OWNER,
    )
    verify = SmsVerifyInput(challenge_id=challenge.challenge_id, code="123456")
    with pytest.raises(ApiError):
        verification.verify(verify, "other-account")
    sms_provider.verify.assert_not_called()
    assert verification.verify(verify, OWNER).verified
    request = data(
        phone_number="+12025550123", phone_verification_id=challenge.challenge_id
    )
    for changes, owner in [
        ({"phone_number": "+12125550123"}, OWNER),
        ({}, "other-account"),
    ]:
        with pytest.raises(ApiError) as caught:
            us_context.service.create(request.model_copy(update=changes), owner)
        assert caught.value.code == "DEMO_PHONE_VERIFICATION_REQUIRED"
    result = us_context.service.create(request, OWNER)
    assert us_context.service.create(request, OWNER).id == result.id
    assert us_context.provider.dial_count == 1
    with us_context.sessions() as session:
        row = session.get(OutboundPhoneVerification, challenge.challenge_id)
        assert row is not None
        assert row.consumed_by_request_id == request.request_id
        assert row.destination_hash != request.phone_number
        assert row.consent_version == "outbound-sms-v1"


@pytest.mark.parametrize("problem", ["missing", "unverified", "expired", "consumed"])
def test_website_cannot_dial_without_fresh_phone_proof(
    us_context: Context,
    problem: str,
) -> None:
    request = data(phone_number="+12025550123")
    if problem != "missing":
        request = us_context.verified_input(request, OWNER)
        with us_context.sessions() as session, session.begin():
            row = session.get(OutboundPhoneVerification, request.phone_verification_id)
            assert row is not None
            if problem == "unverified":
                row.verified_at = None
            elif problem == "expired":
                row.expires_at = datetime.now(UTC) - timedelta(seconds=1)
            else:
                row.consumed_by_request_id = uuid4()
    with pytest.raises(ApiError) as caught:
        us_context.service.create(request, OWNER)
    assert caught.value.code == "DEMO_PHONE_VERIFICATION_REQUIRED"
    assert us_context.provider.dial_count == 0


def test_sms_wrong_codes_and_provider_errors_consume_attempts(
    us_context: Context,
    sms_provider: Mock,
) -> None:
    verification = us_context.service.verification
    challenge = verification.start(
        SmsStartInput(
            phone_number="+12025550123",
            sms_consent=True,
            sms_consent_version="outbound-sms-v1",
        ),
        OWNER,
    )
    sms_provider.verify.side_effect = [sms_unavailable(), None, None, None, None]
    request = SmsVerifyInput(challenge_id=challenge.challenge_id, code="000000")
    for _ in range(5):
        with pytest.raises(ApiError):
            verification.verify(request, OWNER)
    with pytest.raises(ApiError) as caught:
        verification.verify(request, OWNER)
    assert caught.value.code == "DEMO_PHONE_VERIFICATION_REQUIRED"
    assert sms_provider.verify.call_count == 5
    with us_context.sessions() as session:
        row = session.get(OutboundPhoneVerification, challenge.challenge_id)
        assert row is not None
        assert row.attempts == 5
        assert row.verified_at is None


def test_consumed_phone_proof_cannot_dial_a_different_request(
    us_context: Context,
) -> None:
    us_context.service.settings.outbound_demo_account_daily_limit = 2
    us_context.service.settings.outbound_demo_number_daily_limit = 2
    request = us_context.verified_input(data(phone_number="+12025550123"), OWNER)
    result = us_context.service.create(request, OWNER)
    us_context.service.webhook(final_event(result.id))
    with us_context.sessions() as session, session.begin():
        row = session.get(OutboundDemoCall, result.id)
        assert row is not None
        row.created_at = datetime.now(UTC) - timedelta(minutes=10)
    with pytest.raises(ApiError) as caught:
        us_context.service.create(
            request.model_copy(update={"request_id": uuid4()}), OWNER
        )
    assert caught.value.code == "DEMO_PHONE_VERIFICATION_REQUIRED"
    assert us_context.service.create(request, OWNER).id == result.id
    assert us_context.provider.dial_count == 1


def test_sms_limits_share_number_account_and_business_budget(
    us_context: Context,
    sms_provider: Mock,
) -> None:
    verification = us_context.service.verification
    first = SmsStartInput(
        phone_number="+12025550123",
        sms_consent=True,
        sms_consent_version="outbound-sms-v1",
    )
    verification.start(first, OWNER)
    for request, owner in [
        (first, "other-account"),
        (first.model_copy(update={"phone_number": "+12125550123"}), OWNER),
    ]:
        with pytest.raises(ApiError) as caught:
            verification.start(request, owner)
        assert caught.value.code == "DEMO_SMS_LIMIT"
    verification.settings.outbound_demo_sms_daily_limit = 1
    with pytest.raises(ApiError) as caught:
        verification.start(
            first.model_copy(update={"phone_number": "+12125550123"}), "new-account"
        )
    assert caught.value.code == "DEMO_SMS_LIMIT"
    assert sms_provider.send.call_count == 1


def test_failed_sms_send_is_budgeted_and_is_not_automatically_retried(
    us_context: Context,
    sms_provider: Mock,
) -> None:
    sms_provider.send.side_effect = sms_unavailable()
    request = SmsStartInput(
        phone_number="+12025550123",
        sms_consent=True,
        sms_consent_version="outbound-sms-v1",
    )
    with pytest.raises(ApiError):
        us_context.service.verification.start(request, OWNER)
    with pytest.raises(ApiError) as caught:
        us_context.service.verification.start(request, OWNER)
    assert caught.value.code == "DEMO_SMS_LIMIT"
    assert sms_provider.send.call_count == 1


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
    result = context.create_verified(data(), OWNER)
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
    result = context.create_verified(data(), OWNER)
    context.service.webhook(final_event(result.id, metadata=metadata))
    response = context.service.get(result.id, OWNER)
    assert response.status == status
    assert response.terminal is True


def test_sip_transfer_keeps_slot_until_carrier_end_confirmation(
    context: Context,
) -> None:
    result = context.create_verified(data(), OWNER)
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
    response = context.create_verified(data(), OWNER)
    assert response.status is DemoCallStatus.UNKNOWN
    assert response.transfer_status == "unconfirmed"
    with pytest.raises(ApiError) as caught:
        context.create_verified(data(), OWNER)
    assert caught.value.code == "DEMO_CALL_LIMIT"
    assert context.provider.dial_count == 1


def test_malformed_webhook_does_not_release_active_slot(context: Context) -> None:
    result = context.create_verified(data(), OWNER)
    with pytest.raises(ApiError) as caught:
        context.service.webhook(
            final_event(result.id, transcript=[{"tool_results": True}])
        )
    assert caught.value.status_code == 422
    assert context.service.get(result.id, OWNER).status is DemoCallStatus.DIALING


def test_number_limit_survives_cookies_terminal_calls_and_new_keys(
    context: Context,
) -> None:
    result = context.create_verified(data(), OWNER)
    context.service.webhook(final_event(result.id))
    with context.sessions() as session, session.begin():
        row = session.get(OutboundDemoCall, result.id)
        assert row is not None
        row.created_at = datetime.now(UTC) - timedelta(minutes=10)
    with pytest.raises(ApiError) as caught:
        context.create_verified(data(), "fresh-cookie")
    assert caught.value.status_code == 429
    assert context.provider.dial_count == 1


def test_daily_budget_counts_failed_calls_across_destinations(context: Context) -> None:
    other_number = "+15559990004"
    context.service.settings.outbound_demo_allowed_numbers = SecretStr(
        f"{NUMBER},{other_number}"
    )
    context.service.settings.outbound_demo_daily_limit = 1
    context.provider.fail_preflight = True
    result = context.create_verified(data(), OWNER)
    with context.sessions() as session, session.begin():
        row = session.get(OutboundDemoCall, result.id)
        assert row is not None
        row.created_at = datetime.now(UTC) - timedelta(minutes=10)
    with pytest.raises(ApiError) as caught:
        context.create_verified(data(phone_number=other_number), "fresh-cookie")
    assert caught.value.status_code == 429
    assert context.provider.dial_count == 0


def test_webhook_before_http_receipt_can_bind_reserved_call(context: Context) -> None:
    call_id, _ = context.service._reserve(context.verified_input(data(), OWNER), OWNER)
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
