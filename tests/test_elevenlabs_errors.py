import httpx
import pytest

from insurance_operations.elevenlabs_errors import elevenlabs_response_restricted


@pytest.mark.parametrize(
    "status,payload,restricted",
    [
        (402, {}, True),
        (403, {}, True),
        (401, {"detail": {"status": "quota_exceeded"}}, True),
        (400, {"error": {"code": "insufficient_credits"}}, True),
        (400, {"detail": {"message": "Payment not successful"}}, True),
        (401, {"detail": {"status": "account_restricted"}}, True),
        (401, {"detail": {"status": "invalid_api_key"}}, False),
        (429, {"detail": {"status": "rate_limit_exceeded"}}, False),
        (429, {"detail": {"status": "concurrent_limit_exceeded"}}, False),
        (500, {"detail": {"message": "Provider unavailable"}}, False),
        (200, {"detail": {"status": "insufficient_credits"}}, False),
    ],
)
def test_maps_only_upstream_account_restrictions(
    status: int, payload: dict[str, object], restricted: bool
) -> None:
    assert elevenlabs_response_restricted(httpx.Response(status, json=payload)) is restricted


def test_unreadable_provider_errors_remain_generic() -> None:
    assert not elevenlabs_response_restricted(httpx.Response(502, text="bad gateway"))
