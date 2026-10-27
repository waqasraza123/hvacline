import asyncio
from collections.abc import Iterator
from unittest.mock import MagicMock, Mock, patch

import httpx
import pytest
from pydantic import SecretStr, ValidationError
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from insurance_operations.booking_jobs import JobBatchResult, process_booking_jobs
from insurance_operations.job_api import create_job_app
from insurance_operations.job_execution import (
    DeadlineStream,
    DeadlineTransport,
    JobBudget,
    JobDeadlineExceeded,
    check_job_deadline,
    current_job_budget,
    job_budget,
)
from insurance_operations.settings import JobRunnerSettings


def job_settings() -> JobRunnerSettings:
    return JobRunnerSettings(
        _env_file=None,
        app_environment="test",
        database_url="postgresql://synthetic:synthetic@localhost/development",
        direct_database_url=None,
        test_database_url="postgresql://synthetic:synthetic@localhost/jobs_test",
        worker_name="synthetic-jobs",
        booking_jobs_secret=SecretStr("synthetic-job-secret-at-least-32-characters"),
        google_calendar_enabled=False,
        booking_email_enabled=False,
        booking_email_from=None,
    )


async def job_response(
    authorization: str | None,
    result: JobBatchResult | Exception,
    method: str = "POST",
) -> httpx.Response:
    with patch("insurance_operations.job_api.process_booking_jobs") as run:
        if isinstance(result, Exception):
            run.side_effect = result
        else:
            run.return_value = result
        app = create_job_app(job_settings(), MagicMock(spec=Engine))
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="https://jobs.example"
        ) as client:
            headers = {} if authorization is None else {"Authorization": authorization}
            response = await client.request(
                method, "/api/v1/internal/booking-jobs/run", headers=headers
            )
        if (
            authorization
            != "Bearer " + job_settings().booking_jobs_secret.get_secret_value()
            or method != "POST"
        ):
            run.assert_not_called()
        return response


@pytest.mark.parametrize(
    "authorization", [None, "", "Bearer incorrect", "Basic incorrect"]
)
def test_job_endpoint_rejects_unauthorized_requests(authorization: str | None) -> None:
    response = asyncio.run(job_response(authorization, JobBatchResult()))
    assert response.status_code == 401
    assert response.headers["Cache-Control"] == "no-store"


def test_job_endpoint_is_post_only_and_returns_sanitized_counts() -> None:
    token = "Bearer " + job_settings().booking_jobs_secret.get_secret_value()
    response = asyncio.run(job_response(token, JobBatchResult(processed=3)))
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert response.json() == {"status": "completed", "processed": 3, "failed": 0}
    assert asyncio.run(job_response(token, JobBatchResult(), "GET")).status_code == 405


def test_job_endpoint_hides_database_failure_and_can_retry() -> None:
    token = "Bearer " + job_settings().booking_jobs_secret.get_secret_value()

    async def retry() -> None:
        app = create_job_app(job_settings(), MagicMock(spec=Engine))
        with patch(
            "insurance_operations.job_api.process_booking_jobs",
            side_effect=[SQLAlchemyError("sensitive details"), JobBatchResult()],
        ):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="https://jobs.example"
            ) as client:
                headers = {"Authorization": token}
                response = await client.post(
                    "/api/v1/internal/booking-jobs/run", headers=headers
                )
                assert response.status_code == 503
                assert "sensitive" not in response.text
                assert response.headers["Retry-After"] == "60"
                response = await client.post(
                    "/api/v1/internal/booking-jobs/run", headers=headers
                )
                assert response.status_code == 200

    asyncio.run(retry())


@pytest.mark.parametrize("secret", ["", "short", "x" * 32 + "\n"])
def test_job_secret_rejects_weak_or_whitespace_values(secret: str) -> None:
    values = job_settings().model_dump()
    values["booking_jobs_secret"] = SecretStr(secret)
    with pytest.raises(ValidationError, match="BOOKING_JOBS_SECRET"):
        JobRunnerSettings.model_validate(values)


def test_overlapping_batch_does_not_collect_or_execute_jobs() -> None:
    sessions = MagicMock()
    sessions.return_value.__enter__.return_value.scalar.return_value = False
    with patch("insurance_operations.booking_jobs.collect_booking_jobs") as collect:
        assert process_booking_jobs(sessions) == JobBatchResult(status="busy")
    collect.assert_not_called()


def test_deadline_stops_batch_before_next_job_and_resets_context() -> None:
    sessions = MagicMock()
    sessions.return_value.__enter__.return_value.scalar.return_value = True
    first, later = Mock(side_effect=JobDeadlineExceeded), Mock()
    with patch(
        "insurance_operations.booking_jobs.collect_booking_jobs",
        return_value=[first, later],
    ):
        assert process_booking_jobs(sessions) == JobBatchResult(status="deferred")
    first.assert_called_once()
    later.assert_not_called()
    assert current_job_budget.get() is None


def test_failed_job_does_not_discard_following_work() -> None:
    sessions = MagicMock()
    first, later = Mock(side_effect=SQLAlchemyError), Mock()
    with patch(
        "insurance_operations.booking_jobs.collect_booking_jobs",
        return_value=[first, later],
    ):
        assert process_booking_jobs(sessions) == JobBatchResult(processed=1, failed=1)
    later.assert_called_once()


def test_expired_budget_prevents_new_provider_work() -> None:
    with (
        patch("insurance_operations.job_execution.monotonic", return_value=10),
        job_budget(1),
        patch("insurance_operations.job_execution.monotonic", return_value=12),
        pytest.raises(JobDeadlineExceeded),
    ):
        check_job_deadline()
    assert current_job_budget.get() is None


def test_provider_transport_limits_timeout_and_stops_before_expired_request() -> None:
    request = httpx.Request("GET", "https://provider.example")
    response = httpx.Response(200, stream=httpx.ByteStream(b"synthetic"))
    transport = DeadlineTransport(JobBudget(deadline=12))
    try:
        with (
            patch("insurance_operations.job_execution.monotonic", return_value=10),
            patch.object(httpx.HTTPTransport, "handle_request", return_value=response),
        ):
            actual = transport.handle_request(request)
        assert request.extensions["timeout"] == {
            "connect": 0.5,
            "read": 0.5,
            "write": 0.5,
            "pool": 0.5,
        }
        with (
            patch("insurance_operations.job_execution.monotonic", return_value=13),
            patch.object(httpx.HTTPTransport, "handle_request") as send,
        ):
            with pytest.raises(JobDeadlineExceeded):
                transport.handle_request(request)
            send.assert_not_called()
        actual.close()
    finally:
        transport.close()


def test_slow_stream_stops_at_deadline() -> None:
    clock = [0.0]

    class SlowStream(httpx.SyncByteStream):
        def __iter__(self) -> Iterator[bytes]:
            yield b"first"
            clock[0] = 3
            yield b"late"

    stream = DeadlineStream(SlowStream(), JobBudget(deadline=2))
    with patch(
        "insurance_operations.job_execution.monotonic", side_effect=lambda: clock[0]
    ):
        iterator = iter(stream)
        assert next(iterator) == b"first"
        with pytest.raises(JobDeadlineExceeded):
            next(iterator)
