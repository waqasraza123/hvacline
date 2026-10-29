import re
import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Response
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.errors import ApiError
from insurance_operations.homepage_chat.provider import (
    ElevenLabsHomepageProvider,
    HomepageReplyProvider,
)
from insurance_operations.homepage_chat.schemas import (
    HomepageChatInput,
    HomepageChatReply,
    HomepageChatStatus,
)
from insurance_operations.homepage_chat.service import HomepageChatService
from insurance_operations.settings import ApiSettings


def create_homepage_chat_router(
    settings: ApiSettings,
    sessions: sessionmaker[Session],
    provider: HomepageReplyProvider | None = None,
) -> APIRouter:
    router = APIRouter(prefix="/api/v1/homepage-chat")

    def visitor(
        response: Response,
        portal_key: Annotated[str | None, Header(alias="X-Customer-Portal-Key")] = None,
        token: Annotated[str | None, Header(alias="X-Homepage-Visitor")] = None,
    ) -> str:
        response.headers["Cache-Control"] = "no-store"
        secret = settings.customer_portal_secret
        if not settings.homepage_chat_enabled:
            raise ApiError(
                status_code=404,
                code="HOMEPAGE_CHAT_DISABLED",
                message="Sign in to speak with Line.",
            )
        if (
            secret is None
            or portal_key is None
            or not secrets.compare_digest(
                portal_key.encode(), secret.get_secret_value().encode()
            )
            or token is None
            or re.fullmatch(r"[A-Za-z0-9_-]{43}", token) is None
        ):
            raise ApiError(
                status_code=401,
                code="HOMEPAGE_CHAT_UNAUTHORIZED",
                message="Please use Line on the homepage.",
            )
        return token

    def service() -> HomepageChatService:
        key = settings.elevenlabs_api_key
        agent_id = settings.elevenlabs_agent_id
        if key is None or agent_id is None:
            raise ApiError(
                status_code=503,
                code="HOMEPAGE_CHAT_UNAVAILABLE",
                message="Please sign in to speak with Line.",
            )
        return HomepageChatService(
            sessions,
            settings,
            provider or ElevenLabsHomepageProvider(key.get_secret_value(), agent_id),
        )

    @router.get("", response_model=HomepageChatStatus)
    def status(token: Annotated[str, Depends(visitor)]) -> HomepageChatStatus:
        return service().status(token)

    @router.post("", response_model=HomepageChatReply)
    def reply(
        data: HomepageChatInput, token: Annotated[str, Depends(visitor)]
    ) -> HomepageChatReply:
        return service().reply(token, data)

    return router
