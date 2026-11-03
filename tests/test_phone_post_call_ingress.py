import asyncio
from collections.abc import AsyncIterator
from typing import cast
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

from insurance_operations.errors import ApiError
from insurance_operations.telephony.ingress import (
    TelephonyIngressService,
    create_phone_tools_router,
)
from insurance_operations.telephony.providers.elevenlabs import MAX_WEBHOOK_BYTES


@pytest.mark.parametrize("oversized", [False, True])
def test_post_call_stream_is_bounded_before_finalization(oversized: bool) -> None:
    ingress = Mock(spec=TelephonyIngressService)
    app = FastAPI()
    app.include_router(create_phone_tools_router(cast(TelephonyIngressService, ingress)))

    @app.middleware("http")
    async def correlation_id(
        request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request.state.correlation_id = str(uuid4())
        return await call_next(request)

    @app.exception_handler(ApiError)
    async def rejected_event(request: Request, error: ApiError) -> JSONResponse:
        return JSONResponse({"code": error.code}, status_code=error.status_code)

    async def body() -> AsyncIterator[bytes]:
        yield b"x" * MAX_WEBHOOK_BYTES
        if oversized:
            yield b"x"
            raise AssertionError("Oversized requests must stop reading the stream")

    async def exercise() -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="https://api.example.test"
        ) as client:
            response = await client.post(
                "/api/v1/providers/elevenlabs/post-call", content=body()
            )
            if oversized:
                assert response.status_code == 413
                assert response.json()["code"] == "PHONE_POST_CALL_TOO_LARGE"
                ingress.receive_post_call.assert_not_called()
            else:
                assert response.status_code == 200
                assert ingress.receive_post_call.call_args.kwargs["body"] == (
                    b"x" * MAX_WEBHOOK_BYTES
                )

    asyncio.run(exercise())
