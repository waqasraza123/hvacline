from uuid import uuid4

import pytest
from pydantic import ValidationError

from insurance_operations.conversations.schemas import (
    ConversationIntakeConfirmationInput,
    ConversationTurn,
)
from insurance_operations.conversations.spoken import (
    intake_readback,
    require_spoken_confirmation,
)
from insurance_operations.hvac.schemas import ServiceRequestInput


def fictional_request() -> ServiceRequestInput:
    return ServiceRequestInput.model_validate(
        {
            "customer": {
                "full_name": "Fictional Caller",
                "phone": "+12025550123",
                "address": {
                    "line1": "123 Example Street",
                    "city": "New York",
                    "state_code": "NY",
                    "postal_code": "10001",
                },
            },
            "service": {
                "kind": "AC_REPAIR",
                "equipment_issue": "AC is not cooling",
                "preferred_window": "Tomorrow morning",
            },
            "explicit_confirmation": True,
        }
    )


@pytest.mark.parametrize("answer", ["Yes, save my request.", "Yes, that's correct."])
def test_spoken_intake_requires_readback_of_the_current_snapshot(answer: str) -> None:
    request = fictional_request()
    transcript = [
        ConversationTurn(speaker="AGENT", text=intake_readback(request)),
        ConversationTurn(speaker="USER", text=answer),
    ]
    values = {
        "conversation_session_id": uuid4(),
        "customer": request.customer,
        "service": request.service,
        "intake_intent": request.service.equipment_issue,
        "spoken_confirmation": True,
        "transcript": transcript,
    }
    assert ConversationIntakeConfirmationInput.model_validate(values).spoken_confirmation
    changed = request.customer.model_copy(update={"phone": "+12025550124"})
    with pytest.raises(ValidationError, match="complete current details"):
        ConversationIntakeConfirmationInput.model_validate(
            {**values, "customer": changed}
        )


@pytest.mark.parametrize(
    "answer",
    ["No", "Maybe", "Yes, but change my address", "Do not save this", ""],
)
def test_ambiguous_or_negative_answers_cannot_confirm(answer: str) -> None:
    readback = intake_readback(fictional_request())
    with pytest.raises(ValueError):
        require_spoken_confirmation(
            [
                ConversationTurn(speaker="AGENT", text=readback),
                ConversationTurn(speaker="USER", text=answer),
            ],
            readback,
        )


def test_a_different_question_after_readback_invalidates_consent() -> None:
    readback = intake_readback(fictional_request())
    with pytest.raises(ValueError, match="complete current details"):
        require_spoken_confirmation(
            [
                ConversationTurn(speaker="AGENT", text=readback),
                ConversationTurn(speaker="AGENT", text="Would you like a different time?"),
                ConversationTurn(speaker="USER", text="Yes"),
            ],
            readback,
        )
