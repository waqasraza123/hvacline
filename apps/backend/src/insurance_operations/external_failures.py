import json
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, Literal

import httpx

ExternalProvider = Literal[
    "elevenlabs", "stripe", "google_calendar", "gohighlevel", "resend",
    "telnyx", "twilio", "openai", "openai_compatible", "ollama",
]
ExternalFailureKind = Literal[
    "billing", "access", "rate_limited", "timeout", "unavailable", "rejected",
]
EXTERNAL_FAILURES_HEADER = "X-External-Failures"


@dataclass(frozen=True)
class ExternalFailure:
    provider: ExternalProvider
    kind: ExternalFailureKind

    def public(self) -> dict[str, str]:
        return {"provider": self.provider, "kind": self.kind}

    @property
    def code(self) -> str:
        return f"EXTERNAL_{self.provider.upper()}_{self.kind.upper()}"


_failures: ContextVar[list[ExternalFailure] | None] = ContextVar(
    "external_failures", default=None
)


@contextmanager
def collect_external_failures() -> Iterator[list[ExternalFailure]]:
    failures: list[ExternalFailure] = []
    parent = _failures.get()
    token = _failures.set(failures)
    try:
        yield failures
    finally:
        _failures.reset(token)
        if parent is not None:
            for failure in failures:
                record_external_failure(failure)


def current_external_failures() -> list[dict[str, str]]:
    return [failure.public() for failure in (_failures.get() or [])]


def record_external_failure(failure: ExternalFailure) -> ExternalFailure:
    failures = _failures.get()
    if failures is not None and failure not in failures and len(failures) < 8:
        failures.append(failure)
    return failure


def failure_tokens(value: object, depth: int = 0) -> set[str]:
    if depth > 5:
        return set()
    if isinstance(value, str):
        return {value.lower()} if len(value) < 100 else set()
    if isinstance(value, list):
        return set().union(*(failure_tokens(item, depth + 1) for item in value[:20]))
    if isinstance(value, dict):
        return set().union(*(
            failure_tokens(value.get(key), depth + 1)
            for key in ("error", "errors", "error_event", "detail", "code", "type", "reason", "status", "name")
        ))
    return set()


def external_failure(
    provider: ExternalProvider, *, status: int | None = None,
    payload: object = None, error: Exception | None = None,
) -> ExternalFailure:
    tokens = failure_tokens(payload)
    if status == 402 or tokens & {
        "insufficient_quota", "insufficient_credits", "credit_balance_exhausted",
        "billing_hard_limit_reached", "organization_spend_limit_exceeded",
        "payment_required", "payment_failed", "quota_exceeded",
        "payment_not_verified", "payment_not_successful", "subscription_required",
    }:
        kind: ExternalFailureKind = "billing"
    elif status == 429 or tokens & {
        "ratelimitexceeded", "userratelimitexceeded", "quotaexceeded",
        "dailylimitexceeded", "rate_limit_exceeded", "concurrent_limit_exceeded",
    }:
        kind = "rate_limited"
    elif status in {401, 403} or tokens & {
        "invalid_api_key", "invalid_grant", "access_denied", "account_restricted",
        "account_suspended", "access_restricted", "workspace_access_denied",
        "model_access_denied", "voice_access_denied", "authorization_error",
    }:
        kind = "access"
    elif status in {408, 504} or isinstance(error, (httpx.TimeoutException, TimeoutError)):
        kind = "timeout"
    elif status is None or status >= 500:
        kind = "unavailable"
    else:
        kind = "rejected"
    return ExternalFailure(provider, kind)


def response_failure(
    provider: ExternalProvider, response: httpx.Response,
) -> ExternalFailure:
    try:
        payload: object = response.json()
    except (ValueError, httpx.ResponseNotRead):
        payload = None
    return external_failure(provider, status=response.status_code, payload=payload)


def provider_request(
    provider: ExternalProvider, client: httpx.Client, method: str, url: str,
    *, ignored_statuses: frozenset[int] = frozenset(), **kwargs: Any,
) -> httpx.Response:
    try:
        response = client.request(method, url, **kwargs)
    except httpx.RequestError as error:
        record_external_failure(external_failure(provider, error=error))
        raise
    if response.status_code >= 300 and response.status_code not in ignored_statuses:
        record_external_failure(response_failure(provider, response))
    return response


@contextmanager
def provider_stream(
    provider: ExternalProvider, client: httpx.Client, method: str, url: str,
    **kwargs: Any,
) -> Iterator[httpx.Response]:
    try:
        with client.stream(method, url, **kwargs) as response:
            if response.status_code >= 300:
                record_external_failure(response_failure(provider, response))
            yield response
    except httpx.RequestError as error:
        record_external_failure(external_failure(provider, error=error))
        raise


def external_failures_header() -> str | None:
    failures = current_external_failures()
    return json.dumps(failures, separators=(",", ":")) if failures else None


def record_provider_exception(
    provider: ExternalProvider, error: Exception,
) -> ExternalFailure:
    if isinstance(error, httpx.HTTPStatusError):
        failure = response_failure(provider, error.response)
    elif isinstance(error, httpx.RequestError):
        failure = external_failure(provider, error=error)
    else:
        failure = ExternalFailure(provider, "rejected")
    return record_external_failure(failure)
