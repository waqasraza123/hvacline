from dataclasses import dataclass
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


RECOVERY_VOICE_INSTRUCTIONS = """Introduce the configured HVAC business and state that you are an AI assistant calling about their unfinished service request.
Ask whether they want to continue scheduling. Stop if they decline; record an opt-out if requested.
Retrieve only persisted, confirmed request details, and ask only for missing information.
Use the existing availability and reservation tools. Offer only returned slots.
Read back the selected date, time and service address, obtain explicit customer confirmation, then use the existing appointment confirmation tool.
Never invent pricing, availability, technicians or service commitments. End naturally or request staff handoff for hazards, unsupported requests or uncertainty.
"""
