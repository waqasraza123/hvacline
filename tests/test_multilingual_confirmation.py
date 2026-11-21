from datetime import UTC, datetime
import hashlib
import json
from uuid import uuid4

import pytest

from insurance_operations.conversations.booking import appointment_readback
from insurance_operations.conversations.schemas import ConversationIntakeConfirmationInput, ConversationTurn
from insurance_operations.conversations.service import request_fingerprint
from insurance_operations.conversations.spoken import intake_readback, require_spoken_confirmation
from insurance_operations.hvac.schemas import AppointmentView, ServiceRequestInput
from insurance_operations.voice_languages import LanguageCode


def request() -> ServiceRequestInput:
    return ServiceRequestInput.model_validate({
        "customer": {"full_name": "Fictional Caller", "phone": "+12025550123", "address": {
            "line1": "14 Example Lane", "city": "New York", "state_code": "NY", "postal_code": "10001"}},
        "service": {"kind": "AC_REPAIR", "equipment_issue": "AC cooling नहीं कर रहा", "preferred_window": "2026-11-25 afternoon"},
        "explicit_confirmation": True,
    })


@pytest.mark.parametrize(("language", "yes"), [("es", "Sí"), ("fr", "Oui"), ("ar", "نعم"), ("hi", "हाँ"), ("zh", "我确认"), ("ur", "جی ہاں")])
def test_localized_confirmation_preserves_exact_details_and_rejects_corrections(language: LanguageCode, yes: str) -> None:
    value = request()
    readback = intake_readback(value, language)
    for exact in (value.customer.full_name, value.customer.phone, "14 Example Lane", "NY 10001", value.service.equipment_issue):
        assert exact is not None and exact in readback
    turns = [ConversationTurn(speaker="AGENT", text=readback), ConversationTurn(speaker="USER", text=yes)]
    require_spoken_confirmation(turns, readback, language=language)
    for reply in (yes + " but change the date", "maybe", "no", "", "yes", "نعم لا"):
        with pytest.raises(ValueError):
            require_spoken_confirmation([turns[0], ConversationTurn.model_construct(speaker="USER", text=reply)], readback, language=language)
    changed = value.model_copy(update={"customer": value.customer.model_copy(update={"full_name": "Corrected Fictional Name"})})
    with pytest.raises(ValueError):
        require_spoken_confirmation(turns, intake_readback(changed, language), language=language)


def test_language_change_between_readback_and_answer_requires_new_readback() -> None:
    value = request()
    with pytest.raises(ValueError):
        require_spoken_confirmation([
            ConversationTurn(speaker="AGENT", text=intake_readback(value)),
            ConversationTurn(speaker="USER", text="Can we speak Spanish?"),
            ConversationTurn(speaker="AGENT", text="Claro."),
            ConversationTurn(speaker="USER", text="Sí"),
        ], intake_readback(value, "es"), language="es")


def test_localized_appointment_uses_business_timezone_and_preserves_underlying_time() -> None:
    instant = datetime(2026, 11, 25, 19, 0, tzinfo=UTC)
    appointment = AppointmentView.model_construct(starts_at=instant)
    readback = appointment_readback(appointment, "America/New_York", "es")
    assert "2026-11-25 14:00" in readback
    assert "America/New_York" in readback
    assert appointment.starts_at == instant


def test_default_english_retains_the_existing_intake_idempotency_fingerprint() -> None:
    value = request()
    data = ConversationIntakeConfirmationInput(
        conversation_session_id=uuid4(), customer=value.customer,
        service=value.service, intake_intent=value.service.equipment_issue,
        transcript=[ConversationTurn(speaker="AGENT", text="Fictional question"), ConversationTurn(speaker="USER", text="Fictional answer")],
    )
    legacy = json.dumps(data.model_dump(mode="json", exclude={"readback_language"}), sort_keys=True, separators=(",", ":"))
    assert request_fingerprint(data) == hashlib.sha256(legacy.encode()).hexdigest()
    assert request_fingerprint(data.model_copy(update={"readback_language": "es"})) != request_fingerprint(data)
