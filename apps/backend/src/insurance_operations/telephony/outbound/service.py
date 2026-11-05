import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from typing import Any, Literal, cast
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.actors import ActorResolutionError, resolve_development_actor
from insurance_operations.database.models.identity import Agency
from insurance_operations.database.models.operations import AuditEvent
from insurance_operations.database.models.outbound_demo import OutboundDemoCall
from insurance_operations.errors import ApiError
from insurance_operations.settings import ApiSettings
from insurance_operations.telephony.outbound.destinations import validate_us_destination
from insurance_operations.telephony.outbound.provider import (
    ElevenLabsOutboundProvider,
    OutboundProviderError,
    object_value,
    transfer_outcome,
)
from insurance_operations.telephony.outbound.schemas import (
    MESSAGES,
    TERMINAL_STATUSES,
    DemoCallInput,
    DemoCallResponse,
    DemoCallStatus,
)
from insurance_operations.telephony.outbound.settings import OutboundDemoSettings


def unavailable() -> ApiError:
    return ApiError(
        status_code=503,
        code="OUTBOUND_DEMO_UNAVAILABLE",
        message="Telephone demos are unavailable. Please try browser Voice instead.",
    )


class OutboundDemoService:
    def __init__(
        self,
        sessions: sessionmaker[Session],
        api: ApiSettings,
        settings: OutboundDemoSettings,
        provider: ElevenLabsOutboundProvider,
    ) -> None:
        self.sessions = sessions
        self.api = api
        self.settings = settings
        self.provider = provider

    def _hash(self, purpose: str, value: str) -> str:
        secret = self.settings.outbound_demo_secret
        if secret is None:
            raise unavailable()
        return hmac.new(
            secret.get_secret_value().encode(),
            f"outbound-demo/v1/{purpose}:{value}".encode(),
            hashlib.sha256,
        ).hexdigest()

    def _agency(self, session: Session) -> UUID:
        if self.api.development_actor_user_id is None:
            raise unavailable()
        try:
            return resolve_development_actor(
                session, self.api.development_actor_user_id
            ).agency_id
        except ActorResolutionError as error:
            raise unavailable() from error

    def _owned(
        self, session: Session, call_id: UUID, owner: str | None, *, lock: bool = False
    ) -> OutboundDemoCall:
        query = select(OutboundDemoCall).where(
            OutboundDemoCall.id == call_id,
            OutboundDemoCall.agency_id == self._agency(session),
        )
        row = session.scalar(query.with_for_update() if lock else query)
        if row is None or (
            owner is not None
            and not hmac.compare_digest(row.owner_hash, self._hash("owner", owner))
        ):
            raise ApiError(
                status_code=404,
                code="DEMO_CALL_NOT_FOUND",
                message="This call request could not be found.",
            )
        return row

    def create(self, data: DemoCallInput, owner: str) -> DemoCallResponse:
        call_id, existing = self._reserve(data, owner)
        if existing is not None:
            return existing
        try:
            self.provider.preflight(data.phone_number)
            receipt = self.provider.dial(data, str(call_id))
        except OutboundProviderError as error:
            with self.sessions() as session, session.begin():
                row = self._owned(session, call_id, owner, lock=True)
                if row.status == DemoCallStatus.RESERVED:
                    row.status = (
                        DemoCallStatus.UNKNOWN
                        if error.outcome_unknown
                        else DemoCallStatus.FAILED
                    )
                    if not error.outcome_unknown:
                        row.finalized_at = datetime.now(UTC)
                return self._response(row)
        with self.sessions() as session, session.begin():
            row = self._owned(session, call_id, owner, lock=True)
            if (
                row.conversation_id is not None
                and row.conversation_id != receipt.conversation_id
            ):
                raise unavailable()
            row.conversation_id = receipt.conversation_id
            row.sip_call_id = receipt.sip_call_id
            if row.status == DemoCallStatus.RESERVED:
                row.status = DemoCallStatus.DIALING
            return self._response(row)

    def _reserve(
        self, data: DemoCallInput, owner: str
    ) -> tuple[UUID, DemoCallResponse | None]:
        if not self.settings.outbound_demo_enabled:
            raise unavailable()
        if owner != "admin" and not self.settings.website_available:
            raise unavailable()
        if self.settings.outbound_demo_number_policy == "consented_us":
            validate_us_destination(data.phone_number)
        elif data.phone_number not in self.settings.allowed_numbers:
            raise ApiError(
                status_code=403,
                code="DEMO_NUMBER_NOT_AUTHORIZED",
                message="This private demo is limited to numbers approved by the demo owner.",
            )
        now = datetime.now(UTC)
        fingerprint = self._hash("request", data.model_dump_json())
        destination = self._hash("destination", data.phone_number)
        owner_hash = self._hash("owner", owner)
        with self.sessions() as session, session.begin():
            agency_id = self._agency(session)
            session.execute(
                select(Agency.id).where(Agency.id == agency_id).with_for_update()
            ).scalar_one()
            existing = session.scalar(
                select(OutboundDemoCall).where(
                    OutboundDemoCall.agency_id == agency_id,
                    OutboundDemoCall.request_id == data.request_id,
                )
            )
            if existing is not None:
                if (
                    existing.request_hash != fingerprint
                    or existing.owner_hash != owner_hash
                ):
                    raise ApiError(
                        status_code=409,
                        code="DEMO_REQUEST_CONFLICT",
                        message="This request key was already used. Check its existing status.",
                    )
                return existing.id, self._response(existing)
            base = select(OutboundDemoCall).where(
                OutboundDemoCall.agency_id == agency_id
            )
            active = session.scalar(
                base.where(OutboundDemoCall.status.not_in(TERMINAL_STATUSES)).limit(1)
            )
            today = datetime.combine(now.date(), datetime.min.time(), tzinfo=UTC)
            daily = (
                session.scalar(
                    select(func.count()).select_from(
                        base.where(OutboundDemoCall.created_at >= today).subquery()
                    )
                )
                or 0
            )
            number_daily = (
                session.scalar(
                    select(func.count()).select_from(
                        base.where(
                            OutboundDemoCall.destination_hash == destination,
                            OutboundDemoCall.created_at >= now - timedelta(days=1),
                        ).subquery()
                    )
                )
                or 0
            )
            recent = session.scalar(
                base.where(
                    OutboundDemoCall.created_at
                    >= now
                    - timedelta(seconds=self.settings.outbound_demo_cooldown_seconds)
                ).limit(1)
            )
            if (
                active is not None
                or recent is not None
                or daily >= self.settings.outbound_demo_daily_limit
                or number_daily >= self.settings.outbound_demo_number_daily_limit
            ):
                raise ApiError(
                    status_code=429,
                    code="DEMO_CALL_LIMIT",
                    message=(
                        "The demo call limit has been reached. Please try browser Voice."
                    ),
                )
            row = OutboundDemoCall(
                agency_id=agency_id,
                request_id=data.request_id,
                owner_hash=owner_hash,
                destination_hash=destination,
                request_hash=fingerprint,
                scenario=data.scenario.value,
                consent_version=data.consent_version,
                consent_at=now,
                created_at=now,
                status=DemoCallStatus.RESERVED,
                transfer_status="not_requested",
            )
            session.add(row)
            session.flush()
            self._audit(session, row, "OUTBOUND_DEMO_RESERVED", owner == "admin")
            return row.id, None

    def get(self, call_id: UUID, owner: str | None) -> DemoCallResponse:
        with self.sessions() as session:
            return self._response(self._owned(session, call_id, owner))

    def get_request(self, request_id: UUID, owner: str) -> DemoCallResponse:
        with self.sessions() as session:
            row = session.scalar(
                select(OutboundDemoCall).where(
                    OutboundDemoCall.agency_id == self._agency(session),
                    OutboundDemoCall.request_id == request_id,
                    OutboundDemoCall.owner_hash == self._hash("owner", owner),
                )
            )
            if row is None:
                raise ApiError(
                    status_code=404,
                    code="DEMO_CALL_NOT_FOUND",
                    message="The request is not yet available. Do not request another call; contact the demo owner.",
                )
            return self._response(row)

    def refresh(self, call_id: UUID) -> DemoCallResponse:
        with self.sessions() as session:
            row = self._owned(session, call_id, None)
            conversation_id = row.conversation_id
        if conversation_id is None:
            return self.get(call_id, None)
        try:
            data = self.provider.conversation(conversation_id)
        except OutboundProviderError as error:
            raise unavailable() from error
        self.apply_provider_data(data, event_type="refresh", fingerprint=None)
        return self.get(call_id, None)

    def carrier_ended(self, call_id: UUID) -> DemoCallResponse:
        with self.sessions() as session, session.begin():
            row = self._owned(session, call_id, None, lock=True)
            if row.status not in TERMINAL_STATUSES:
                row.status = DemoCallStatus.DISCONNECTED
                row.finalized_at = datetime.now(UTC)
                self._audit(session, row, "OUTBOUND_DEMO_CARRIER_END_CONFIRMED", True)
            return self._response(row)

    def _audit(
        self, session: Session, row: OutboundDemoCall, event: str, admin: bool
    ) -> None:
        session.add(
            AuditEvent(
                agency_id=row.agency_id,
                actor_type="STAFF" if admin else "SYSTEM",
                actor_user_id=self.api.development_actor_user_id if admin else None,
                event_type=event,
                occurred_at=datetime.now(UTC),
                summary=event,
                details={"outbound_demo_call_id": str(row.id)},
                correlation_id=uuid4(),
                event_version=1,
            )
        )

    def webhook(self, payload: dict[str, object]) -> None:
        kind = payload.get("type")
        if not isinstance(kind, str) or kind not in {
            "post_call_transcription",
            "call_initiation_failure",
        }:
            raise ApiError(
                status_code=422,
                code="DEMO_EVENT_INVALID",
                message="Unsupported demo call event.",
            )
        data = object_value(payload.get("data"))
        # Store only a digest; provider transcripts, phone numbers and errors stay out of this table.
        fingerprint = self._hash(
            "event", json.dumps(payload, sort_keys=True, separators=(",", ":"))
        )
        self.apply_provider_data(data, event_type=str(kind), fingerprint=fingerprint)

    def apply_provider_data(
        self, data: dict[str, Any], *, event_type: str, fingerprint: str | None
    ) -> None:
        conversation_id = data.get("conversation_id")
        if data.get(
            "agent_id"
        ) != self.settings.outbound_demo_agent_id or not isinstance(
            conversation_id, str
        ):
            raise ApiError(
                status_code=422,
                code="DEMO_EVENT_INVALID",
                message="Invalid demo call identity.",
            )
        variables = object_value(
            object_value(data.get("conversation_initiation_client_data")).get(
                "dynamic_variables"
            )
        )
        metadata = object_value(data.get("metadata"))
        provider_status = data.get("status")
        duration = metadata.get("call_duration_secs", 0)
        if (
            (provider_status is not None and not isinstance(provider_status, str))
            or type(duration) is not int
            or duration < 0
            or not isinstance(data.get("transcript", []), list)
            or (
                event_type == "post_call_transcription"
                and provider_status not in {"done", "failed"}
            )
        ):
            raise ApiError(
                status_code=422,
                code="DEMO_EVENT_INVALID",
                message="Invalid demo call lifecycle.",
            )
        try:
            observed_transfer = transfer_outcome(
                data, self.settings.outbound_demo_human_number.get_secret_value()
            )
        except ValueError as error:
            raise ApiError(
                status_code=422,
                code="DEMO_EVENT_INVALID",
                message="Invalid demo call transcript.",
            ) from error
        with self.sessions() as session, session.begin():
            agency_id = self._agency(session)
            # The same tenant lock serializes webhook binding against new reservations.
            session.execute(
                select(Agency.id).where(Agency.id == agency_id).with_for_update()
            ).scalar_one()
            row = session.scalar(
                select(OutboundDemoCall)
                .where(
                    OutboundDemoCall.agency_id == agency_id,
                    OutboundDemoCall.conversation_id == conversation_id,
                )
                .with_for_update()
            )
            if row is None:
                try:
                    call_id = UUID(str(variables.get("outbound_demo_call_id", "")))
                except ValueError:
                    call_id = None
                if call_id is not None:
                    row = session.scalar(
                        select(OutboundDemoCall)
                        .where(
                            OutboundDemoCall.agency_id == agency_id,
                            OutboundDemoCall.id == call_id,
                            OutboundDemoCall.conversation_id.is_(None),
                        )
                        .with_for_update()
                    )
            if row is None:
                # Retryable: the provider can finish before its outbound HTTP response arrives.
                raise ApiError(
                    status_code=503,
                    code="DEMO_EVENT_UNBOUND",
                    message="The outbound receipt has not yet been bound.",
                )
            if row.status in TERMINAL_STATUSES or (
                fingerprint is not None and row.last_event_hash == fingerprint
            ):
                return
            row.conversation_id = conversation_id
            if event_type == "call_initiation_failure":
                if (
                    row.status
                    in {
                        DemoCallStatus.IN_PROGRESS,
                        DemoCallStatus.PROCESSING,
                    }
                    or row.transfer_status != "not_requested"
                ):
                    return
                body = object_value(metadata.get("body"))
                code = (
                    body.get("sip_status_code")
                    if metadata.get("type") == "sip"
                    else None
                )
                if type(code) is not int:
                    code = None
                row.status = (
                    DemoCallStatus.REJECTED
                    if code in {486, 600, 603}
                    else DemoCallStatus.UNANSWERED
                    if code in {408, 480}
                    else DemoCallStatus.FAILED
                )
            elif event_type == "post_call_transcription" or provider_status in {
                "done",
                "failed",
            }:
                if row.transfer_status not in {"refer_accepted", "unconfirmed"} or (
                    observed_transfer == "refer_accepted"
                ):
                    row.transfer_status = observed_transfer
                if row.transfer_status in {"refer_accepted", "unconfirmed"}:
                    row.status = DemoCallStatus.UNKNOWN
                elif provider_status == "failed" or metadata.get("error"):
                    row.status = (
                        DemoCallStatus.DISCONNECTED
                        if duration > 0
                        else DemoCallStatus.FAILED
                    )
                elif (
                    "disconnect"
                    in str(metadata.get("termination_reason", "")).casefold()
                ):
                    row.status = DemoCallStatus.DISCONNECTED
                else:
                    row.status = DemoCallStatus.COMPLETED
            elif row.status != DemoCallStatus.UNKNOWN:
                next_status = {
                    "initiated": DemoCallStatus.DIALING,
                    "in-progress": DemoCallStatus.IN_PROGRESS,
                    "processing": DemoCallStatus.PROCESSING,
                }.get(provider_status, DemoCallStatus.UNKNOWN)
                order = [
                    DemoCallStatus.RESERVED,
                    DemoCallStatus.DIALING,
                    DemoCallStatus.IN_PROGRESS,
                    DemoCallStatus.PROCESSING,
                    DemoCallStatus.UNKNOWN,
                ]
                if order.index(next_status) > order.index(DemoCallStatus(row.status)):
                    row.status = next_status
            row.last_event_hash = fingerprint
            if row.status in TERMINAL_STATUSES:
                row.finalized_at = datetime.now(UTC)

    @staticmethod
    def _response(row: OutboundDemoCall) -> DemoCallResponse:
        status = DemoCallStatus(row.status)
        message = MESSAGES[status]
        if row.transfer_status == "refer_accepted":
            message += " A transfer was accepted by SIP; a human answer is unconfirmed."
        elif row.transfer_status == "failed":
            message += " The human transfer failed."
        elif row.transfer_status == "unconfirmed":
            message += " The human transfer outcome is unconfirmed."
        return DemoCallResponse(
            id=row.id,
            status=status,
            transfer_status=cast(
                Literal["not_requested", "refer_accepted", "failed", "unconfirmed"],
                row.transfer_status,
            ),
            created_at=row.created_at,
            terminal=status in TERMINAL_STATUSES,
            message=message,
        )
