from unittest.mock import patch
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.orm import sessionmaker

from insurance_operations.actors import ActorContext
from insurance_operations.errors import ApiError, api_error_handler
from insurance_operations.recovery.routes import create_recovery_router
from insurance_operations.recovery.continuation_routes import create_recovery_continuation_routes, create_recovery_voice_tools
from insurance_operations.settings import ApiSettings


def application() -> FastAPI:
    settings = ApiSettings(_env_file=None, app_environment="development", api_host="127.0.0.1", api_port=8000, database_url="postgresql://synthetic:synthetic@localhost/synthetic", web_origin="http://localhost:3000", demo_sandbox_enabled=False,
        demo_admin_token=SecretStr("synthetic-admin-token-at-least-32-characters"), conversation_ai_enabled=False)
    app = FastAPI()

    @app.exception_handler(ApiError)
    async def error_handler(request: Request, error: ApiError) -> JSONResponse:
        return await api_error_handler(request, error)

    actor = ActorContext(uuid4(), "Synthetic admin", uuid4(), "Synthetic HVAC", "DEVELOPMENT")
    app.include_router(create_recovery_router(settings, sessionmaker(), lambda: actor))
    app.include_router(create_recovery_continuation_routes(settings, sessionmaker()))
    app.include_router(create_recovery_voice_tools(settings, sessionmaker()))
    return app


def test_recovery_always_requires_administrator_even_if_sandbox_gate_is_disabled() -> None:
    app = application()
    with patch("insurance_operations.recovery.routes.RecoveryService.summary", return_value={"total": 0}) as summary, TestClient(app) as client:
        prefix = "/api/v1/development/lead-recovery"
        for path in ["/summary", "/cases", "/settings", "/ai", "/staff"]:
            assert client.get(prefix + path).status_code == 401
            assert client.get(prefix + path, headers={"Authorization": "Bearer synthetic-customer"}).status_code == 401
        summary.assert_not_called()
        response = client.get(prefix + "/summary", headers={"X-Demo-Admin-Token": "synthetic-admin-token-at-least-32-characters"})
        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "no-store"


def test_provider_requests_are_not_performed_for_unauthenticated_tests() -> None:
    app = application()
    with patch("insurance_operations.recovery.ai.chat_completion") as completion, TestClient(app) as client:
        response = client.post("/api/v1/development/lead-recovery/ai/test", json={"expected_row_version": 1})
        assert response.status_code == 401
        completion.assert_not_called()


def test_customer_and_voice_tools_require_their_own_authorization() -> None:
    app = application()
    with patch("insurance_operations.recovery.voice.RecoveryVoice.bind") as bind, TestClient(app) as client:
        assert client.get("/api/v1/recovery/continuation").status_code == 403
        assert client.get("/api/v1/recovery/continuation", headers={"X-Demo-Admin-Token": "synthetic-admin-token-at-least-32-characters"}).status_code == 403
        for action in ["continue", "context", "readback", "release", "finish"]:
            response = client.post(f"/api/v1/providers/recovery/voice/tools/{action}", json={"action": "STOP"})
            assert response.status_code == 403
        bind.assert_not_called()
