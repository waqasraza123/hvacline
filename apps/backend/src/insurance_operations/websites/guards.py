from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from insurance_operations.database.models.conversation import ConversationSession
from insurance_operations.database.models.website import Website, WebsiteAgentBinding
from insurance_operations.errors import ApiError


def website_unavailable() -> ApiError:
    return ApiError(
        status_code=404,
        code="WEBSITE_UNAVAILABLE",
        message="This website or action is not available.",
    )


def active_website(
    session: Session, agency_id: UUID, website_id: UUID, binding_id: UUID
) -> Website:
    site = session.scalar(
        select(Website).where(Website.id == website_id, Website.agency_id == agency_id)
    )
    agent = session.scalar(
        select(WebsiteAgentBinding).where(
            WebsiteAgentBinding.id == binding_id,
            WebsiteAgentBinding.agency_id == agency_id,
        )
    )
    if (
        site is None
        or site.status != "published"
        or not site.voice_enabled
        or site.agent_binding_id != binding_id
        or agent is None
        or not agent.enabled
        or not agent.browser_tools_confirmed
    ):
        raise website_unavailable()
    return site


def session_website(
    session: Session, conversation: ConversationSession, capability: str | None = None
) -> Website | None:
    if conversation.website_id is None:
        return None
    if conversation.website_agent_binding_id is None:
        raise website_unavailable()
    site = active_website(
        session,
        conversation.agency_id,
        conversation.website_id,
        conversation.website_agent_binding_id,
    )
    if capability is not None:
        allowed = capability in {
            "knowledge",
            "lead_capture",
        } and conversation.website_capabilities.get(capability, False)
        if capability == "lead_capture":
            allowed = allowed and site.lead_capture_enabled
        if not allowed:
            raise ApiError(
                status_code=403,
                code="WEBSITE_CAPABILITY_DISABLED",
                message="This action is not enabled for this website.",
            )
    return site
