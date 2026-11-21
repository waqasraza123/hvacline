from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.actors import ActorContext
from insurance_operations.conversations.contracts import ConversationProvider
from insurance_operations.conversations.providers.elevenlabs import (
    ElevenLabsConversationProvider,
)
from insurance_operations.conversations.schemas import (
    ConversationSessionCreateInput,
    ConversationSessionResponse,
)
from insurance_operations.conversations.service import ConversationService
from insurance_operations.database.models.approved_faq import AgencyApprovedFaq
from insurance_operations.database.models.conversation import ConversationSession
from insurance_operations.database.models.identity import Agency
from insurance_operations.database.models.operations import AuditActorType, AuditEvent
from insurance_operations.database.models.website import (
    Website,
    WebsiteAgentBinding,
    WebsiteVersion,
)
from insurance_operations.errors import ApiError
from insurance_operations.settings import ApiSettings, RuntimeEnvironment
from insurance_operations.websites.guards import website_unavailable
from insurance_operations.websites.schemas import WebsiteDocument, WebsiteSave


class WebsiteService:
    def __init__(
        self,
        sessions: sessionmaker[Session],
        settings: ApiSettings,
        provider_factory: Callable[[str], ConversationProvider] | None = None,
    ) -> None:
        self.sessions, self.settings = sessions, settings
        self.provider_factory = provider_factory

    def enabled(self) -> None:
        if (
            not self.settings.website_platform_enabled
            or self.settings.app_environment
            not in {RuntimeEnvironment.DEVELOPMENT, RuntimeEnvironment.TEST}
        ):
            raise website_unavailable()

    def _owned(
        self, session: Session, actor: ActorContext, website_id: UUID
    ) -> Website:
        site = session.scalar(
            select(Website)
            .where(Website.id == website_id, Website.agency_id == actor.agency_id)
            .with_for_update()
        )
        if site is None:
            raise website_unavailable()
        return site

    def available(self, session: Session, site: WebsiteVersion) -> bool:
        agent = (
            session.get(WebsiteAgentBinding, site.agent_binding_id)
            if site.agent_binding_id
            else None
        )
        return bool(
            site.voice_enabled
            and agent
            and agent.agency_id == site.agency_id
            and agent.enabled
            and agent.browser_tools_confirmed
            and (
                self.provider_factory is not None
                or (
                    self.settings.elevenlabs_api_key
                    and self.settings.elevenlabs_privacy_confirmed
                )
            )
        )

    def public(self, slug: str) -> dict[str, object]:
        self.enabled()
        with self.sessions() as session:
            site = session.scalar(
                select(Website)
                .join(Agency, Agency.id == Website.agency_id)
                .where(
                    Website.slug == slug,
                    Website.status == "published",
                    Agency.archived_at.is_(None),
                )
            )
            if site is None:
                raise website_unavailable()
            version = (
                session.get(WebsiteVersion, site.published_version_id)
                if site.published_version_id
                else None
            )
            if version is None:
                raise website_unavailable()
            return {
                "id": str(site.id),
                "slug": site.slug,
                "configuration": WebsiteDocument.model_validate(
                    version.configuration
                ).model_dump(mode="json"),
                "voice_available": self.available(session, version),
                "capabilities": {
                    "lead_capture": version.lead_capture_enabled,
                    "booking": False,
                    "memory": False,
                },
            }

    def owner_view(self, site: Website) -> dict[str, object]:
        return {
            "id": str(site.id),
            "slug": site.slug,
            "configuration": site.configuration,
            "status": site.status,
            "row_version": site.row_version,
            "published_version_id": str(site.published_version_id)
            if site.published_version_id
            else None,
            "agent_binding_id": str(site.agent_binding_id)
            if site.agent_binding_id
            else None,
            "knowledge_faq_ids": site.knowledge_faq_ids,
            "voice_enabled": site.voice_enabled,
            "lead_capture_enabled": site.lead_capture_enabled,
            "created_at": site.created_at.isoformat(),
            "updated_at": site.updated_at.isoformat(),
        }

    def list(self, actor: ActorContext) -> dict[str, object]:
        self.enabled()
        with self.sessions() as session:
            sites = session.scalars(
                select(Website)
                .where(Website.agency_id == actor.agency_id)
                .order_by(Website.created_at.desc())
                .limit(100)
            ).all()
            agents = session.scalars(
                select(WebsiteAgentBinding)
                .where(WebsiteAgentBinding.agency_id == actor.agency_id)
                .order_by(WebsiteAgentBinding.label)
            ).all()
            faqs = session.scalars(
                select(AgencyApprovedFaq).where(
                    AgencyApprovedFaq.agency_id == actor.agency_id,
                    AgencyApprovedFaq.status == "ACTIVE",
                )
            ).all()
            return {
                "websites": [self.owner_view(site) for site in sites],
                "agents": [
                    {
                        "id": str(agent.id),
                        "label": agent.label,
                        "enabled": agent.enabled and agent.browser_tools_confirmed,
                    }
                    for agent in agents
                ],
                "knowledge": [
                    {"id": str(faq.id), "question": faq.question} for faq in faqs
                ],
            }

    def save(
        self, actor: ActorContext, data: WebsiteSave, website_id: UUID | None = None
    ) -> dict[str, object]:
        self.enabled()
        try:
            with self.sessions() as session, session.begin():
                if data.agent_binding_id is not None:
                    agent = session.scalar(
                        select(WebsiteAgentBinding).where(
                            WebsiteAgentBinding.id == data.agent_binding_id,
                            WebsiteAgentBinding.agency_id == actor.agency_id,
                        )
                    )
                    if agent is None:
                        raise website_unavailable()
                if data.voice_enabled and data.agent_binding_id is None:
                    raise ApiError(
                        status_code=422,
                        code="WEBSITE_AGENT_REQUIRED",
                        message=(
                            "Choose an authorized configured agent "
                            "before enabling voice."
                        ),
                    )
                if data.knowledge_faq_ids:
                    owned = set(
                        session.scalars(
                            select(AgencyApprovedFaq.id).where(
                                AgencyApprovedFaq.id.in_(data.knowledge_faq_ids),
                                AgencyApprovedFaq.agency_id == actor.agency_id,
                                AgencyApprovedFaq.status == "ACTIVE",
                            )
                        ).all()
                    )
                    if owned != set(data.knowledge_faq_ids):
                        raise website_unavailable()
                if website_id is None:
                    if data.expected_row_version != 0:
                        raise self.conflict()
                    site = Website(
                        agency_id=actor.agency_id,
                        slug=data.configuration.slug,
                        template_id=data.configuration.templateId,
                    )
                    session.add(site)
                else:
                    site = self._owned(session, actor, website_id)
                    if site.row_version != data.expected_row_version:
                        raise self.conflict()
                    if site.slug != data.configuration.slug:
                        raise ApiError(
                            status_code=422,
                            code="WEBSITE_SLUG_IMMUTABLE",
                            message="The website slug cannot change after creation.",
                        )
                    site.row_version += 1
                if website_id is None:
                    site.status = "draft"
                if data.status == "disabled":
                    site.status = "disabled"
                site.configuration = data.configuration.model_copy(
                    update={"status": "demo"}
                ).model_dump(mode="json")
                site.template_id = data.configuration.templateId
                site.agent_binding_id = data.agent_binding_id
                site.knowledge_faq_ids = [str(key) for key in data.knowledge_faq_ids]
                site.voice_enabled, site.lead_capture_enabled = (
                    data.voice_enabled,
                    data.lead_capture_enabled,
                )
                site.updated_at = datetime.now(UTC)
                session.flush()
                if data.status == "published":
                    self._publish(session, actor, site, site)
                self._audit(session, actor, site, "WEBSITE_DRAFT_SAVED")
                return self.owner_view(site)
        except IntegrityError as error:
            raise ApiError(
                status_code=409,
                code="WEBSITE_CONFLICT",
                message=(
                    "The website slug or binding is unavailable. "
                    "Refresh before retrying."
                ),
            ) from error

    @staticmethod
    def conflict() -> ApiError:
        return ApiError(
            status_code=409,
            code="WEBSITE_VERSION_CONFLICT",
            message="The website changed. Reload it before saving again.",
        )

    @staticmethod
    def _audit(
        session: Session, actor: ActorContext, site: Website, event: str
    ) -> None:
        session.add(
            AuditEvent(
                agency_id=actor.agency_id,
                actor_type=AuditActorType.STAFF.value,
                actor_user_id=actor.app_user_id,
                event_type=event,
                occurred_at=datetime.now(UTC),
                summary="Website configuration changed",
                details={
                    "website_id": str(site.id),
                    "row_version": site.row_version,
                    "published_version_id": str(site.published_version_id)
                    if site.published_version_id
                    else None,
                },
                correlation_id=uuid4(),
            )
        )

    def _publish(
        self,
        session: Session,
        actor: ActorContext,
        site: Website,
        source: Website | WebsiteVersion,
    ) -> None:
        document = WebsiteDocument.model_validate(source.configuration)
        if source.agent_binding_id:
            binding = session.get(WebsiteAgentBinding, source.agent_binding_id)
            if binding is None or binding.agency_id != actor.agency_id:
                raise website_unavailable()
            if source.voice_enabled and (
                not binding.enabled or not binding.browser_tools_confirmed
            ):
                raise ApiError(
                    status_code=422,
                    code="WEBSITE_AGENT_UNAVAILABLE",
                    message="Enable and review this agent before publishing voice.",
                )
        elif source.voice_enabled:
            raise ApiError(
                status_code=422,
                code="WEBSITE_AGENT_REQUIRED",
                message="Choose an authorized agent before publishing voice.",
            )
        if source.knowledge_faq_ids:
            selected = [UUID(value) for value in source.knowledge_faq_ids]
            owned = set(
                session.scalars(
                    select(AgencyApprovedFaq.id).where(
                        AgencyApprovedFaq.id.in_(selected),
                        AgencyApprovedFaq.agency_id == actor.agency_id,
                        AgencyApprovedFaq.status == "ACTIVE",
                    )
                )
            )
            if owned != set(selected):
                raise website_unavailable()
        number = (
            session.scalar(
                select(func.max(WebsiteVersion.number)).where(
                    WebsiteVersion.website_id == site.id
                )
            )
            or 0
        ) + 1
        version = WebsiteVersion(
            website_id=site.id,
            agency_id=site.agency_id,
            number=number,
            configuration=document.model_copy(
                update={"status": "published"}
            ).model_dump(mode="json"),
            agent_binding_id=source.agent_binding_id,
            knowledge_faq_ids=list(source.knowledge_faq_ids),
            voice_enabled=source.voice_enabled,
            lead_capture_enabled=source.lead_capture_enabled,
            created_by=actor.app_user_id,
        )
        session.add(version)
        session.flush()
        site.published_version_id = version.id
        site.status = "published"
        session.flush()
        self._audit(session, actor, site, "WEBSITE_PUBLISHED")

    def versions(
        self, actor: ActorContext, website_id: UUID
    ) -> Sequence[dict[str, object]]:
        self.enabled()
        with self.sessions() as session:
            site = self._owned(session, actor, website_id)
            versions = session.scalars(
                select(WebsiteVersion)
                .where(
                    WebsiteVersion.website_id == site.id,
                    WebsiteVersion.agency_id == actor.agency_id,
                )
                .order_by(WebsiteVersion.number.desc())
            )
            return [
                {
                    "id": str(version.id),
                    "number": version.number,
                    "created_at": version.created_at.isoformat(),
                    "active": site.status == "published"
                    and version.id == site.published_version_id,
                    "brand_name": WebsiteDocument.model_validate(
                        version.configuration
                    ).brand.name,
                }
                for version in versions
            ]

    def publication(
        self,
        actor: ActorContext,
        website_id: UUID,
        expected_row_version: int,
        *,
        unpublish: bool = False,
        restore_version_id: UUID | None = None,
    ) -> dict[str, object]:
        self.enabled()
        with self.sessions() as session, session.begin():
            site = self._owned(session, actor, website_id)
            if site.row_version != expected_row_version:
                raise self.conflict()
            site.row_version += 1
            site.updated_at = datetime.now(UTC)
            if unpublish:
                site.status = "disabled"
                self._audit(session, actor, site, "WEBSITE_UNPUBLISHED")
            else:
                source: Website | WebsiteVersion = site
                if restore_version_id:
                    previous = session.scalar(
                        select(WebsiteVersion).where(
                            WebsiteVersion.id == restore_version_id,
                            WebsiteVersion.website_id == site.id,
                            WebsiteVersion.agency_id == actor.agency_id,
                        )
                    )
                    if previous is None:
                        raise website_unavailable()
                    source = previous
                self._publish(session, actor, site, source)
                if restore_version_id:
                    self._audit(session, actor, site, "WEBSITE_ROLLED_BACK")
            session.flush()
            return self.owner_view(site)

    def owned_session(self, actor: ActorContext, slug: str, session_id: UUID) -> None:
        self.enabled()
        with self.sessions() as session:
            row = session.scalar(
                select(ConversationSession)
                .join(Website, Website.id == ConversationSession.website_id)
                .where(
                    Website.slug == slug,
                    Website.agency_id == actor.agency_id,
                    ConversationSession.id == session_id,
                    ConversationSession.agency_id == actor.agency_id,
                    ConversationSession.initiated_by == actor.app_user_id,
                )
            )
            if row is None:
                raise website_unavailable()

    def authorize(
        self, actor: ActorContext, slug: str, data: ConversationSessionCreateInput
    ) -> ConversationSessionResponse:
        self.enabled()
        with self.sessions() as session:
            site = session.scalar(
                select(Website).where(
                    Website.slug == slug,
                    Website.agency_id == actor.agency_id,
                    Website.status == "published",
                )
            )
            if site is None or site.published_version_id is None:
                raise website_unavailable()
            version = session.get(WebsiteVersion, site.published_version_id)
            if (
                version is None
                or not self.available(session, version)
                or version.agent_binding_id is None
            ):
                raise website_unavailable()
            binding = session.get(WebsiteAgentBinding, version.agent_binding_id)
            if binding is None or binding.agency_id != actor.agency_id:
                raise website_unavailable()
            version_id = version.id
            site_id, binding_id, provider_agent_id = (
                site.id,
                binding.id,
                binding.provider_agent_id,
            )
        if self.provider_factory:
            provider = self.provider_factory(provider_agent_id)
        else:
            key = self.settings.elevenlabs_api_key
            if key is None:
                raise website_unavailable()
            provider = ElevenLabsConversationProvider(
                api_key=key.get_secret_value(), agent_id=provider_agent_id
            )
        try:
            service = ConversationService(
                session_factory=self.sessions, settings=self.settings, provider=provider
            )
            return service.authorize_session(
                actor=actor,
                request=data,
                website_id=site_id,
                website_agent_binding_id=binding_id,
                website_version_id=version_id,
            )
        finally:
            provider.close()
