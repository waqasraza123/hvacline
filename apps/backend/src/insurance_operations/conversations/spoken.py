import re
from collections.abc import Sequence
from typing import Protocol

from insurance_operations.hvac.schemas import ServiceRequestInput


class SpokenTurn(Protocol):
    @property
    def speaker(self) -> str: ...

    @property
    def text(self) -> str: ...


def normalized_speech(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.casefold()))


def require_spoken_confirmation(
    turns: Sequence[SpokenTurn], readback: str, action: str = "save my request"
) -> None:
    if len(turns) < 2 or turns[-1].speaker != "USER":
        raise ValueError("Read back the details and wait for the customer's answer")
    accepted = {
        "yes",
        "yes please",
        "yes that is correct",
        "yes thats correct",
        "yes that s correct",
        "yes correct",
        "confirm",
        "confirmed",
        "i confirm",
        "yes i confirm",
        f"yes {action}",
    }
    if normalized_speech(turns[-1].text) not in accepted:
        raise ValueError("A clear yes or confirm after the full readback is required")
    agent_turns: list[str] = []
    for turn in reversed(turns[:-1]):
        if turn.speaker != "AGENT":
            break
        agent_turns.insert(0, turn.text)
    if not normalized_speech(" ".join(agent_turns)).endswith(
        normalized_speech(readback)
    ):
        raise ValueError("Read the complete current details before asking for consent")


def intake_readback(request: ServiceRequestInput) -> str:
    customer = request.customer
    address = customer.address
    if address is None:
        raise ValueError("A complete service address is required")
    service = request.service
    email = (
        f" Email for booking confirmations and reminders: {customer.email}."
        if customer.email
        else ""
    )
    hazard = "reported" if service.hazardous_condition else "not reported"
    street = f"{address.line1}, {address.line2}" if address.line2 else address.line1
    readback = (
        f"Please confirm these details. Name: {customer.full_name}. "
        f"Callback number: {customer.phone}.{email} "
        f"Service address: {street}, {address.city}, "
        f"{address.state_code} {address.postal_code}, US. "
        f"Service: {service.kind.value.replace('_', ' ').lower()}. "
        f"Issue: {service.equipment_issue}. "
        f"Preferred appointment window: {service.preferred_window}. "
        f"Hazardous condition: {hazard}. "
        "May I save these details and the conversation transcript? "
        "Reply yes to save my request, or tell me what to correct."
    )
    if len(readback) > 1800:
        raise ValueError(
            "Shorten the issue description before reading back the request"
        )
    return readback
