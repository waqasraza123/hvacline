from collections.abc import Iterator
from contextlib import contextmanager
from unittest.mock import patch

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from insurance_operations.ghl.demo import GhlDemoService, create_ghl_demo_router
from insurance_operations.ghl.provider import GhlClient
from insurance_operations.ghl.service import ProviderFactory
from insurance_operations.job_execution import JobDeadlineExceeded
from insurance_operations.settings import ApiSettings


def settings(**overrides: object) -> ApiSettings:
    values: dict[str, object] = {
        "app_environment": "development",
        "database_url": "postgresql://synthetic:synthetic@localhost/synthetic",
        "api_host": "127.0.0.1",
        "api_port": 8000,
        "ghl_enabled": False,
        "ghl_demo_enabled": True,
        "ghl_demo_fictional_data_only": True,
        "ghl_demo_location_id": "demo-location",
        "ghl_demo_private_integration_token": "synthetic-private-demo-token",
        "conversation_ai_enabled": False,
        "google_calendar_enabled": False,
        "booking_email_enabled": False,
    }
    return ApiSettings(_env_file=None, **{**values, **overrides})


def fixture_data() -> dict[str, object]:
    return {
        "pipelines": [
            {
                "id": "pipeline-one",
                "locationId": "demo-location",
                "name": "Fictional HVAC",
                "stages": [{"id": "stage-one", "name": "New request"}],
            }
        ],
        "opportunities": [
            {
                "id": "opportunity-one",
                "locationId": "demo-location",
                "pipelineId": "pipeline-one",
                "pipelineStageId": "stage-one",
                "status": "open",
                "name": "Private opportunity title",
                "contact": {"email": "private@example.invalid"},
                "customFields": [{"id": "field-one", "fieldValue": "Private field"}],
            }
        ],
        "meta": {"nextPage": ""},
    }


def factory(
    data: dict[str, object],
    requests: list[httpx.Request],
    status: int = 200,
) -> ProviderFactory:
    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if status != 200:
            return httpx.Response(status, headers={"Retry-After": "300"})
        result = (
            {"pipelines": data["pipelines"]}
            if request.url.path.endswith("/pipelines")
            else {"opportunities": data["opportunities"], "meta": data["meta"]}
        )
        return httpx.Response(200, json=result)

    @contextmanager
    def opened(token: str, location: str) -> Iterator[GhlClient]:
        with httpx.Client(transport=httpx.MockTransport(respond)) as client:
            yield GhlClient(client, token, location)

    return opened


@pytest.mark.parametrize(
    "overrides",
    [
        {"ghl_demo_fictional_data_only": False},
        {"ghl_demo_location_id": None},
        {"ghl_demo_location_id": "../foreign"},
        {"ghl_demo_private_integration_token": None},
        {"ghl_demo_private_integration_token": "short"},
        {"ghl_demo_private_integration_token": "invalid token with spaces"},
    ],
)
def test_public_demo_requires_explicit_fictional_scope_and_valid_credentials(
    overrides: dict[str, object],
) -> None:
    with pytest.raises(ValidationError) as failure:
        settings(**overrides)
    assert "synthetic-private-demo-token" not in str(failure.value)


def test_disabled_demo_never_uses_provider_credentials() -> None:
    requests: list[httpx.Request] = []
    service = GhlDemoService(
        settings(ghl_demo_enabled=False), factory(fixture_data(), requests)
    )
    assert service.read().state == "disabled"
    assert requests == []


def test_public_projection_excludes_contact_details_ids_titles_and_secrets() -> None:
    requests: list[httpx.Request] = []
    service = GhlDemoService(settings(), factory(fixture_data(), requests))
    view = service.read()
    assert view.state == "live"
    assert view.snapshot is not None
    assert view.snapshot.counts.loaded == 1
    assert view.snapshot.pipelines[0].stages[0].count == 1
    serialized = view.model_dump_json()
    for excluded in (
        "demo-location",
        "pipeline-one",
        "stage-one",
        "opportunity-one",
        "synthetic-private-demo-token",
        "private@example.invalid",
        "Private opportunity title",
        "Private field",
    ):
        assert excluded not in serialized
    assert len(requests) == 2
    for request in requests:
        assert request.method == "GET"
        assert request.url.host == "services.leadconnectorhq.com"
        assert request.url.params["locationId"] == "demo-location"
        assert request.headers["Version"] == "v3"
    assert requests[1].url.params["getNotes"] == "false"
    assert requests[1].url.params["getTasks"] == "false"
    assert requests[1].url.params["getCalendarEvents"] == "false"


@pytest.mark.parametrize(
    "kind", ["foreign", "stage", "duplicate", "status", "oversized"]
)
def test_invalid_remote_data_cannot_become_a_live_snapshot(kind: str) -> None:
    data = fixture_data()
    opportunity = {
        "id": "opportunity-one",
        "locationId": "foreign" if kind == "foreign" else "demo-location",
        "pipelineId": "pipeline-one",
        "pipelineStageId": "unknown" if kind == "stage" else "stage-one",
        "status": "invalid" if kind == "status" else "open",
    }
    data["opportunities"] = [opportunity] * (
        101 if kind == "oversized" else 2 if kind == "duplicate" else 1
    )
    service = GhlDemoService(settings(), factory(data, []))
    view = service.read()
    assert view.state == "unavailable"
    assert view.snapshot is None


def test_real_empty_response_is_live_with_zero_counts_and_no_fake_records() -> None:
    service = GhlDemoService(
        settings(), factory({"pipelines": [], "opportunities": [], "meta": {}}, [])
    )
    view = service.read()
    assert view.state == "live"
    assert view.snapshot is not None
    assert view.snapshot.counts.loaded == 0
    assert view.snapshot.pipelines == []


def test_cache_coalesces_reads_and_marks_previous_snapshot_on_failure() -> None:
    requests: list[httpx.Request] = []
    service = GhlDemoService(settings(), factory(fixture_data(), requests))
    with patch("insurance_operations.ghl.demo.monotonic", return_value=100):
        first = service.read()
        assert service.read() == first
    assert len(requests) == 2
    service.factory = factory(fixture_data(), requests, status=429)
    with patch("insurance_operations.ghl.demo.monotonic", return_value=161):
        failed = service.read()
    assert failed.state == "unavailable"
    assert failed.snapshot == first.snapshot
    with patch("insurance_operations.ghl.demo.monotonic", return_value=222):
        assert service.read() == failed
    assert len(requests) == 3


def test_public_route_does_not_authorize_writes_or_destination_overrides() -> None:
    requests: list[httpx.Request] = []
    configuration = settings()
    service = GhlDemoService(configuration, factory(fixture_data(), requests))
    application = FastAPI()
    application.include_router(create_ghl_demo_router(configuration, service))
    with TestClient(application) as client:
        result = client.get("/api/v1/public/ghl-demo?locationId=foreign")
        assert result.status_code == 200
        assert result.json()["state"] == "live"
        assert result.headers["Cache-Control"] == "no-store"
        for method in ("POST", "PUT", "PATCH", "DELETE"):
            assert client.request(method, "/api/v1/public/ghl-demo").status_code == 405
    assert all(
        request.url.params["locationId"] == "demo-location" for request in requests
    )


def test_inflight_refresh_cannot_start_another_provider_read() -> None:
    requests: list[httpx.Request] = []
    service = GhlDemoService(settings(), factory(fixture_data(), requests))
    with service.lock:
        assert service.read().state == "unavailable"
    assert requests == []


def test_provider_deadline_returns_unavailable_without_exposing_an_exception() -> None:
    service = GhlDemoService(settings(), factory(fixture_data(), []))
    with patch.object(service, "pull", side_effect=JobDeadlineExceeded):
        result = service.read()
    assert result.state == "unavailable"
    assert result.snapshot is None
