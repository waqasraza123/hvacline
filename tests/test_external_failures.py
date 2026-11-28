import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context

import httpx
import pytest
from starlette.requests import Request

from insurance_operations.errors import ApiError, api_error_handler
from insurance_operations.external_failures import (
    ExternalFailure,
    collect_external_failures,
    current_external_failures,
    external_failure,
    provider_request,
    record_external_failure,
    record_provider_exception,
)


@pytest.mark.parametrize("status,payload,kind", [
    (402, {}, "billing"),
    (401, {}, "access"),
    (403, {}, "access"),
    (429, {}, "rate_limited"),
    (429, {"error": {"code": "insufficient_quota"}}, "billing"),
    (403, {"error": {"errors": [{"reason": "userRateLimitExceeded"}]}}, "rate_limited"),
    (504, {}, "timeout"),
    (503, {}, "unavailable"),
    (422, {}, "rejected"),
])
def test_provider_status_classification(status: int, payload: object, kind: str) -> None:
    assert external_failure("openai", status=status, payload=payload).kind == kind


def test_context_is_request_local_and_shared_with_sync_handler_threads() -> None:
    assert current_external_failures() == []
    with collect_external_failures():
        context = copy_context()
        with ThreadPoolExecutor(max_workers=1) as pool:
            pool.submit(context.run, record_external_failure, ExternalFailure("stripe", "access")).result()
        assert current_external_failures() == [{"provider": "stripe", "kind": "access"}]
        with collect_external_failures():
            record_external_failure(ExternalFailure("resend", "rate_limited"))
        assert len(current_external_failures()) == 2
    assert current_external_failures() == []


def test_observation_keeps_the_response_and_request_without_exposing_raw_data() -> None:
    def upstream(request: httpx.Request) -> httpx.Response:
        assert request.headers["Idempotency-Key"] == "synthetic-key"
        return httpx.Response(402, json={"error": {"message": "private-provider-body"}})

    with httpx.Client(transport=httpx.MockTransport(upstream)) as client:
        with collect_external_failures():
            response = provider_request("stripe", client, "POST", "https://api.stripe.com/test",
                headers={"Idempotency-Key": "synthetic-key"})
            assert response.status_code == 402
            assert current_external_failures() == [{"provider": "stripe", "kind": "billing"}]
        with collect_external_failures():
            provider_request("stripe", client, "POST", "https://api.stripe.com/test", ignored_statuses=frozenset({402}),
                headers={"Idempotency-Key": "synthetic-key"})
            assert current_external_failures() == []


def test_dependency_failure_does_not_relabel_an_ordinary_application_error() -> None:
    request = Request({"type": "http", "headers": [], "method": "GET", "path": "/"})
    with collect_external_failures():
        ordinary = asyncio.run(api_error_handler(request, ApiError(status_code=503, code="APP_UNAVAILABLE", message="Try later")))
        assert ordinary.status_code == 503
        assert b"external_failures" not in ordinary.body
        record_external_failure(ExternalFailure("telnyx", "access"))
        dependency = asyncio.run(api_error_handler(request, ApiError(status_code=503, code="DEMO_SMS_UNAVAILABLE", message="Try later")))
        assert dependency.status_code == 424
        assert b"telnyx" in dependency.body
        assert b"access" in dependency.body


def test_timeout_and_malformed_provider_payload_remain_distinct() -> None:
    with collect_external_failures():
        timeout = record_provider_exception("resend", httpx.ReadTimeout("private-error"))
        malformed = record_provider_exception("resend", ValueError("private-body"))
        assert timeout.code == "EXTERNAL_RESEND_TIMEOUT"
        assert malformed.code == "EXTERNAL_RESEND_REJECTED"
        assert current_external_failures() == [
            {"provider": "resend", "kind": "timeout"},
            {"provider": "resend", "kind": "rejected"},
        ]


def test_concurrent_async_requests_do_not_share_notifications() -> None:
    async def exercise(provider: str) -> list[dict[str, str]]:
        with collect_external_failures():
            if provider == "stripe":
                record_external_failure(ExternalFailure("stripe", "access"))
            await asyncio.sleep(0)
            return current_external_failures()

    async def requests() -> list[list[dict[str, str]]]:
        return list(await asyncio.gather(exercise("stripe"), exercise("resend")))

    assert asyncio.run(requests()) == [[{"provider": "stripe", "kind": "access"}], []]
