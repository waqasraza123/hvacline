from unittest.mock import patch
from uuid import uuid4

from cryptography.fernet import Fernet
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.orm import sessionmaker

from insurance_operations.actors import ActorContext
from insurance_operations.errors import ApiError, api_error_handler
from insurance_operations.ghl.provider import GhlError
from insurance_operations.ghl.routes import create_ghl_router
from insurance_operations.ghl.service import GhlService
from insurance_operations.settings import ApiSettings


def app() -> tuple[FastAPI, GhlService]:
    settings = ApiSettings.model_validate(
        {
            "app_environment": "development",
            "database_url": "postgresql://synthetic:synthetic@localhost/synthetic",
            "web_origin": "http://localhost:3000",
            "ghl_enabled": True,
            "ghl_token_encryption_key": SecretStr(Fernet.generate_key().decode()),
            "demo_sandbox_enabled": False,
            "demo_admin_token": SecretStr("synthetic-administrator-token-long-enough"),
            "conversation_ai_enabled": False,
        }
    )
    actor = ActorContext(
        uuid4(), "Synthetic owner", uuid4(), "Synthetic business", "DEVELOPMENT"
    )
    service = GhlService(sessionmaker(), settings)
    application = FastAPI()

    @application.exception_handler(ApiError)
    async def error_handler(request: Request, error: ApiError) -> JSONResponse:
        return await api_error_handler(request, error)

    application.include_router(
        create_ghl_router(settings, sessionmaker(), lambda: actor, service)
    )
    return application, service


def test_ghl_always_requires_admin_token_even_with_sandbox_gate_disabled() -> None:
    application, service = app()
    with patch.object(
        service, "status", return_value={"enabled": True, "connection": None}
    ) as status:
        with TestClient(application) as client:
            assert client.get("/api/v1/development/integrations/ghl").status_code == 401
            assert (
                client.get(
                    "/api/v1/development/integrations/ghl",
                    headers={"X-Demo-Admin-Token": "wrong"},
                ).status_code
                == 401
            )
            status.assert_not_called()
            response = client.get(
                "/api/v1/development/integrations/ghl",
                headers={
                    "X-Demo-Admin-Token": "synthetic-administrator-token-long-enough"
                },
            )
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"


def test_provider_failures_return_safe_codes_without_token_or_provider_content() -> (
    None
):
    application, service = app()
    with patch.object(
        service,
        "discover",
        side_effect=GhlError("GHL_AUTH_REQUIRED", connection_error=True),
    ):
        with TestClient(application) as client:
            response = client.post(
                "/api/v1/development/integrations/ghl/discover",
                headers={
                    "X-Demo-Admin-Token": "synthetic-administrator-token-long-enough"
                },
                json={
                    "location_id": "synthetic-location",
                    "token": "synthetic-private-token",
                },
            )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "GHL_AUTH_REQUIRED"
    assert "synthetic-private-token" not in response.text
    assert response.headers["Cache-Control"] == "no-store"


def test_customer_credentials_do_not_authorize_ghl_management() -> None:
    application, _ = app()
    with TestClient(application) as client:
        response = client.get(
            "/api/v1/development/integrations/ghl",
            headers={
                "Authorization": "Bearer synthetic-customer-session",
                "X-Customer-Portal-Key": "synthetic-customer-key",
            },
        )
        assert response.status_code == 401
