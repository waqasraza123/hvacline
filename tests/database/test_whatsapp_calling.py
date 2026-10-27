import asyncio
import hashlib
import hmac
import json
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.application import create_app
from insurance_operations.database.models.conversation import ConversationSession
from insurance_operations.database.models.hvac import Appointment, HvacServiceRequest
from insurance_operations.database.models.identity import (
    Agency,
    AgencyMembership,
    AppUser,
)
from insurance_operations.database.models.lead import LeadHandoffRequest
from insurance_operations.database.models.whatsapp import WhatsAppConversation
from insurance_operations.hvac.schemas import ScheduleInput
from insurance_operations.hvac.service import SchedulingService
from insurance_operations.settings import ApiSettings, DatabaseSettings
from insurance_operations.whatsapp.routes import CONSENT_READBACK, configure_whatsapp
from insurance_operations.whatsapp.settings import WhatsAppSettings


def history(readback: str, answer: str = "yes") -> str:
    return json.dumps(
        {
            "entries": [
                {"role": "agent", "message": readback},
                {"role": "user", "message": answer},
            ]
        }
    )


@pytest.fixture
def whatsapp_connection(migrated_database: Engine) -> Iterator[Connection]:
    with migrated_database.connect() as connection:
        transaction = connection.begin()
        try:
            yield connection
        finally:
            transaction.rollback()


@pytest.mark.parametrize("callback_only", [False, True])
def test_whatsapp_inbound_call_is_scoped_consented_idempotent_and_persisted(
    migrated_database: Engine,
    whatsapp_connection: Connection,
    database_settings: DatabaseSettings,
    callback_only: bool,
) -> None:
    sessions = sessionmaker(
        bind=whatsapp_connection,
        class_=Session,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    with sessions() as session, session.begin():
        agency = Agency(
            name="Synthetic WhatsApp HVAC",
            slug=f"whatsapp-{uuid4()}",
            environment_kind="DEVELOPMENT",
        )
        user = AppUser(auth_subject=uuid4(), display_name="Synthetic WhatsApp Operator")
        session.add_all([agency, user])
        session.flush()
        session.add(AgencyMembership(agency_id=agency.id, app_user_id=user.id))
        agency_id, user_id = agency.id, user.id
    settings = ApiSettings(
        _env_file=None,
        app_environment="development",
        api_host="127.0.0.1",
        api_port=8000,
        database_url=database_settings.runtime_database_url,
        database_ssl_mode=database_settings.database_ssl_mode,
        development_actor_user_id=user_id,
        conversation_daily_session_limit=1,
        conversation_ai_enabled=False,
        google_calendar_enabled=False,
        booking_email_enabled=False,
    )
    whatsapp = WhatsAppSettings(
        _env_file=None,
        app_environment="development",
        whatsapp_enabled=True,
        whatsapp_agency_id=agency_id,
        whatsapp_actor_user_id=user_id,
        elevenlabs_whatsapp_agent_id="synthetic-agent",
        elevenlabs_whatsapp_phone_number_id="synthetic-number-id",
        elevenlabs_whatsapp_init_secret="i" * 32,
        elevenlabs_whatsapp_tool_secret="t" * 32,
        elevenlabs_whatsapp_session_secret="s" * 32,
        elevenlabs_whatsapp_post_call_secret="p" * 32,
        elevenlabs_whatsapp_privacy_confirmed=True,
    )
    sessions.configure(info={"integration_settings": settings})
    with (
        patch("insurance_operations.application.sessionmaker", return_value=sessions),
        patch(
            "insurance_operations.whatsapp.routes.sessionmaker", return_value=sessions
        ),
    ):
        app = create_app(settings, migrated_database)
        configure_whatsapp(app, settings, whatsapp, migrated_database)
    scheduling = SchedulingService(sessions)
    day = (datetime.now(UTC) + timedelta(days=2)).date()
    windows = [{"weekday": day.weekday(), "start": "08:00", "end": "17:00"}]
    scheduling.configure(
        agency_id,
        ScheduleInput.model_validate(
            {
                "expected_version": 0,
                "enabled": True,
                "timezone": "America/New_York",
                "postal_codes": ["10001"],
                "windows": windows,
                "notice_minutes": 0,
                "teams": [{"key": "team-a", "name": "Test team", "windows": windows}],
            }
        ),
        uuid4(),
    )

    async def scenario() -> None:
        base = "/api/v1/providers/elevenlabs/whatsapp"
        conversation_id = f"conv_{uuid4()}"
        payload = {
            "caller_id": "BSUID:opaque-user",
            "called_number": "synthetic-number-id",
            "agent_id": "synthetic-agent",
            "call_sid": "",
            "conversation_id": conversation_id,
        }
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            assert (
                await client.post(f"{base}/initialize", json=payload)
            ).status_code == 401
            initialized = await client.post(
                f"{base}/initialize",
                json=payload,
                headers={"Authorization": "Bearer " + "i" * 32},
            )
            assert initialized.status_code == 200, initialized.text
            variables = initialized.json()["dynamic_variables"]
            repeated = await client.post(
                f"{base}/initialize",
                json=payload,
                headers={"Authorization": "Bearer " + "i" * 32},
            )
            assert repeated.json() == initialized.json()
            conflicting = await client.post(
                f"{base}/initialize",
                json={**payload, "caller_id": "another-BSUID"},
                headers={"Authorization": "Bearer " + "i" * 32},
            )
            assert conflicting.status_code == 401
            concurrent = await client.post(
                f"{base}/initialize",
                json={**payload, "conversation_id": f"conv_{uuid4()}"},
                headers={"Authorization": "Bearer " + "i" * 32},
            )
            assert concurrent.status_code == 409
            headers = {
                "Authorization": "Bearer " + "t" * 32,
                "X-HVACLine-Binding-ID": variables["whatsapp_binding_id"],
                "X-HVACLine-Session-Token": variables["secret__whatsapp_session_token"],
                "X-ElevenLabs-Conversation-ID": conversation_id,
                "X-ElevenLabs-Text-Only": "false",
            }
            consent_data = {
                "ai_disclosure_accepted": True,
                "voice_processing_accepted": True,
                "synthetic_data_acknowledged": True,
                "provider_history": history(CONSENT_READBACK),
            }
            for changed in [
                {"X-ElevenLabs-Text-Only": "true"},
                {"X-ElevenLabs-Conversation-ID": "another-call"},
                {"X-HVACLine-Session-Token": "invalid"},
            ]:
                assert (
                    await client.post(
                        f"{base}/consent",
                        json=consent_data,
                        headers={**headers, **changed},
                    )
                ).status_code == 401
            assert (
                await client.post(
                    f"{base}/consent",
                    json={
                        **consent_data,
                        "provider_history": history(CONSENT_READBACK, "no"),
                    },
                    headers=headers,
                )
            ).status_code == 422
            with sessions() as session:
                binding = session.scalar(
                    select(WhatsAppConversation).where(
                        WhatsAppConversation.conversation_id == conversation_id
                    )
                )
                assert binding is not None and binding.session_id is None
            consent = await client.post(
                f"{base}/consent", json=consent_data, headers=headers
            )
            assert consent.status_code == 200, consent.text
            session_id = consent.json()["session_id"]
            root = f"{base}/sessions/{session_id}"
            assert (
                await client.post(f"{base}/consent", json=consent_data, headers=headers)
            ).json() == consent.json()
            assert (
                await client.post(
                    f"{base}/sessions/{uuid4()}/faq",
                    json={"query": "hours"},
                    headers=headers,
                )
            ).status_code == 409
            customer: dict[str, object] = {
                "full_name": "Fictional Caller",
                "phone": "+15550100100",
            }
            if callback_only:
                readback = await client.post(
                    f"{root}/callback-readback",
                    json={"customer": customer},
                    headers=headers,
                )
                data = {
                    "customer": customer,
                    "reason": "Human assistance requested",
                    "provider_history": history(readback.json()["readback"]),
                }
                result = await client.post(
                    f"{root}/callback", json=data, headers=headers
                )
                assert result.status_code == 200, result.text
                assert result.json()["request_kind"] == "CALLBACK"
                assert (
                    await client.post(f"{root}/callback", json=data, headers=headers)
                ).json() == result.json()
            else:
                customer["address"] = {
                    "line1": "10 Fictional Street",
                    "city": "New York",
                    "state_code": "NY",
                    "postal_code": "10001",
                    "country_code": "US",
                }
                draft = {
                    "customer": customer,
                    "service": {
                        "kind": "AC_REPAIR",
                        "equipment_issue": "Fictional AC is not cooling",
                        "preferred_window": "Next available",
                        "hazardous_condition": False,
                    },
                }
                readback = await client.post(
                    f"{root}/booking/intake-readback", json=draft, headers=headers
                )
                assert readback.status_code == 200, readback.text
                data = {
                    **draft,
                    "provider_history": history(readback.json()["readback"]),
                }
                intake = await client.post(
                    f"{root}/confirm-intake", json=data, headers=headers
                )
                assert intake.status_code == 200, intake.text
                assert (
                    await client.post(
                        f"{root}/confirm-intake", json=data, headers=headers
                    )
                ).json() == intake.json()
                slots = await client.post(
                    f"{root}/booking/availability",
                    json={"day": day.isoformat()},
                    headers=headers,
                )
                assert slots.status_code == 200, slots.text
                slot = slots.json()["slots"][0]
                reservation = await client.post(
                    f"{root}/booking/reservations",
                    json={
                        "team_key": slot["team_key"],
                        "starts_at": slot["starts_at"],
                        "idempotency_key": f"whatsapp-{uuid4()}",
                    },
                    headers=headers,
                )
                assert reservation.status_code == 200, reservation.text
                assert reservation.json()["appointment"]["status"] == "HELD"
                confirm_url = f"{root}/booking/appointments/{reservation.json()['appointment']['id']}/confirm"
                assert (
                    await client.post(
                        confirm_url,
                        json={
                            "explicit_confirmation": True,
                            "provider_history": history(
                                reservation.json()["readback"], "no"
                            ),
                        },
                        headers=headers,
                    )
                ).status_code == 409
                confirmed = await client.post(
                    confirm_url,
                    json={
                        "explicit_confirmation": True,
                        "provider_history": history(reservation.json()["readback"]),
                    },
                    headers=headers,
                )
                assert confirmed.status_code == 200, confirmed.text
                assert confirmed.json()["appointment"]["status"] == "CONFIRMED"
                assert (
                    await client.post(
                        confirm_url,
                        json={
                            "explicit_confirmation": True,
                            "provider_history": history(reservation.json()["readback"]),
                        },
                        headers=headers,
                    )
                ).json() == confirmed.json()
            now = int(datetime.now(UTC).timestamp())
            body = json.dumps(
                {
                    "type": "post_call_transcription",
                    "event_timestamp": now,
                    "data": {
                        "agent_id": "synthetic-agent",
                        "conversation_id": conversation_id,
                        "transcript": [
                            {
                                "role": "agent",
                                "message": "This must never create a booking",
                            }
                        ],
                    },
                }
            ).encode()
            signature = hmac.new(
                b"p" * 32, str(now).encode() + b"." + body, hashlib.sha256
            ).hexdigest()
            post_headers = {"ElevenLabs-Signature": f"t={now},v0={signature}"}
            assert (
                await client.post(f"{base}/post-call", content=body)
            ).status_code == 401
            for _ in range(2):
                assert (
                    await client.post(
                        f"{base}/post-call", content=body, headers=post_headers
                    )
                ).status_code == 200
            assert (
                await client.post(
                    f"{root}/faq", json={"query": "hours"}, headers=headers
                )
            ).status_code == 409
            limited = await client.post(
                f"{base}/initialize",
                json={**payload, "conversation_id": f"conv_{uuid4()}"},
                headers={"Authorization": "Bearer " + "i" * 32},
            )
            assert limited.status_code == 429
            operations = await client.get("/api/v1/development/hvac/operations")
            assert operations.status_code == 200, operations.text
            if callback_only:
                assert len(operations.json()["handoffs"]) == 1
            else:
                assert operations.json()["appointments"][0]["status"] == "CONFIRMED"
                assert operations.json()["service_requests"][0]["status"] == "BOOKED"
        with sessions() as session:
            conversation = session.get(ConversationSession, UUID(session_id))
            assert conversation is not None and conversation.channel == "WHATSAPP"
            assert (
                conversation.inbound_call_id is None
                and conversation.ended_at is not None
            )
            count = session.scalar(
                select(func.count())
                .select_from(Appointment)
                .where(Appointment.agency_id == agency_id)
            )
            assert count == (0 if callback_only else 1)
            if callback_only:
                assert (
                    session.scalar(
                        select(func.count())
                        .select_from(LeadHandoffRequest)
                        .where(LeadHandoffRequest.agency_id == agency_id)
                    )
                    == 1
                )
            else:
                saved = session.scalar(
                    select(HvacServiceRequest).where(
                        HvacServiceRequest.agency_id == agency_id
                    )
                )
                assert saved is not None and saved.status == "BOOKED"

    asyncio.run(scenario())
