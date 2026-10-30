import pytest

from insurance_operations.errors import ApiError
from insurance_operations.telephony.phone_service import normalize_post_call


@pytest.mark.parametrize(
    ("event_type", "data", "path", "error_type"),
    [
        (
            "post_call_transcription",
            {},
            "data.conversation_initiation_client_data",
            "dict_type",
        ),
        (
            "post_call_transcription",
            {"conversation_initiation_client_data": {}},
            "data.conversation_initiation_client_data.dynamic_variables",
            "dict_type",
        ),
        (
            "post_call_transcription",
            {"conversation_initiation_client_data": {"dynamic_variables": {}}},
            "data.conversation_initiation_client_data.dynamic_variables."
            "phone_inbound_call_id",
            "missing",
        ),
        (
            "post_call_transcription",
            {
                "conversation_initiation_client_data": {
                    "dynamic_variables": {"phone_inbound_call_id": "private-uuid"}
                }
            },
            "data.conversation_initiation_client_data.dynamic_variables."
            "phone_inbound_call_id",
            "uuid_parsing",
        ),
        ("call_initiation_failure", {}, "data.metadata", "dict_type"),
        (
            "call_initiation_failure",
            {"metadata": {"type": "sip"}},
            "data.metadata.body",
            "dict_type",
        ),
        (
            "call_initiation_failure",
            {"metadata": {"type": "sip", "body": {}}},
            "data.metadata.body.call_sid",
            "missing",
        ),
        (
            "call_initiation_failure",
            {"metadata": {"type": "private-provider", "body": {}}},
            "data.metadata.type",
            "literal_error",
        ),
        (
            "call_initiation_failure",
            {"metadata": {"type": {}, "body": {}}},
            "data.metadata.type",
            "literal_error",
        ),
        (
            "call_initiation_failure",
            {"metadata": {"type": "sip", "body": {"call_sid": ""}}},
            "data.metadata.body.call_sid",
            "string_too_short",
        ),
        ("post_call_audio", {}, "type", "literal_error"),
    ],
)
def test_post_call_diagnostics_identify_the_failed_contract_without_values(
    caplog: pytest.LogCaptureFixture,
    event_type: str,
    data: dict[str, object],
    path: str,
    error_type: str,
) -> None:
    with pytest.raises(ApiError) as rejected:
        normalize_post_call(
            {
                "type": event_type,
                "event_timestamp": 1_786_550_400,
                "data": {
                    "conversation_id": "private-conversation",
                    "agent_id": "private-agent",
                    "transcript": [{"role": "user", "message": "private-message"}],
                    **data,
                },
            }
        )
    assert rejected.value.status_code == 422
    assert rejected.value.code == "PHONE_POST_CALL_EVENT_INVALID"
    assert rejected.value.details == {}
    assert len(caplog.records) == 1
    assert caplog.records[0].args == ([{"path": path, "type": error_type}],)
    assert caplog.records[0].exc_info is None
    assert "private" not in caplog.text


def test_documented_sip_failure_does_not_require_initiation_dynamic_variables(
    caplog: pytest.LogCaptureFixture,
) -> None:
    normalized = normalize_post_call(
        {
            "type": "call_initiation_failure",
            "event_timestamp": 1_786_550_400,
            "data": {
                "agent_id": "private-agent",
                "conversation_id": "private-conversation",
                "failure_reason": "unknown",
                "metadata": {
                    "type": "sip",
                    "body": {
                        "from_number": "+15559990002",
                        "to_number": "+15559990001",
                        "sip_status_code": 503,
                        "error_reason": "private-error-reason",
                        "call_sid": "private-sip-call-id",
                    },
                },
            },
        }
    )
    assert normalized.inbound_call_id is None
    assert normalized.source_adapter_name == "telnyx_sip"
    assert normalized.source_call_reference == "private-sip-call-id"
    assert not caplog.records
    assert "private-error-reason" not in normalized.model_dump_json()
    assert "+15559990002" not in normalized.model_dump_json()


def test_post_call_model_error_logs_no_transcript_or_exception(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with pytest.raises(ApiError):
        normalize_post_call(
            {
                "type": "post_call_transcription",
                "event_timestamp": 1_786_550_400,
                "data": {
                    "conversation_id": "private-conversation",
                    "conversation_initiation_client_data": {
                        "dynamic_variables": {
                            "phone_inbound_call_id": (
                                "00000000-0000-4000-8000-000000000010"
                            )
                        }
                    },
                    "transcript": [{"role": "user", "message": "private" * 300}],
                },
            }
        )
    assert len(caplog.records) == 1
    assert caplog.records[0].args == (
        [{"path": "data.transcript.0.text", "type": "string_too_long"}],
    )
    assert caplog.records[0].exc_info is None
    assert "private" not in caplog.text
