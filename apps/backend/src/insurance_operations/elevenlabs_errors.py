import re
from typing import Final

import httpx

ELEVENLABS_ACCOUNT_RESTRICTED: Final = "ELEVENLABS_ACCOUNT_RESTRICTED"

_ACCOUNT_CODES = frozenset({
    "insufficient_credits", "quota_exceeded", "payment_required", "payment_failed",
    "payment_not_verified", "payment_not_successful", "subscription_required",
    "account_restricted", "account_suspended", "access_restricted", "access_denied",
    "workspace_access_denied", "model_access_denied", "voice_access_denied",
    "authorization_error", "feature_not_available", "paid_plan_required",
    "detected_unusual_activity",
})
_ACCOUNT_CODE_PATTERN = re.compile(
    r"\b(?:" + "|".join(sorted(_ACCOUNT_CODES)) + r")\b", re.IGNORECASE
)
_ACCOUNT_MESSAGE = re.compile(
    r"(?:insufficient|not enough|no remaining|out of) (?:credits|quota)"
    r"|(?:credits|quota) (?:exhausted|exceeded|depleted)"
    r"|payment (?:failed|declined|not (?:verified|successful)|required)"
    r"|(?:account|access) (?:is |has been )?(?:restricted|denied|blocked|suspended)",
    re.IGNORECASE,
)


def elevenlabs_account_restricted(value: object, *, depth: int = 0) -> bool:
    if depth > 4:
        return False
    if isinstance(value, str):
        bounded = value[:8000]
        return bool(
            _ACCOUNT_CODE_PATTERN.search(bounded) or _ACCOUNT_MESSAGE.search(bounded)
        )
    if isinstance(value, dict):
        return any(
            elevenlabs_account_restricted(value.get(key), depth=depth + 1)
            for key in ("detail", "error", "error_event", "status", "code", "type", "message", "reason")
        )
    return False


def elevenlabs_response_restricted(response: httpx.Response) -> bool:
    if not response.is_error:
        return False
    if response.status_code in {402, 403}:
        return True
    try:
        return elevenlabs_account_restricted(response.json())
    except ValueError:
        return False


def elevenlabs_http_error_restricted(error: Exception) -> bool:
    return isinstance(error, httpx.HTTPStatusError) and elevenlabs_response_restricted(error.response)


def elevenlabs_error_details(restricted: bool) -> dict[str, str]:
    return {"provider_error_code": ELEVENLABS_ACCOUNT_RESTRICTED} if restricted else {}
