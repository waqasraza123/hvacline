from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from insurance_operations.database.models.conversation import ConversationSession
from insurance_operations.database.models.website import (
    Website,
    WebsiteAgentBinding,
    WebsiteVersion,
)
from insurance_operations.errors import ApiError


def website_unavailable() -> ApiError:
    return ApiError(
        status_code=404,
        code="WEBSITE_UNAVAILABLE",
        message="This website or action is not available.",
    )


def active_website(
    session: Session,
    agency_id: UUID,
    website_id: UUID,
    binding_id: UUID,
    version_id: UUID | None = None,
) -> WebsiteVersion:
    site = session.scalar(
        select(Website).where(Website.id == website_id, Website.agency_id == agency_id)
    )
    agent = session.scalar(
        select(WebsiteAgentBinding).where(
            WebsiteAgentBinding.id == binding_id,
            WebsiteAgentBinding.agency_id == agency_id,
        )
    )
    version = (
        session.get(WebsiteVersion, site.published_version_id)
        if site and site.published_version_id
        else None
    )
    if (
        site is None
        or site.status != "published"
        or version is None
        or not version.voice_enabled
        or version.agent_binding_id != binding_id
        or (version_id is not None and version.id != version_id)
        or agent is None
        or not agent.enabled
        or not agent.browser_tools_confirmed
    ):
        raise website_unavailable()
    return version


def session_website(
    session: Session, conversation: ConversationSession, capability: str | None = None
) -> WebsiteVersion | None:
    if conversation.website_id is None:
        return None
    if (
        conversation.website_agent_binding_id is None
        or conversation.website_version_id is None
    ):
        raise website_unavailable()
    site = active_website(
        session,
        conversation.agency_id,
        conversation.website_id,
        conversation.website_agent_binding_id,
        conversation.website_version_id,
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
