import asyncio
from unittest.mock import MagicMock
from uuid import uuid4

from cryptography.fernet import Fernet
from fastapi import FastAPI
import httpx
import pytest
from pydantic import ValidationError

from insurance_operations.errors import ApiError
from insurance_operations.settings import ApiSettings
from insurance_operations.workspace.access import principal
from insurance_operations.workspace.routes import create_workspace_router
from insurance_operations.workspace.schemas import BusinessInput, EnrollmentInput, InvitationInput


@pytest.fixture(autouse=True)
def isolate_workspace_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ApiSettings.model_fields:
        monkeypatch.delenv(name.upper(), raising=False)


def settings(**overrides: object) -> ApiSettings:
    return ApiSettings(_env_file=None, **{
        "app_environment": "development", "api_host": "127.0.0.1", "api_port": 8000,
        "database_url": "postgresql://synthetic:synthetic@localhost/dev",
        "workspace_portal_enabled": True, "workspace_portal_secret": "synthetic-workspace-portal-key-at-least-32",
        "workspace_mfa_encryption_key": Fernet.generate_key().decode(),
        "workspace_bootstrap_token": "synthetic-workspace-bootstrap-key-at-least-32", **overrides,
    })


def test_workspace_configuration_requires_independent_security_keys() -> None:
    for overrides in (
        {"workspace_portal_secret": "short"}, {"workspace_mfa_encryption_key": "invalid"},
        {"workspace_bootstrap_token": "synthetic-workspace-portal-key-at-least-32"},
        {"demo_admin_token": "synthetic-workspace-portal-key-at-least-32"},
    ):
        with pytest.raises(ValidationError):
            settings(**overrides)


def test_invitation_inputs_reject_extra_privileges_and_weak_enrollment() -> None:
    with pytest.raises(ValidationError):
        EnrollmentInput(token="x" * 43, display_name="Fictional Staff", password="short")
    with pytest.raises(ValidationError):
        InvitationInput.model_validate({"email": "staff@example.com", "role": "OWNER", "agency_id": str(uuid4())})
    with pytest.raises(ValidationError):
        BusinessInput(creation_key=uuid4(), name="Business", slug="../wrong", owner_email="owner@example.com")


def test_missing_staff_token_never_falls_back_to_a_configured_development_actor() -> None:
    session = MagicMock()
    with pytest.raises(ApiError) as failure:
        principal(session, None)
    assert failure.value.status_code == 401
    session.execute.assert_not_called()


@pytest.mark.parametrize("enabled,headers,expected", [
    (False, {}, 404), (True, {}, 401),
    (True, {"X-Workspace-Portal-Key": "incorrect"}, 401),
    (True, {"X-Workspace-Portal-Key": "synthetic-workspace-portal-key-at-least-32"}, 401),
])
def test_staff_routes_gate_disabled_portal_and_missing_identity_before_data_access(enabled: bool, headers: dict[str, str], expected: int) -> None:
    sessions = MagicMock()
    app = FastAPI()
    from fastapi.responses import JSONResponse

    @app.exception_handler(ApiError)
    async def error_handler(_request: object, error: ApiError) -> JSONResponse:
        return JSONResponse({"error": {"message": error.message}}, status_code=error.status_code)

    app.include_router(create_workspace_router(settings(workspace_portal_enabled=enabled), sessions))

    async def get() -> int:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://example.com") as client:
            return (await client.get("/api/v1/workspace/auth/me", headers=headers)).status_code

    assert asyncio.run(get()) == expected
    if expected == 401 and headers.get("X-Workspace-Portal-Key") == "synthetic-workspace-portal-key-at-least-32":
        sessions.return_value.__enter__.return_value.execute.assert_not_called()
    else:
        sessions.assert_not_called()
