from dataclasses import dataclass, field
from typing import Literal, Protocol
from uuid import UUID


@dataclass(frozen=True)
class RecoveryContact:
    agency_id: UUID
    case_id: UUID
    request_id: UUID
    business_name: str
    phone: str
    idempotency_key: str
    attempt_id: UUID | None = None
    grant_token: str | None = field(default=None, repr=False)
    configuration: dict[str, object] | None = None


@dataclass(frozen=True)
class DeliveryOutcome:
    status: Literal["QUEUED", "SENT", "DELIVERED", "FAILED", "UNKNOWN"]
    provider_reference: str | None = None
    failure_code: str | None = None


class RecoveryDeliveryProvider(Protocol):
    def available(self, agency_id: UUID, channel: str) -> bool: ...
    def send(self, contact: RecoveryContact, channel: str) -> DeliveryOutcome: ...


class UnavailableRecoveryProvider:
    def available(self, agency_id: UUID, channel: str) -> bool:
        return False

    def send(self, contact: RecoveryContact, channel: str) -> DeliveryOutcome:
        return DeliveryOutcome("FAILED", failure_code="RECOVERY_PROVIDER_UNAVAILABLE")


def sms_message(business_name: str) -> str:
    return (f"Hi, this is {business_name}. You recently asked about HVAC service but didn't finish booking. "
        "Would you like help scheduling an appointment? Reply YES for help or STOP to opt out.")


VOICE_FIRST_MESSAGE = "Hi, this is the AI assistant for {{recovery_business_name}} calling about your unfinished HVAC service request. Would you like to continue scheduling?"

RECOVERY_VOICE_INSTRUCTIONS = """You are the AI recovery assistant for {{recovery_business_name}}.
Your first message identifies the business, AI disclosure and purpose. Wait for permission to continue.
Call recovery_continue only after an explicit yes. If declined, call recovery_finish with DECLINED and end_call.
For STOP or no more calls, use recovery_finish with STOP and end_call immediately.
After recovery_continue succeeds, recovery_context returns confirmed request details. Do not ask again for saved details.
If any saved details are wrong or missing, use recovery_finish with STAFF_REQUEST; never invent or overwrite them.
Call recovery_availability with a requested date and offer only returned available slots in the returned timezone.
Call recovery_reserve only for the customer's chosen slot, using the latest row_version. Holds are provisional.
Call recovery_readback, speak its exact full readback, then wait for the customer's explicit yes or confirm.
Only then call recovery_confirm with the returned nonce, row_version and explicit_confirmation=true.
Say confirmed only if that tool returns status CONFIRMED. Delivery, a hold or an unknown provider response is not a booking.
For a changed choice before approval, use recovery_release, then fetch availability again. For uncertain confirmation, refresh recovery_context; keep the same selection and nonce.
For hazards use recovery_finish with HAZARD and tell the caller to seek appropriate emergency help without promising a dispatch.
For staff assistance use recovery_finish with STAFF_REQUEST. Never promise a live transfer.
Never invent pricing, availability, technicians or service commitments. Do not use external tools, other agents, SMS or other phone numbers.
After confirmed booking or a finish action, end_call naturally. Tool failures require honest recovery/staff guidance; never claim success.
"""
