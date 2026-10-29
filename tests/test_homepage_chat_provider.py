import json
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from insurance_operations.conversations.contracts import ConnectionGrant
from insurance_operations.conversations.providers.elevenlabs import (
    ElevenLabsConversationProvider,
)
from insurance_operations.homepage_chat.provider import (
    ElevenLabsHomepageProvider,
    HomepageProviderError,
)
from insurance_operations.homepage_chat.schemas import HomepageChatInput


def event(kind: str, **values: object) -> str:
    return json.dumps({"type": kind, **values})


def run_provider(
    events: list[str | Exception],
) -> tuple[str, list[dict[str, object]], MagicMock]:
    socket = MagicMock()
    socket.recv.side_effect = events
    socket.__enter__.return_value = socket
    lookup = MagicMock(
        return_value='{"matched":true,"approved_answer":"We handle AC repair."}'
    )
    with (
        patch.object(
            ElevenLabsConversationProvider,
            "authorize_session",
            return_value=MagicMock(
                spec=ConnectionGrant,
                credential="wss://api.elevenlabs.io/v1/convai/conversation?test=true",
            ),
        ),
        patch(
            "insurance_operations.homepage_chat.provider.connect", return_value=socket
        ),
    ):
        reply = ElevenLabsHomepageProvider("test-key", "test-agent").reply(
            "Can you help with AC repair?", lookup
        )
    return (
        reply,
        [json.loads(call.args[0]) for call in socket.send.call_args_list],
        lookup,
    )


def test_guest_ignores_greeting_and_allows_only_faq_tools() -> None:
    reply, sent, lookup = run_provider(
        [
            event("conversation_initiation_metadata"),
            event(
                "agent_response",
                agent_response_event={"agent_response": "Initial greeting"},
            ),
            event("agent_response_complete"),
            event("ping", ping_event={"event_id": 7}),
            event(
                "client_tool_call",
                client_tool_call={
                    "tool_name": "lookup_approved_faq",
                    "tool_call_id": "faq-1",
                    "parameters": {"query": "AC repair"},
                },
            ),
            event(
                "client_tool_call",
                client_tool_call={
                    "tool_name": "confirm_appointment",
                    "tool_call_id": "booking-1",
                    "parameters": {"explicit_confirmation": True},
                },
            ),
            event(
                "agent_response",
                agent_response_event={
                    "agent_response": "We handle AC repair. Sign in when you are ready to book."
                },
            ),
            event("agent_response_complete"),
        ]
    )
    assert reply == "We handle AC repair. Sign in when you are ready to book."
    assert sent[0]["dynamic_variables"] == {"homepage_guest": True}
    assert len([item for item in sent if item["type"] == "user_message"]) == 1
    lookup.assert_called_once_with("AC repair")
    rejected = [item for item in sent if item.get("tool_call_id") == "booking-1"]
    assert rejected[0]["is_error"] is True
    assert "SIGN_IN_REQUIRED" in str(rejected[0]["result"])


@pytest.mark.parametrize("message_sent", [False, True])
def test_provider_failure_reports_whether_generation_may_have_started(
    message_sent: bool,
) -> None:
    events: list[str | Exception] = [event("conversation_initiation_metadata")]
    if message_sent:
        events.append(event("agent_response_complete"))
    events.append(TimeoutError())
    with pytest.raises(HomepageProviderError) as failure:
        run_provider(events)
    assert failure.value.message_sent is message_sent


@pytest.mark.parametrize(
    "message,accepted", [("   ", True), ("x" * 1001, True), ("Hello", False)]
)
def test_guest_input_requires_a_bounded_message_and_explicit_disclosure(
    message: str, accepted: bool
) -> None:
    with pytest.raises(ValidationError):
        HomepageChatInput.model_validate(
            {
                "message": message,
                "request_id": "00000000-0000-4000-8000-000000000001",
                "ai_disclosure_accepted": accepted,
            }
        )
