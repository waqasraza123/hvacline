import logging

from pydantic import ValidationError

logger = logging.getLogger(__name__)

_FIELD_NAMES = frozenset(
    {
        "CallSid",
        "agent_id",
        "body",
        "call_id",
        "call_sid",
        "called_number",
        "caller_id",
        "conversation_id",
        "conversation_initiation_client_data",
        "data",
        "dynamic_variables",
        "event_timestamp",
        "inbound_call_id",
        "metadata",
        "phone_inbound_call_id",
        "sip_headers",
        "source_call_reference",
        "speaker",
        "text",
        "transcript",
        "type",
    }
)


def log_webhook_validation_failure(
    *,
    path: tuple[str | int, ...] = (),
    error_type: str = "value_error",
    error: ValidationError | None = None,
) -> None:
    fields = (
        [
            (path + tuple(item["loc"]), item["type"])
            for item in error.errors(
                include_url=False, include_context=False, include_input=False
            )[:20]
        ]
        if error is not None
        else [(path, error_type)]
    )
    safe_fields = []
    for location, kind in fields:
        safe_path = []
        for index, part in enumerate(location):
            safe_path.append(
                str(part) if isinstance(part, int) or part in _FIELD_NAMES else "*"
            )
            if part == "sip_headers" and index + 1 < len(location):
                safe_path.append("*")
                break
        safe_fields.append({"path": ".".join(safe_path) or "$", "type": kind})
    logger.warning("Phone webhook validation failed: %s", safe_fields)
