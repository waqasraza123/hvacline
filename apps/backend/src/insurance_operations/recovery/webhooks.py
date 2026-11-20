import re
from typing import Mapping
from uuid import UUID

from fastapi import APIRouter, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from starlette.concurrency import run_in_threadpool
from twilio.request_validator import RequestValidator

from insurance_operations.database.models.recovery import RecoveryAttempt, RecoveryGrant
from insurance_operations.errors import ApiError
from insurance_operations.recovery.domain import destination_digest
from insurance_operations.recovery.inbox import encrypt_recipient, enqueue, event_fingerprint
from insurance_operations.recovery.transports import SMS_STATUSES
from insurance_operations.settings import DatabaseSettings
from insurance_operations.telephony.contracts import TelephonyAdapterError
from insurance_operations.telephony.providers.elevenlabs import ElevenLabsPhoneProvider
from insurance_operations.telephony.providers.twilio import verified_form_parameters
from insurance_operations.conversations.spoken import normalized_speech

PREFIX = "/api/v1/providers/recovery"


def explicit_voice_opt_out(transcript: object) -> bool:
    if not isinstance(transcript, list) or len(transcript) > 120:
        return False
    accepted = {"stop", "stop calling", "stop calling me", "do not call me", "don t call me",
        "dont call me", "remove me from your list", "unsubscribe", "no more calls"}
    return any(isinstance(turn, dict) and turn.get("role") == "user" and isinstance(turn.get("message"), str)
        and len(turn["message"]) <= 8000 and normalized_speech(turn["message"]) in accepted for turn in transcript)


def rejected() -> ApiError:
    return ApiError(status_code=401, code="RECOVERY_WEBHOOK_REJECTED", message="Recovery webhook verification failed.", headers={"Cache-Control": "no-store"})


async def bounded_body(request: Request) -> bytes:
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > 262144:
            raise ApiError(status_code=413, code="RECOVERY_WEBHOOK_TOO_LARGE", message="Webhook payload exceeds its limit.")
    return bytes(body)


def twilio_form(settings: DatabaseSettings, path: str, headers: Mapping[str, str], body: bytes) -> dict[str, str]:
    if not settings.recovery_twilio_auth_token or not settings.recovery_twilio_account_sid or not settings.recovery_public_api_origin or not settings.recovery_agency_id:
        raise rejected()
    try:
        parameters = verified_form_parameters(request_validator=RequestValidator(settings.recovery_twilio_auth_token.get_secret_value()),
            expected_url=settings.recovery_public_api_origin.rstrip("/") + path, headers=headers, body=body)
    except TelephonyAdapterError:
        raise rejected() from None
    if parameters.get("AccountSid") != settings.recovery_twilio_account_sid or not re.fullmatch(r"SM[0-9a-fA-F]{32}", parameters.get("MessageSid", "")):
        raise rejected()
    return parameters


def record_status(settings: DatabaseSettings, sessions: sessionmaker[Session], identifier: UUID,
                  headers: Mapping[str, str], body: bytes, *, reply: bool) -> None:
    path = f"{PREFIX}/twilio/{'reply-status' if reply else 'status'}/{identifier}"
    parameters = twilio_form(settings, path, headers, body)
    with sessions() as session:
        grant = session.get(RecoveryGrant, identifier) if reply else None
        attempt = session.get(RecoveryAttempt, grant.attempt_id if grant else identifier)
        if (attempt is None or attempt.agency_id != settings.recovery_agency_id or attempt.provider != "TWILIO_SMS"
            or reply and (grant is None or grant.agency_id != attempt.agency_id)):
            raise rejected()
        configuration = attempt.dispatch_configuration or {}
        if configuration.get("account_sid") != parameters["AccountSid"] or configuration.get("api_origin") != settings.recovery_public_api_origin:
            raise rejected()
        if parameters.get("From") and parameters["From"] != configuration.get("from_number"):
            raise rejected()
        if parameters.get("To") and destination_digest(settings, attempt.agency_id, parameters["To"]) != attempt.recipient_digest:
            raise rejected()
        status = SMS_STATUSES.get(parameters.get("MessageStatus", ""))
        if status is None:
            return
        data: dict[str, object] = {"provider_reference": parameters["MessageSid"], "status": status,
            "terminal": False, "reply_grant_id": str(grant.id) if grant else None}
        enqueue(sessions, settings, agency_id=attempt.agency_id, provider="TWILIO_SMS", attempt_id=attempt.id,
            key=f"{parameters['MessageSid']}:{status}", kind="RECEIPT", data=data)


def record_incoming(settings: DatabaseSettings, sessions: sessionmaker[Session], headers: Mapping[str, str], body: bytes) -> None:
    parameters = twilio_form(settings, f"{PREFIX}/twilio/incoming", headers, body)
    phone = parameters.get("From", "")
    if parameters.get("To") != settings.recovery_sms_from_number or re.fullmatch(r"\+[1-9][0-9]{7,14}", phone) is None or settings.recovery_agency_id is None:
        raise rejected()
    text = parameters.get("Body", "").strip().upper()
    kind = "STOP" if parameters.get("OptOutType", "").upper() == "STOP" or text in {"STOP", "STOPALL", "UNSUBSCRIBE", "CANCEL", "END", "QUIT"} else "YES" if text == "YES" and parameters.get("NumMedia", "0") == "0" else "OTHER_REPLY"
    data: dict[str, object] = {"recipient_digest": destination_digest(settings, settings.recovery_agency_id, phone),
        "recipient_ciphertext": encrypt_recipient(settings, settings.recovery_agency_id, phone),
        "body_fingerprint": event_fingerprint(settings, parameters.get("Body", ""))}
    enqueue(sessions, settings, agency_id=settings.recovery_agency_id, provider="TWILIO_SMS",
        key=parameters["MessageSid"], kind=kind, data=data)


def record_voice(settings: DatabaseSettings, sessions: sessionmaker[Session], headers: Mapping[str, str], body: bytes) -> None:
    secret = settings.recovery_voice_webhook_secret
    if secret is None or settings.recovery_agency_id is None or settings.recovery_voice_agent_id is None:
        raise rejected()
    try:
        payload = ElevenLabsPhoneProvider(api_key=None, agent_id=settings.recovery_voice_agent_id,
            post_call_webhook_secret=secret.get_secret_value()).verify_post_call_webhook(headers=headers, body=body)
        data = payload["data"]
        if not isinstance(data, dict):
            raise ValueError
        reference = data["conversation_id"]
        if not isinstance(reference, str) or not 1 <= len(reference) <= 200:
            raise ValueError
        kind = payload.get("type")
        if kind not in {"post_call_transcription", "call_initiation_failure"}:
            raise ValueError
        variables = (data.get("conversation_initiation_client_data") or {}).get("dynamic_variables") or {}
        candidate = UUID(str(variables["recovery_attempt_id"])) if variables.get("recovery_attempt_id") else None
    except (TelephonyAdapterError, ValueError, TypeError, KeyError, AttributeError):
        raise rejected() from None
    with sessions() as session:
        attempt = session.scalar(select(RecoveryAttempt).where(RecoveryAttempt.agency_id == settings.recovery_agency_id,
            RecoveryAttempt.provider == "ELEVENLABS_RECOVERY", RecoveryAttempt.id == candidate if candidate else RecoveryAttempt.provider_reference == reference))
        if attempt:
            config = attempt.dispatch_configuration or {}
            if config.get("agent_id") != data.get("agent_id") or attempt.provider_reference and attempt.provider_reference != reference:
                raise rejected()
        opted_out = explicit_voice_opt_out(data.get("transcript"))
        safe = {"provider_reference": reference, "status": "FAILED" if kind == "call_initiation_failure" or data.get("status") == "failed" else "SENT", "terminal": True,
            "opt_out": opted_out}
        if opted_out and attempt and attempt.recipient_digest:
            enqueue(sessions, settings, agency_id=settings.recovery_agency_id, provider="ELEVENLABS_RECOVERY", attempt_id=attempt.id,
                key=f"{reference}:explicit-stop", kind="STOP", data={"recipient_digest": attempt.recipient_digest})
        enqueue(sessions, settings, agency_id=settings.recovery_agency_id, provider="ELEVENLABS_RECOVERY", attempt_id=attempt.id if attempt else None,
            key=f"{reference}:{kind}", kind="RECEIPT", data=safe)


def create_recovery_webhooks(settings: DatabaseSettings, sessions: sessionmaker[Session]) -> APIRouter:
    router = APIRouter(prefix=PREFIX, include_in_schema=False)

    @router.post("/twilio/status/{identifier}")
    async def status(identifier: UUID, request: Request) -> Response:
        if request.url.query:
            raise rejected()
        await run_in_threadpool(record_status, settings, sessions, identifier, dict(request.headers), await bounded_body(request), reply=False)
        return Response(status_code=204)

    @router.post("/twilio/reply-status/{identifier}")
    async def reply_status(identifier: UUID, request: Request) -> Response:
        if request.url.query:
            raise rejected()
        await run_in_threadpool(record_status, settings, sessions, identifier, dict(request.headers), await bounded_body(request), reply=True)
        return Response(status_code=204)

    @router.post("/twilio/incoming")
    async def incoming(request: Request) -> Response:
        if request.url.query:
            raise rejected()
        await run_in_threadpool(record_incoming, settings, sessions, dict(request.headers), await bounded_body(request))
        return Response(content="<Response/>", media_type="application/xml", headers={"Cache-Control": "no-store"})

    @router.post("/voice/webhook")
    async def voice(request: Request) -> dict[str, str]:
        await run_in_threadpool(record_voice, settings, sessions, dict(request.headers), await bounded_body(request))
        return {"status": "received"}

    return router
