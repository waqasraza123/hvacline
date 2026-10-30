import secrets
from collections.abc import Mapping
from datetime import UTC, datetime

from pydantic import ValidationError

from insurance_operations.errors import ApiError
from insurance_operations.telephony.contracts import (
    PhoneCallInitialization,
    TelephonyAdapterError,
    TransferInstruction,
    VerifiedInboundCall,
    VerifiedTransferResult,
)
from insurance_operations.telephony.sip_schemas import (
    SipConversationInitiation,
    normalize_sip_phone_number,
)
from insurance_operations.telephony.webhook_validation import (
    log_webhook_validation_failure,
)

MAX_INITIATION_BYTES = 16_384


class TelnyxSipAdapter:
    adapter_name = "telnyx_sip"
    adapter_version = "1"

    def __init__(
        self, *, agent_id: str, initiation_secret: str, maximum_duration_seconds: int
    ) -> None:
        self._agent_id = agent_id
        self._initiation_secret = initiation_secret
        self._maximum_duration_seconds = maximum_duration_seconds

    def verify_authorization(self, authorization: str | None) -> None:
        scheme, _, supplied = (authorization or "").partition(" ")
        if scheme.casefold() != "bearer" or not secrets.compare_digest(
            supplied.encode("utf-8"), self._initiation_secret.encode("utf-8")
        ):
            raise ApiError(
                status_code=401,
                code="PHONE_INITIATION_REJECTED",
                message="The phone initiation request could not be authenticated",
            )

    def verify_initiation(
        self, *, headers: Mapping[str, str], body: bytes
    ) -> tuple[VerifiedInboundCall, PhoneCallInitialization]:
        authorization = next(
            (
                value
                for key, value in headers.items()
                if key.casefold() == "authorization"
            ),
            None,
        )
        self.verify_authorization(authorization)
        if len(body) > MAX_INITIATION_BYTES:
            raise ApiError(
                status_code=413,
                code="PHONE_INITIATION_TOO_LARGE",
                message="The phone initiation request is too large",
            )
        try:
            request = SipConversationInitiation.model_validate_json(body)
        except ValidationError as error:
            log_webhook_validation_failure(error=error)
            raise ApiError(
                status_code=422,
                code="PHONE_INITIATION_INVALID",
                message="The phone initiation request did not satisfy the SIP contract",
            ) from error
        if request.agent_id != self._agent_id:
            raise ApiError(
                status_code=403,
                code="PHONE_AGENT_REJECTED",
                message="The phone agent is not authorized for this integration",
            )
        try:
            caller_number = normalize_sip_phone_number(request.caller_id)
        except ValueError:
            caller_number = None
        return (
            VerifiedInboundCall(
                adapter_name=self.adapter_name,
                adapter_version=self.adapter_version,
                source_call_reference=(
                    request.call_id or f"conversation:{request.conversation_id}"
                ),
                called_number_e164=request.called_number,
                caller_number_e164=caller_number,
                occurred_at=datetime.now(UTC),
            ),
            PhoneCallInitialization(
                conversation_id=request.conversation_id,
                agent_id=request.agent_id,
                provider_call_id=request.call_id,
                maximum_duration_seconds=self._maximum_duration_seconds,
            ),
        )

    def verify_inbound_webhook(
        self, *, headers: Mapping[str, str], body: bytes
    ) -> VerifiedInboundCall:
        call, _ = self.verify_initiation(headers=headers, body=body)
        return call

    def request_transfer(
        self, *, source_call_reference: str, instruction: TransferInstruction
    ) -> None:
        raise TelephonyAdapterError(
            "SIP live transfer result verification is unavailable"
        )

    def verify_transfer_callback(
        self, *, headers: Mapping[str, str], body: bytes
    ) -> VerifiedTransferResult:
        raise TelephonyAdapterError(
            "SIP live transfer result verification is unavailable"
        )

    def close(self) -> None:
        return None
