import asyncio
import hashlib
import hmac
import json
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.application import create_app
from insurance_operations.database.models.approved_faq import AgencyApprovedFaq
from insurance_operations.database.models.conversation import (
    ConversationIntake,
    ConversationSession,
)
from insurance_operations.database.models.identity import (
    Agency,
    AgencyMembership,
    AppUser,
)
from insurance_operations.database.models.lead import AgencyLead, LeadHandoffRequest
from insurance_operations.database.models.receptionist import AgencyReceptionistSettings
from insurance_operations.database.models.telephony import (
    AgencyCallPolicy,
    AgencyInboundNumber,
    InboundCall,
    InboundCallEvent,
)
from insurance_operations.settings import ApiSettings, DatabaseSettings
from insurance_operations.telephony.ingress import configure_telephony_ingress
from insurance_operations.telephony.settings import TelephonyProviderSettings

AGENT = "synthetic-sip-phone-agent"
INIT_SECRET = "synthetic-sip-init-secret-at-least-32-characters"
TOOL_SECRET = "synthetic-sip-tool-secret"
POST_SECRET = "synthetic-sip-post-call-secret"
PREFIX = "/api/v1/providers/elevenlabs/"
INIT_PATH = PREFIX + "sip/initialize"
INIT_HEADERS = {"Authorization": f"Bearer {INIT_SECRET}"}
TOOL_HEADERS = {"Authorization": f"Bearer {TOOL_SECRET}"}


@dataclass
class SipContext:
    app: FastAPI
    sessions: sessionmaker[Session]
    agency_id: UUID
    user_id: UUID
    called_number: str
    conversation_id: str
    call_id: str

    def payload(self, **overrides: object) -> dict[str, object]:
        return {
            "caller_id": "+15559991002",
            "called_number": self.called_number,
            "agent_id": AGENT,
            "conversation_id": self.conversation_id,
            "call_id": self.call_id,
            "call_sid": "",
            **overrides,
        }


@pytest.fixture
def make_sip_context(
    migrated_database: Engine,
    database_settings: DatabaseSettings,
    monkeypatch: pytest.MonkeyPatch,
) -> Callable[[], SipContext]:
    def forbidden_twilio(*args: object, **kwargs: object) -> None:
        raise AssertionError("SIP must not construct Twilio or invoke register-call")

    monkeypatch.setattr(
        "insurance_operations.telephony.ingress.TwilioTelephonyAdapter",
        forbidden_twilio,
    )
    monkeypatch.setattr(
        "insurance_operations.telephony.providers.elevenlabs."
        "ElevenLabsPhoneProvider.register_inbound_call",
        forbidden_twilio,
    )

    def build() -> SipContext:
        sessions = sessionmaker(
            bind=migrated_database, class_=Session, expire_on_commit=False
        )
        number = f"+1555{uuid4().int % 10**7:07d}"
        with sessions() as session, session.begin():
            agency = Agency(
                name="Synthetic SIP HVAC",
                slug=f"sip-{uuid4()}",
                environment_kind="DEVELOPMENT",
            )
            user = AppUser(auth_subject=uuid4(), display_name="Synthetic SIP Operator")
            session.add_all([agency, user])
            session.flush()
            session.add(AgencyMembership(agency_id=agency.id, app_user_id=user.id))
            session.add(
                AgencyCallPolicy(
                    agency_id=agency.id,
                    inbound_enabled=True,
                    timezone="UTC",
                    availability_windows=[
                        {"weekday": day, "start_local": "00:00", "end_local": "23:59"}
                        for day in range(7)
                    ],
                    transfer_enabled=True,
                    transfer_destination_e164="+15559991003",
                    transfer_ring_timeout_seconds=20,
                    max_concurrent_calls=2,
                    daily_call_limit=10,
                    callback_fallback_enabled=True,
                    after_hours_message="The team is outside office hours.",
                    unavailable_message="Please confirm details for a callback.",
                    created_by=user.id,
                    updated_by=user.id,
                )
            )
            session.add(
                AgencyInboundNumber(
                    agency_id=agency.id,
                    phone_number_e164=number,
                    label="Synthetic SIP line",
                    status="ACTIVE",
                    created_by=user.id,
                    updated_by=user.id,
                )
            )
            agency_id, user_id = agency.id, user.id
        api_settings = ApiSettings(
            _env_file=None,
            app_environment="development",
            api_host="127.0.0.1",
            api_port=8000,
            database_url=database_settings.runtime_database_url,
            database_ssl_mode=database_settings.database_ssl_mode,
            development_actor_user_id=user_id,
            conversation_ai_enabled=False,
            google_calendar_enabled=False,
            booking_email_enabled=False,
            demo_sandbox_enabled=False,
            customer_portal_enabled=False,
            homepage_chat_enabled=False,
        )
        sessions.configure(info={"integration_settings": api_settings})
        provider_settings = TelephonyProviderSettings(
            _env_file=None,
            app_environment="development",
            telephony_provider_enabled=True,
            telephony_provider="telnyx_sip",
            development_actor_user_id=user_id,
            elevenlabs_phone_agent_id=AGENT,
            elevenlabs_phone_initiation_secret=INIT_SECRET,
            elevenlabs_phone_tool_secret=TOOL_SECRET,
            elevenlabs_post_call_webhook_secret=POST_SECRET,
            elevenlabs_privacy_confirmed=True,
        )
        app = create_app(api_settings, migrated_database)
        configure_telephony_ingress(app, provider_settings, migrated_database)
        return SipContext(
            app=app,
            sessions=sessions,
            agency_id=agency_id,
            user_id=user_id,
            called_number=number,
            conversation_id=f"conv_{uuid4()}",
            call_id=f"{uuid4()}@carrier.example.test",
        )

    return build


@pytest.fixture
def sip(make_sip_context: Callable[[], SipContext]) -> SipContext:
    return make_sip_context()


def post(
    sip: SipContext,
    path: str,
    *,
    payload: dict[str, object] | None = None,
    headers: dict[str, str] | None = None,
    content: bytes | None = None,
) -> Response:
    async def send() -> Response:
        async with AsyncClient(
            transport=ASGITransport(app=sip.app), base_url="http://test"
        ) as client:
            return await client.post(
                path, json=payload, headers=headers, content=content
            )

    return asyncio.run(send())


def initialize(sip: SipContext, **changes: object) -> Response:
    return post(sip, INIT_PATH, payload=sip.payload(**changes), headers=INIT_HEADERS)


def call_context(sip: SipContext, initialized: Response) -> dict[str, object]:
    return {
        "inbound_call_id": initialized.json()["dynamic_variables"][
            "phone_inbound_call_id"
        ],
        "conversation_id": sip.conversation_id,
    }


def consent(sip: SipContext, context: dict[str, object], **changes: object) -> Response:
    return post(
        sip,
        PREFIX + "tools/phone-consent",
        headers=TOOL_HEADERS,
        payload={
            **context,
            "ai_disclosure_accepted": True,
            "microphone_consent_granted": True,
            **changes,
        },
    )


def signed_post(sip: SipContext, payload: dict[str, object]) -> Response:
    body = json.dumps(payload).encode()
    timestamp = int(datetime.now(UTC).timestamp())
    signature = hmac.new(
        POST_SECRET.encode(), str(timestamp).encode() + b"." + body, hashlib.sha256
    ).hexdigest()
    return post(
        sip,
        PREFIX + "post-call",
        content=body,
        headers={"ElevenLabs-Signature": f"t={timestamp},v0={signature}"},
    )


def end_payload(sip: SipContext, context: dict[str, object]) -> dict[str, object]:
    return {
        "type": "post_call_transcription",
        "event_timestamp": int(datetime.now(UTC).timestamp()),
        "data": {
            "agent_id": AGENT,
            "conversation_id": sip.conversation_id,
            "conversation_initiation_client_data": {
                "dynamic_variables": {
                    "phone_inbound_call_id": context["inbound_call_id"]
                }
            },
            "transcript": [],
        },
    }


def test_authenticated_initiation_persists_exact_context_and_replays(
    sip: SipContext,
) -> None:
    first = initialize(sip)
    assert first.status_code == 200, first.text
    assert first.headers["cache-control"] == "no-store"
    assert first.json() == initialize(sip).json()
    variables = first.json()["dynamic_variables"]
    assert set(first.json()) == {"type", "dynamic_variables"}
    assert first.json()["type"] == "conversation_initiation_client_data"
    assert set(variables) == {"phone_inbound_call_id", "phone_max_duration_seconds"}
    assert variables["phone_max_duration_seconds"] == 180
    with sip.sessions() as session:
        call = session.get(InboundCall, UUID(variables["phone_inbound_call_id"]))
        assert call is not None
        assert call.agency_id == sip.agency_id and call.adapter_name == "telnyx_sip"
        assert call.source_call_reference == sip.call_id
        assert (
            call.adapter_metadata["external_session_reference"] == sip.conversation_id
        )
        assert call.adapter_metadata["provider_call_id"] == sip.call_id
        assert (
            session.scalar(
                select(func.count())
                .select_from(ConversationSession)
                .where(ConversationSession.inbound_call_id == call.id)
            )
            == 0
        )
    assert initialize(sip, conversation_id="conv_other").status_code == 409
    assert initialize(sip, call_id="another-SIP-ID").status_code == 409
    assert initialize(sip, caller_id="+15559991004").status_code == 409


def test_digits_only_sip_numbers_share_the_canonical_call_and_tenant_route(
    sip: SipContext, make_sip_context: Callable[[], SipContext]
) -> None:
    initialized = initialize(
        sip, called_number=sip.called_number.removeprefix("+"), caller_id="15559991002"
    )
    assert initialized.status_code == 200, initialized.text
    assert initialized.headers["cache-control"] == "no-store"
    assert initialized.json()["type"] == "conversation_initiation_client_data"
    assert initialize(sip).json() == initialized.json()
    call_id = UUID(initialized.json()["dynamic_variables"]["phone_inbound_call_id"])
    with sip.sessions() as session:
        call = session.get(InboundCall, call_id)
        assert call is not None
        assert call.agency_id == sip.agency_id
        assert call.caller_number_e164 == "+15559991002"
        assert (
            session.scalar(
                select(func.count())
                .select_from(InboundCall)
                .where(InboundCall.agency_id == sip.agency_id)
            )
            == 1
        )
    other = make_sip_context()
    assert (
        initialize(sip, called_number=other.called_number.removeprefix("+")).status_code
        == 404
    )


@pytest.mark.parametrize("authorization", [None, "Bearer invalid", "Basic invalid"])
def test_initiation_authentication_precedes_database_work(
    sip: SipContext, authorization: str | None
) -> None:
    headers = {"Authorization": authorization} if authorization is not None else {}
    result = post(sip, INIT_PATH, payload=sip.payload(), headers=headers)
    assert result.status_code == 401
    with sip.sessions() as session:
        assert (
            session.scalar(
                select(func.count())
                .select_from(InboundCall)
                .where(InboundCall.agency_id == sip.agency_id)
            )
            == 0
        )


def test_number_agent_policy_and_body_rejections(sip: SipContext) -> None:
    assert initialize(sip, called_number="+15550000000").status_code == 404
    assert initialize(sip, agent_id="wrong-agent").status_code == 403
    assert initialize(sip, conversation_id="x" * 181).status_code == 422
    assert initialize(sip, agency_id=str(sip.agency_id)).status_code == 422
    too_large = post(
        sip,
        INIT_PATH,
        headers={**INIT_HEADERS, "Content-Type": "application/json"},
        content=b" " * 16_385,
    )
    assert too_large.status_code == 413
    with sip.sessions() as session, session.begin():
        number = session.scalar(
            select(AgencyInboundNumber).where(
                AgencyInboundNumber.agency_id == sip.agency_id
            )
        )
        assert number is not None
        number.status = "INACTIVE"
    assert initialize(sip).status_code == 404
    with sip.sessions() as session, session.begin():
        number = session.scalar(
            select(AgencyInboundNumber).where(
                AgencyInboundNumber.agency_id == sip.agency_id
            )
        )
        policy = session.scalar(
            select(AgencyCallPolicy).where(AgencyCallPolicy.agency_id == sip.agency_id)
        )
        assert number is not None and policy is not None
        number.status = "ACTIVE"
        policy.inbound_enabled = False
    assert initialize(sip).status_code == 409


def test_tenant_routing_and_consent_isolation(
    sip: SipContext, make_sip_context: Callable[[], SipContext]
) -> None:
    other = make_sip_context()
    initialized = initialize(sip)
    context = call_context(sip, initialized)
    assert initialize(sip, called_number=other.called_number).status_code == 404
    assert initialize(other, call_id=sip.call_id).status_code == 409
    assert consent(other, context).status_code == 409
    wrong_conversation = {**context, "conversation_id": "conv_forged"}
    assert consent(sip, wrong_conversation).status_code == 409
    assert consent(sip, context).status_code == 200
    for tool, body in [
        ("availability", {"postal_code": "10001", "day": "2026-11-01"}),
        ("approved-faq", {"query": "office hours"}),
    ]:
        assert (
            post(
                sip,
                PREFIX + "tools/" + tool,
                payload={**wrong_conversation, **body},
                headers=TOOL_HEADERS,
            ).status_code
            == 409
        )


def test_fallback_identity_binds_real_system_call_id_on_consent(
    sip: SipContext,
) -> None:
    initialized = initialize(sip, call_id=None, call_sid="not-a-Twilio-SID")
    assert initialized.status_code == 200
    context = call_context(sip, initialized)
    assert consent(sip, context, call_id=sip.call_id).status_code == 200
    assert consent(sip, context, call_id="different-call").status_code == 409
    assert initialize(sip, call_id=None, call_sid="").json() == initialized.json()
    with sip.sessions() as session:
        call = session.get(InboundCall, UUID(str(context["inbound_call_id"])))
        assert call is not None
        assert call.source_call_reference == f"conversation:{sip.conversation_id}"
        assert call.adapter_metadata["provider_call_id"] == sip.call_id


@pytest.mark.parametrize("duplicate", [True, False])
def test_parallel_initialization_serializes_duplicates_and_concurrent_limits(
    sip: SipContext, duplicate: bool
) -> None:
    with sip.sessions() as session, session.begin():
        policy = session.scalar(
            select(AgencyCallPolicy).where(AgencyCallPolicy.agency_id == sip.agency_id)
        )
        assert policy is not None
        policy.max_concurrent_calls = 1

    def start(index: int) -> Response:
        return (
            initialize(sip)
            if duplicate
            else initialize(
                sip,
                call_id=f"{sip.call_id}.{index}",
                conversation_id=f"{sip.conversation_id}_{index}",
            )
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(start, range(2)))
    assert sorted(result.status_code for result in results) == (
        [200, 200] if duplicate else [200, 429]
    )
    if duplicate:
        assert results[0].json() == results[1].json()
    with sip.sessions() as session:
        assert (
            session.scalar(
                select(func.count())
                .select_from(InboundCall)
                .where(InboundCall.agency_id == sip.agency_id)
            )
            == 1
        )


def test_unconfirmed_signed_end_releases_concurrency_but_preserves_daily_quota(
    sip: SipContext,
) -> None:
    with sip.sessions() as session, session.begin():
        policy = session.scalar(
            select(AgencyCallPolicy).where(AgencyCallPolicy.agency_id == sip.agency_id)
        )
        assert policy is not None
        policy.daily_call_limit = 1
    first = initialize(sip)
    context = call_context(sip, first)
    payload = end_payload(sip, context)
    assert (
        post(
            sip, PREFIX + "post-call", content=json.dumps(payload).encode()
        ).status_code
        == 403
    )
    assert signed_post(sip, payload).status_code == 200
    assert signed_post(sip, payload).status_code == 200
    assert initialize(sip).status_code == 409
    limited = initialize(sip, call_id="new-SIP-call", conversation_id="conv_new_call")
    assert limited.status_code == 429
    assert limited.json()["error"]["code"] == "INBOUND_CALL_DAILY_LIMIT_REACHED"
    with sip.sessions() as session:
        call = session.get(InboundCall, UUID(str(context["inbound_call_id"])))
        assert call is not None and call.status == "COMPLETED"
        assert (
            session.scalar(
                select(func.count())
                .select_from(ConversationIntake)
                .where(ConversationIntake.agency_id == sip.agency_id)
            )
            == 0
        )
    changed = end_payload(sip, {**context, "inbound_call_id": str(uuid4())})
    assert signed_post(sip, changed).status_code == 409


def test_signed_sip_initiation_failure_uses_documented_metadata_and_replays(
    sip: SipContext,
) -> None:
    first = initialize(sip, call_id=None)
    payload: dict[str, object] = {
        "type": "call_initiation_failure",
        "event_timestamp": int(datetime.now(UTC).timestamp()),
        "data": {
            "agent_id": AGENT,
            "conversation_id": sip.conversation_id,
            "failure_reason": "unknown",
            "metadata": {
                "type": "sip",
                "body": {
                    "from_number": "+15559991002",
                    "to_number": sip.called_number,
                    "sip_status_code": 503,
                    "error_reason": "unavailable",
                    "call_sid": sip.call_id,
                },
            },
        },
    }
    assert signed_post(sip, payload).status_code == 200
    assert signed_post(sip, payload).status_code == 200
    with sip.sessions() as session:
        call = session.get(
            InboundCall, UUID(str(call_context(sip, first)["inbound_call_id"]))
        )
        assert call is not None and call.status == "FAILED"
        assert call.failure_code == "PHONE_PROVIDER_INITIATION_FAILED"
        assert call.adapter_metadata["provider_call_id"] == sip.call_id


def test_uninitialized_failure_is_a_context_conflict_not_a_schema_failure(
    sip: SipContext,
) -> None:
    payload: dict[str, object] = {
        "type": "call_initiation_failure",
        "event_timestamp": int(datetime.now(UTC).timestamp()),
        "data": {
            "agent_id": AGENT,
            "conversation_id": sip.conversation_id,
            "failure_reason": "unknown",
            "metadata": {"type": "sip", "body": {"call_sid": sip.call_id}},
        },
    }
    result = signed_post(sip, payload)
    assert result.status_code == 409
    assert result.json()["error"]["code"] == "PHONE_CONVERSATION_CONTEXT_INVALID"
    with sip.sessions() as session:
        assert (
            session.scalar(
                select(func.count())
                .select_from(InboundCall)
                .where(InboundCall.agency_id == sip.agency_id)
            )
            == 0
        )


def test_post_call_diagnostics_are_emitted_only_after_signature_verification(
    sip: SipContext, caplog: pytest.LogCaptureFixture
) -> None:
    payload = end_payload(sip, {"inbound_call_id": "private-invalid-uuid"})
    unsigned = post(sip, PREFIX + "post-call", content=json.dumps(payload).encode())
    assert unsigned.status_code == 403
    assert not caplog.records
    result = signed_post(sip, payload)
    assert result.status_code == 422
    assert result.json()["error"]["code"] == "PHONE_POST_CALL_EVENT_INVALID"
    assert len(caplog.records) == 1
    assert caplog.records[0].args == (
        [
            {
                "path": "data.conversation_initiation_client_data.dynamic_variables."
                "phone_inbound_call_id",
                "type": "uuid_parsing",
            }
        ],
    )
    assert "private" not in caplog.text
    assert POST_SECRET not in caplog.text


def test_expired_initialization_cannot_restart_or_obtain_consent(
    sip: SipContext,
) -> None:
    first = initialize(sip)
    context = call_context(sip, first)
    with sip.sessions() as session, session.begin():
        call = session.get(InboundCall, UUID(str(context["inbound_call_id"])))
        assert call is not None
        call.received_at = datetime.now(UTC) - timedelta(seconds=181)
    assert initialize(sip).status_code == 409
    assert consent(sip, context).status_code == 409


@pytest.mark.parametrize("callback_enabled", [True, False])
def test_telnyx_handoff_respects_callback_policy_without_carrier_transfer(
    sip: SipContext, monkeypatch: pytest.MonkeyPatch, callback_enabled: bool
) -> None:
    def forbidden_transfer(*args: object, **kwargs: object) -> None:
        raise AssertionError("SIP live transfer must remain disabled")

    monkeypatch.setattr(
        "insurance_operations.telephony.providers.telnyx_sip."
        "TelnyxSipAdapter.request_transfer",
        forbidden_transfer,
    )
    with sip.sessions() as session, session.begin():
        policy = session.scalar(
            select(AgencyCallPolicy).where(AgencyCallPolicy.agency_id == sip.agency_id)
        )
        assert policy is not None
        policy.callback_fallback_enabled = callback_enabled
    first = initialize(sip)
    context = call_context(sip, first)
    assert consent(sip, context).status_code == 200
    payload = {**context, "kind": "LIVE_TRANSFER"}
    handoff = post(
        sip, PREFIX + "tools/request-handoff", payload=payload, headers=TOOL_HEADERS
    )
    assert handoff.status_code == 200, handoff.text
    assert handoff.json()["action"] == (
        "COLLECT_CALLBACK" if callback_enabled else "CONTINUE_AI"
    )
    assert (
        post(
            sip, PREFIX + "tools/request-handoff", payload=payload, headers=TOOL_HEADERS
        ).json()["replayed"]
        is True
    )
    with sip.sessions() as session:
        events = session.scalars(
            select(InboundCallEvent).where(
                InboundCallEvent.inbound_call_id
                == UUID(str(context["inbound_call_id"]))
            )
        ).all()
        assert any(event.event_type == "TRANSFER_REQUESTED" for event in events)
        assert not any(event.event_type == "TRANSFER_SUCCEEDED" for event in events)


def test_shared_phone_tools_finalize_only_confirmed_content_and_a_callback(
    sip: SipContext,
) -> None:
    with sip.sessions() as session, session.begin():
        session.add(
            AgencyReceptionistSettings(
                agency_id=sip.agency_id,
                public_name="Synthetic SIP HVAC",
                greeting="I am the AI receptionist.",
                office_hours="Weekdays",
                contact_phone="+15559991003",
                supported_insurance_categories=["AC repair"],
                escalation_message="Please speak with our team.",
                created_by=sip.user_id,
                updated_by=sip.user_id,
            )
        )
        session.add(
            AgencyApprovedFaq(
                agency_id=sip.agency_id,
                question="What services are available?",
                normalized_question="what services are available",
                approved_answer="AC repair is available.",
                status="ACTIVE",
                created_by=sip.user_id,
                updated_by=sip.user_id,
            )
        )
    first = initialize(sip)
    context = call_context(sip, first)
    assert consent(sip, context).status_code == 200
    faq = post(
        sip,
        PREFIX + "tools/approved-faq",
        headers=TOOL_HEADERS,
        payload={**context, "query": "What services are available?"},
    )
    assert faq.status_code == 200 and faq.json()["matched"] is True
    assert faq.json()["answer"] == "AC repair is available."
    confirmation = {
        **context,
        "customer": {"full_name": "Synthetic SIP Caller", "phone": "+15559991002"},
        "intake_intent": "Request AC repair and a callback",
        "explicit_verbal_confirmation": True,
    }
    assert (
        post(
            sip,
            PREFIX + "tools/confirm-intake",
            headers=TOOL_HEADERS,
            payload={**confirmation, "explicit_verbal_confirmation": False},
        ).status_code
        == 422
    )
    for _ in range(2):
        assert (
            post(
                sip,
                PREFIX + "tools/confirm-intake",
                headers=TOOL_HEADERS,
                payload=confirmation,
            ).status_code
            == 200
        )
    assert (
        post(
            sip,
            PREFIX + "tools/request-handoff",
            headers=TOOL_HEADERS,
            payload={**context, "kind": "LIVE_TRANSFER"},
        ).json()["action"]
        == "COLLECT_CALLBACK"
    )
    with sip.sessions() as session:
        assert (
            session.scalar(
                select(func.count())
                .select_from(AgencyLead)
                .where(AgencyLead.agency_id == sip.agency_id)
            )
            == 0
        )
    payload = end_payload(sip, context)
    data = payload["data"]
    assert isinstance(data, dict)
    data["conversation_id"] = "conv_wrong_binding"
    assert signed_post(sip, payload).status_code == 409
    data["conversation_id"] = sip.conversation_id
    assert signed_post(sip, payload).status_code == 422
    data["transcript"] = [
        {"role": "agent", "message": "Do you confirm this intake and callback?"},
        {"role": "user", "message": "Yes, I confirm."},
    ]
    assert signed_post(sip, payload).status_code == 200
    assert signed_post(sip, payload).status_code == 200
    data["transcript"] = [
        {"role": "agent", "message": "Do you confirm this intake and callback?"},
        {"role": "user", "message": "A changed replay must be rejected."},
    ]
    assert signed_post(sip, payload).status_code == 409
    with sip.sessions() as session:
        leads = session.scalars(
            select(AgencyLead).where(AgencyLead.agency_id == sip.agency_id)
        ).all()
        handoffs = session.scalars(
            select(LeadHandoffRequest).where(
                LeadHandoffRequest.agency_id == sip.agency_id
            )
        ).all()
        assert len(leads) == 1
        assert len(handoffs) == 1 and handoffs[0].request_kind == "CALLBACK"


def test_same_conversation_cannot_be_initialized_in_parallel_for_two_businesses(
    sip: SipContext, make_sip_context: Callable[[], SipContext]
) -> None:
    other = make_sip_context()

    def start(context: SipContext) -> Response:
        return initialize(context, conversation_id=sip.conversation_id)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(start, [sip, other]))
    assert sorted(result.status_code for result in results) == [200, 409]
