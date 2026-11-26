import asyncio
from unittest.mock import MagicMock
from uuid import uuid4

import httpx
import pytest
from cryptography.fernet import Fernet
from fastapi import FastAPI
from pydantic import ValidationError

from insurance_operations.conversations.schemas import ConversationTurn
from insurance_operations.customer_memory.service import redact_pairing_codes
from insurance_operations.errors import ApiError, api_error_handler
from insurance_operations.phone_access.routes import create_phone_access_tools_router
from insurance_operations.phone_access.schemas import AccessApprovalInput, PhoneAccessStart
from insurance_operations.settings import ApiSettings


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ApiSettings.model_fields:
        monkeypatch.delenv(name.upper(), raising=False)


def configuration(**overrides: object) -> ApiSettings:
    return ApiSettings(_env_file=None, **{
        "app_environment": "development", "api_host": "127.0.0.1", "api_port": 8000,
        "database_url": "postgresql://synthetic:synthetic@localhost/development",
        "development_actor_user_id": uuid4(), "demo_sandbox_enabled": True,
        "demo_admin_token": "synthetic-demo-access-at-least-32-characters",
        "website_platform_enabled": True, "customer_portal_enabled": True,
        "customer_portal_secret": "synthetic-customer-portal-at-least-32-characters",
        "customer_mfa_encryption_key": Fernet.generate_key().decode(),
        "phone_account_access_enabled": True, **overrides,
    })


@pytest.mark.parametrize("overrides", [
    {"customer_portal_enabled": False}, {"demo_sandbox_enabled": False},
    {"app_environment": "production"}, {"development_actor_user_id": None},
])
def test_call_access_cannot_bypass_customer_environment(overrides: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        configuration(**overrides)


def test_tools_require_the_existing_provider_secret_before_database_access() -> None:
    sessions = MagicMock()
    verify = MagicMock(side_effect=ApiError(status_code=403, code="REJECTED", message="Denied"))
    app = FastAPI()
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(create_phone_access_tools_router(configuration(), sessions, verify))

    async def call() -> httpx.Response:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://example.com") as client:
            return await client.post("/api/v1/providers/elevenlabs/tools/account/appointments", json={"inbound_call_id": str(uuid4()), "conversation_id": "synthetic"})

    assert asyncio.run(call()).status_code == 403
    sessions.assert_not_called()


def test_disabled_tools_do_not_read_customer_or_call_data() -> None:
    sessions, verify = MagicMock(), MagicMock()
    app = FastAPI()
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(create_phone_access_tools_router(configuration(phone_account_access_enabled=False), sessions, verify))

    async def call() -> httpx.Response:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://example.com") as client:
            return await client.post("/api/v1/providers/elevenlabs/tools/account/begin", json={"inbound_call_id": str(uuid4()), "conversation_id": "synthetic", "explicit_request": True})

    assert asyncio.run(call()).status_code == 404
    sessions.assert_not_called()
    verify.assert_not_called()


def test_code_approval_rejects_authenticator_codes_and_caller_supplied_identity() -> None:
    with pytest.raises(ValidationError):
        AccessApprovalInput(access_id=uuid4(), code="123456", explicit_confirmation=True)
    with pytest.raises(ValidationError):
        AccessApprovalInput(access_id=uuid4(), code="CALL-ABCD-1234-FFFF", explicit_confirmation=False)
    with pytest.raises(ValidationError):
        PhoneAccessStart.model_validate({"inbound_call_id": str(uuid4()), "conversation_id": "synthetic", "explicit_request": True, "account_id": str(uuid4())})


def test_call_codes_are_removed_before_transcript_storage() -> None:
    turns = [ConversationTurn(speaker="AGENT", text="Enter CALL-ABCD-1234-FFFF here."),
             ConversationTurn(speaker="USER", text="call abcd 1234 ffff"),
             ConversationTurn(speaker="USER", text="I need AC maintenance.")]
    result = redact_pairing_codes(turns)
    assert result[0].text == "Enter [account linking code omitted] here."
    assert result[1].text == "[account linking code omitted]"
    assert result[2].text == turns[2].text
