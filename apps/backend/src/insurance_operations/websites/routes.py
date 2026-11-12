import secrets
from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request, Response
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.actors import ActorContext
from insurance_operations.approved_faqs.schemas import ApprovedFaqLookupInput
from insurance_operations.approved_faqs.service import ApprovedFaqService
from insurance_operations.conversations.schemas import (
    ConversationEndInput,
)
from insurance_operations.conversations.service import ConversationService
from insurance_operations.customer_access.service import CustomerAccessService
from insurance_operations.errors import ApiError
from insurance_operations.settings import ApiSettings
from insurance_operations.websites.guards import website_unavailable
from insurance_operations.websites.schemas import (
    WebsiteInquiry,
    WebsiteSave,
    WebsiteSessionCreateInput,
)
from insurance_operations.websites.service import WebsiteService


def create_website_router(
    settings: ApiSettings,
    sessions: sessionmaker[Session],
    owner_dependency: Callable[..., ActorContext],
    website_service: WebsiteService | None = None,
) -> APIRouter:
    router = APIRouter()
    websites = website_service or WebsiteService(sessions, settings)
    access = CustomerAccessService(sessions, settings)
    conversations = ConversationService(
        session_factory=sessions, settings=settings, provider=None
    )
    faqs = ApprovedFaqService(session_factory=sessions)
    Owner = Annotated[ActorContext, Depends(owner_dependency)]

    def customer(
        authorization: Annotated[str | None, Header()] = None,
        portal_key: Annotated[str | None, Header(alias="X-Customer-Portal-Key")] = None,
    ) -> ActorContext:
        websites.enabled()
        secret = settings.customer_portal_secret
        if (
            not settings.customer_portal_enabled
            or not settings.demo_sandbox_enabled
            or secret is None
            or not portal_key
            or not secrets.compare_digest(
                portal_key.encode(), secret.get_secret_value().encode()
            )
        ):
            raise website_unavailable()
        token = (
            authorization[7:]
            if authorization and authorization.startswith("Bearer ")
            else None
        )
        return access.identity(token)[0]

    Customer = Annotated[ActorContext, Depends(customer)]

    @router.get("/api/v1/websites/{slug}")
    def public_website(slug: str, response: Response) -> dict[str, object]:
        response.headers["Cache-Control"] = "no-store"
        return websites.public(slug)

    @router.get("/api/v1/development/websites")
    def list_websites(owner: Owner, response: Response) -> dict[str, object]:
        response.headers["Cache-Control"] = "no-store"
        return websites.list(owner)

    @router.post("/api/v1/development/websites", status_code=201)
    def create_website(data: WebsiteSave, owner: Owner) -> dict[str, object]:
        return websites.save(owner, data)

    @router.put("/api/v1/development/websites/{website_id}")
    def update_website(
        website_id: UUID, data: WebsiteSave, owner: Owner
    ) -> dict[str, object]:
        return websites.save(owner, data, website_id)

    @router.post(
        "/api/v1/customer/websites/{slug}/conversation-sessions", status_code=201
    )
    def authorize(
        slug: str, data: WebsiteSessionCreateInput, actor: Customer
    ) -> object:
        return websites.authorize(actor, slug, data)

    @router.post(
        "/api/v1/customer/websites/{slug}/conversation-sessions/{session_id}/end"
    )
    def end(
        slug: str, session_id: UUID, data: ConversationEndInput, actor: Customer
    ) -> object:
        websites.owned_session(actor, slug, session_id)
        return conversations.end_session(
            actor=actor, conversation_session_id=session_id, outcome=data.outcome
        )

    @router.post(
        "/api/v1/customer/websites/{slug}/conversation-sessions/{session_id}/approved-faq-lookup"
    )
    def faq(
        slug: str,
        session_id: UUID,
        data: ApprovedFaqLookupInput,
        actor: Customer,
        request: Request,
    ) -> object:
        websites.owned_session(actor, slug, session_id)
        return faqs.conversation_lookup(
            actor=actor,
            conversation_session_id=session_id,
            query=data.query,
            correlation_id=UUID(request.state.correlation_id),
        )

    @router.post(
        "/api/v1/customer/websites/{slug}/conversation-intakes", status_code=201
    )
    def inquiry(
        slug: str,
        data: WebsiteInquiry,
        actor: Customer,
        request: Request,
        response: Response,
        key: Annotated[
            str, Header(alias="Idempotency-Key", min_length=1, max_length=128)
        ],
    ) -> object:
        if not all(
            character.isascii() and (character.isalnum() or character in "_.:-")
            for character in key
        ):
            raise ApiError(
                status_code=422,
                code="INVALID_IDEMPOTENCY_KEY",
                message="Invalid confirmation key.",
            )
        websites.owned_session(actor, slug, data.conversation_session_id)
        result, replayed = conversations.confirm_intake(
            actor=actor,
            request=data,
            idempotency_key=key,
            correlation_id=UUID(request.state.correlation_id),
        )
        if replayed:
            response.headers["Idempotent-Replayed"] = "true"
        return result

    return router
