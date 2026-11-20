from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import DBAPIError

from insurance_operations.database.models.hvac import Appointment
from insurance_operations.database.models.recovery import RecoveryAttempt, RecoveryCase, RecoveryGrant, RecoveryWebhook
from insurance_operations.errors import ApiError
from insurance_operations.hvac.service import SchedulingService
from insurance_operations.hvac.schemas import AppointmentView
from insurance_operations.recovery.continuation import Confirmation, RecoveryContinuation, SlotSelection
from insurance_operations.recovery.delivery_jobs import expire_continuation
from insurance_operations.recovery.domain import destination_digest
from insurance_operations.recovery.grants import create_grant, grant_token
from insurance_operations.recovery.inbox import enqueue, process_event
from tests.database.test_recovery import RecoveryContext, recovery_context as recovery_context


def sent_attempt(context: RecoveryContext, *, channel: str = "SMS", uncertain: bool = False) -> RecoveryAttempt:
    with context.sessions() as session, session.begin():
        case = session.get(RecoveryCase, context.case_id)
        case.status = "NEEDS_REVIEW" if uncertain else "AWAITING_RESPONSE"
        attempt = RecoveryAttempt(agency_id=context.actor.agency_id, recovery_case_id=context.case_id,
            channel=channel, attempt_number=1, status="UNKNOWN" if uncertain else "SENT",
            scheduled_at=datetime.now(UTC) - timedelta(minutes=1), started_at=datetime.now(UTC) - timedelta(minutes=1),
            provider="TWILIO_SMS" if channel == "SMS" else "ELEVENLABS_RECOVERY",
            provider_reference=None if uncertain else "SM" + "7" * 32,
            recipient_digest=destination_digest(context.settings, context.actor.agency_id, "+12025550123"),
            dispatch_configuration={"business_name": "Synthetic HVAC"}, idempotency_key=str(uuid4()))
        session.add(attempt)
        session.flush()
        return attempt


def active_booking(context: RecoveryContext) -> tuple[RecoveryContinuation, str]:
    attempt = sent_attempt(context)
    with context.sessions() as session, session.begin():
        grant = create_grant(session, attempt, active=True, expires_at=datetime.now(UTC) + timedelta(minutes=30))
        token = grant_token(context.settings, grant)
    return RecoveryContinuation(context.sessions, context.settings), token


def reserve_and_read(context: RecoveryContext, continuation: RecoveryContinuation, token: str) -> dict[str, object]:
    available = continuation.availability(token, (datetime.now(UTC) + timedelta(days=2)).date())
    slot = available.slots[0]
    state = continuation.context(token)
    continuation.reserve(token, SlotSelection.model_validate({"expected_row_version": state["row_version"], "team_key": slot.team_key, "starts_at": slot.starts_at}))
    return continuation.readback(token)


def test_early_signed_receipt_can_bind_unknown_attempt_without_resending(recovery_context: RecoveryContext) -> None:
    context = recovery_context
    attempt = sent_attempt(context, uncertain=True)
    event = enqueue(context.sessions, context.settings, agency_id=context.actor.agency_id, provider="TWILIO_SMS",
        attempt_id=attempt.id, key="synthetic-delivered", kind="RECEIPT",
        data={"provider_reference": "SM" + "8" * 32, "status": "DELIVERED", "terminal": False})
    process_event(context.sessions, event)
    process_event(context.sessions, event)
    with context.sessions() as session:
        stored = session.get(RecoveryAttempt, attempt.id)
        assert stored.status == "DELIVERED" and stored.provider_reference == "SM" + "8" * 32
        assert session.get(RecoveryCase, context.case_id).status != "RECOVERED"
        assert session.scalar(select(func.count()).select_from(RecoveryAttempt).where(RecoveryAttempt.recovery_case_id == context.case_id)) == 1


def test_yes_is_deduplicated_and_creates_one_requested_link_not_a_call(recovery_context: RecoveryContext) -> None:
    context = recovery_context
    attempt = sent_attempt(context)
    payload = {"recipient_digest": attempt.recipient_digest, "body_fingerprint": "synthetic-yes"}
    event = enqueue(context.sessions, context.settings, agency_id=context.actor.agency_id,
        provider="TWILIO_SMS", key="synthetic-yes", kind="YES", data=payload)
    assert enqueue(context.sessions, context.settings, agency_id=context.actor.agency_id,
        provider="TWILIO_SMS", key="synthetic-yes", kind="YES", data=payload) == event
    process_event(context.sessions, event)
    process_event(context.sessions, event)
    with context.sessions() as session:
        grants = list(session.scalars(select(RecoveryGrant).where(RecoveryGrant.attempt_id == attempt.id)))
        assert len(grants) == 1 and grants[0].channel == "SMS" and grants[0].reply_status == "PENDING"
        assert session.get(RecoveryCase, context.case_id).paused
        assert session.get(RecoveryWebhook, event).processed_at is not None
    with pytest.raises(ApiError):
        enqueue(context.sessions, context.settings, agency_id=context.actor.agency_id,
            provider="TWILIO_SMS", key="synthetic-yes", kind="STOP", data=payload)


def test_pending_stop_blocks_customer_confirmation_before_inbox_processing(recovery_context: RecoveryContext) -> None:
    context = recovery_context
    continuation, token = active_booking(context)
    readback = reserve_and_read(context, continuation, token)
    enqueue(context.sessions, context.settings, agency_id=context.actor.agency_id, provider="TWILIO_SMS",
        key="synthetic-stop", kind="STOP", data={"recipient_digest": destination_digest(context.settings, context.actor.agency_id, "+12025550123")})
    with pytest.raises(ApiError):
        continuation.confirm(token, Confirmation.model_validate({"expected_row_version": readback["row_version"], "nonce": readback["nonce"], "explicit_confirmation": True}))
    with context.sessions() as session:
        assert session.scalar(select(Appointment.status).where(Appointment.service_request_id == context.request_id)) == "HELD"


def test_real_booking_service_consumes_attributed_grant_once(recovery_context: RecoveryContext) -> None:
    context = recovery_context
    continuation, token = active_booking(context)
    readback = reserve_and_read(context, continuation, token)
    confirmation = Confirmation.model_validate({"expected_row_version": readback["row_version"], "nonce": readback["nonce"], "explicit_confirmation": True})
    booked = continuation.confirm(token, confirmation)
    assert booked.status == "CONFIRMED"
    assert continuation.confirm(token, confirmation).id == booked.id
    assert continuation.context(token)["confirmed"] is True
    with context.sessions() as session:
        case = session.get(RecoveryCase, context.case_id)
        assert case.status == "RECOVERED" and case.recovered_appointment_id == booked.id
        grant = session.scalar(select(RecoveryGrant).where(RecoveryGrant.recovery_case_id == case.id))
        assert grant.status == "CONSUMED" and grant.approved_at is not None


def test_unknown_booking_confirmation_preserves_approval_and_original_selection(recovery_context: RecoveryContext) -> None:
    context = recovery_context
    continuation, token = active_booking(context)
    readback = reserve_and_read(context, continuation, token)
    confirmation = Confirmation.model_validate({"expected_row_version": readback["row_version"], "nonce": readback["nonce"], "explicit_confirmation": True})
    with patch.object(continuation.scheduling, "confirm", side_effect=ApiError(status_code=409,
            code="GHL_APPOINTMENT_CREATION_UNKNOWN", message="Synthetic uncertain write")):
        with pytest.raises(ApiError):
            continuation.confirm(token, confirmation)
    assert continuation.context(token)["approved_confirmation"] is not None
    with pytest.raises(ApiError):
        continuation.release(token)
    assert continuation.confirm(token, confirmation).status == "CONFIRMED"


def test_independent_confirmation_of_unapproved_hold_gets_no_recovery_credit(recovery_context: RecoveryContext) -> None:
    context = recovery_context
    continuation, token = active_booking(context)
    reserve_and_read(context, continuation, token)
    with context.sessions() as session:
        grant = session.scalar(select(RecoveryGrant).where(RecoveryGrant.recovery_case_id == context.case_id))
        appointment_id = grant.appointment_id
    SchedulingService(context.sessions).confirm(context.actor.agency_id, appointment_id, True, uuid4())
    with context.sessions() as session:
        case = session.get(RecoveryCase, context.case_id)
        assert case.status == "CLOSED" and case.recovered_appointment_id is None
    with pytest.raises(ApiError):
        continuation.context(token)


def test_expired_unapproved_continuation_releases_only_automation_pause(recovery_context: RecoveryContext) -> None:
    context = recovery_context
    attempt = sent_attempt(context)
    with context.sessions() as session, session.begin():
        grant = create_grant(session, attempt, active=True, expires_at=datetime.now(UTC) - timedelta(minutes=1))
        identifier = grant.id
        case = session.get(RecoveryCase, context.case_id)
        case.paused, case.reason = True, "CUSTOMER_CONTINUING_BOOKING"
    expire_continuation(context.sessions, identifier)
    with context.sessions() as session:
        assert session.get(RecoveryGrant, identifier).status == "EXPIRED"
        assert session.get(RecoveryCase, context.case_id).paused is False


def test_stop_between_saved_approval_and_booking_transaction_blocks_confirmation(recovery_context: RecoveryContext) -> None:
    context = recovery_context
    continuation, token = active_booking(context)
    readback = reserve_and_read(context, continuation, token)
    confirm = continuation.scheduling.confirm

    def concurrent_stop(agency_id: UUID, appointment_id: UUID, explicit_confirmation: bool, correlation_id: UUID) -> AppointmentView:
        enqueue(context.sessions, context.settings, agency_id=context.actor.agency_id, provider="TWILIO_SMS",
            key="synthetic-interleaved-stop", kind="STOP", data={"recipient_digest": destination_digest(context.settings, context.actor.agency_id, "+12025550123")})
        return confirm(agency_id, appointment_id, explicit_confirmation, correlation_id)

    with patch.object(continuation.scheduling, "confirm", side_effect=concurrent_stop):
        with pytest.raises(ApiError):
            continuation.confirm(token, Confirmation.model_validate({"expected_row_version": readback["row_version"], "nonce": readback["nonce"], "explicit_confirmation": True}))
    with context.sessions() as session:
        assert session.scalar(select(Appointment.status).where(Appointment.service_request_id == context.request_id)) == "HELD"


def test_database_rejects_grant_channel_mismatch_and_dispatch_rewrite(recovery_context: RecoveryContext) -> None:
    context = recovery_context
    attempt = sent_attempt(context)
    with pytest.raises(DBAPIError), context.sessions() as session, session.begin():
        session.add(RecoveryGrant(agency_id=context.actor.agency_id, attempt_id=attempt.id,
            recovery_case_id=context.case_id, channel="VOICE", status="WAITING", expires_at=datetime.now(UTC) + timedelta(minutes=5)))
        session.flush()
    with pytest.raises(DBAPIError), context.sessions() as session, session.begin():
        session.get(RecoveryAttempt, attempt.id).recipient_digest = "different-destination"
        session.flush()


def test_customer_yes_does_not_override_manual_staff_pause(recovery_context: RecoveryContext) -> None:
    context = recovery_context
    attempt = sent_attempt(context)
    with context.sessions() as session, session.begin():
        case = session.get(RecoveryCase, context.case_id)
        case.paused, case.reason = True, "MANUALLY_PAUSED"
    event = enqueue(context.sessions, context.settings, agency_id=context.actor.agency_id,
        provider="TWILIO_SMS", key="synthetic-paused-yes", kind="YES", data={"recipient_digest": attempt.recipient_digest})
    process_event(context.sessions, event)
    with context.sessions() as session:
        assert session.get(RecoveryCase, context.case_id).reason == "MANUALLY_PAUSED"
        assert session.scalar(select(RecoveryGrant.id).where(RecoveryGrant.attempt_id == attempt.id)) is None
        assert session.get(RecoveryWebhook, event).failure_code == "RECOVERY_PAUSED_BY_STAFF"
