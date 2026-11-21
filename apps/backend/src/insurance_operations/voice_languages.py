"""Agency language intent and separately attested ElevenLabs capabilities."""

import secrets
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated, Literal, Self, TypedDict, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request, Response
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.actors import ActorContext
from insurance_operations.database.models.conversation import ConversationSession
from insurance_operations.database.models.hvac import Appointment, HvacServiceRequest
from insurance_operations.database.models.operations import AuditEvent
from insurance_operations.database.models.receptionist import AgencyReceptionistSettings
from insurance_operations.errors import ApiError

LanguageCode = Literal["en", "es", "fr", "ar", "hi", "zh", "ur"]
VoiceChannel = Literal["browser", "mobile", "phone", "recovery"]
LANGUAGES: dict[LanguageCode, str] = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "ar": "Arabic",
    "hi": "Hindi",
    "zh": "Mandarin Chinese",
    "ur": "Urdu",
}
CHANNELS: tuple[VoiceChannel, ...] = ("browser", "mobile", "phone", "recovery")


class LanguageCapability(TypedDict):
    channel: VoiceChannel
    code: LanguageCode
    name: str
    enabled: bool
    available: bool
    voice_id: str
    greeting: str
    automatic_switching: bool
    status: str
    verified_at: str | None


class LanguageRegistry(TypedDict):
    configuration: dict[str, object]
    languages: list[LanguageCapability]
    effective_defaults: dict[VoiceChannel, LanguageCode | None]
    observation_status: str
    observed_switches: None
    switch_failures: None
    unsupported_requests: None
    note: str


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class LanguagePreset(StrictModel):
    voice_id: str = Field(default="", max_length=200, pattern=r"^[A-Za-z0-9_-]*$")
    greeting: str = Field(default="", max_length=600)


class VoiceLanguageConfiguration(StrictModel):
    default_language: LanguageCode = "en"
    enabled_languages: list[LanguageCode] = Field(
        default_factory=lambda: ["en"], min_length=1, max_length=7
    )
    automatic_switching: bool = False
    presets: dict[VoiceChannel, dict[LanguageCode, LanguagePreset]] = Field(
        default_factory=dict
    )

    @model_validator(mode="after")
    def valid_languages(self) -> Self:
        if len(set(self.enabled_languages)) != len(self.enabled_languages):
            raise ValueError("Enabled languages must be unique")
        if (
            "en" not in self.enabled_languages
            or self.default_language not in self.enabled_languages
        ):
            raise ValueError("English and the default language must be enabled")
        return self


class ProviderLanguageEvidence(StrictModel):
    agency_id: UUID
    agent_id: str = Field(min_length=1, max_length=200)
    verified_at: datetime
    default_language: LanguageCode = "en"
    supported_languages: list[LanguageCode] = Field(min_length=1, max_length=7)
    presets: dict[LanguageCode, LanguagePreset]
    language_override: bool = False
    language_detection: bool = False
    mid_call_switching: bool = False
    safety_prompt_verified: bool = False
    stack_verified: bool = False

    @model_validator(mode="after")
    def valid_evidence(self) -> Self:
        if self.verified_at.tzinfo is None or self.verified_at > datetime.now(UTC):
            raise ValueError(
                "Provider verification requires a past timezone-aware timestamp"
            )
        if len(set(self.supported_languages)) != len(self.supported_languages):
            raise ValueError("Provider languages must be unique")
        if (
            "en" not in self.supported_languages
            or self.default_language not in self.supported_languages
        ):
            raise ValueError("Provider must support English and its default language")
        if set(self.presets) != set(self.supported_languages):
            raise ValueError("Each supported language needs its verified preset")
        if any(
            not preset.voice_id or not preset.greeting
            for preset in self.presets.values()
        ):
            raise ValueError(
                "Verified presets require a voice and reviewed disclosure greeting"
            )
        if self.mid_call_switching and not self.language_detection:
            raise ValueError(
                "Mid-call switching requires the provider language-detection tool"
            )
        return self


def configuration(session: Session, agency_id: UUID) -> VoiceLanguageConfiguration:
    row = session.scalar(
        select(AgencyReceptionistSettings).where(
            AgencyReceptionistSettings.agency_id == agency_id
        )
    )
    return VoiceLanguageConfiguration.model_validate(
        row.voice_languages if row else {}
    )


def registry(
    settings: object, agency_id: UUID, config: VoiceLanguageConfiguration
) -> LanguageRegistry:
    evidence_map: dict[VoiceChannel, ProviderLanguageEvidence] = getattr(
        settings, "voice_language_provider_evidence", {}
    )
    agent_ids = {
        "browser": getattr(settings, "elevenlabs_agent_id", None),
        "mobile": getattr(settings, "elevenlabs_agent_id", None),
        "phone": getattr(settings, "elevenlabs_phone_agent_id", None),
        "recovery": getattr(settings, "recovery_voice_agent_id", None),
    }
    rows: list[LanguageCapability] = []
    for channel in CHANNELS:
        evidence = evidence_map.get(channel)
        agent_has_evidence = any(
            item.agent_id == agent_ids[channel] for item in evidence_map.values()
        )
        # Phone consent/finalization and recovery's exact hosted-agent preflight
        # still enforce English contracts. Never advertise them as multilingual.
        integrated = channel in {"browser", "mobile"}
        bound = (
            evidence is not None
            and evidence.agency_id == agency_id
            and evidence.agent_id == agent_ids[channel]
        )
        compatible = bool(
            bound and evidence and integrated
            and evidence.stack_verified
            and evidence.safety_prompt_verified
            and evidence.language_override
            and evidence.default_language == config.default_language
            and set(evidence.supported_languages) == set(config.enabled_languages)
            and evidence.language_detection == config.automatic_switching
            and (not config.automatic_switching or evidence.mid_call_switching)
            and all(
                config.presets.get(channel, {}).get(code) == preset
                for code, preset in evidence.presets.items()
            )
        )
        local = (
            channel in {"browser", "mobile"}
            and getattr(settings, "conversation_provider", "elevenlabs")
            != "elevenlabs"
        )
        for code, name in LANGUAGES.items():
            preset = config.presets.get(channel, {}).get(code, LanguagePreset())
            legacy = code == "en" and not agent_has_evidence
            available = bool(
                (legacy and (not local or channel == "browser"))
                or (not local and compatible and code in config.enabled_languages)
            )
            status = "unsupported"
            if available:
                status = (
                    "existing_english_default" if legacy else "verified_configuration"
                )
            elif integrated and not local:
                status = "requires_provider_setup"
            rows.append({
                "channel": channel,
                "code": code,
                "name": name,
                "enabled": code in config.enabled_languages,
                "available": available,
                "voice_id": preset.voice_id,
                "greeting": preset.greeting,
                "automatic_switching": bool(
                    available and compatible and config.automatic_switching
                ),
                "status": status,
                "verified_at": (
                    evidence.verified_at.isoformat() if bound and evidence else None
                ),
            })
    effective_defaults: dict[VoiceChannel, LanguageCode | None] = {}
    for channel in CHANNELS:
        available_codes = {
            item["code"] for item in rows
            if item["channel"] == channel and item["available"]
        }
        effective_defaults[channel] = (
            config.default_language if config.default_language in available_codes
            else "en" if "en" in available_codes else None
        )
    return {
        "configuration": config.model_dump(mode="json"),
        "languages": rows,
        "effective_defaults": effective_defaults,
        "observation_status": "unavailable",
        "observed_switches": None,
        "switch_failures": None,
        "unsupported_requests": None,
        "note": (
            "Successful full provider results update the in-session language display. "
            "Client-observed switches are not persisted as server-authoritative "
            "diagnostics. Initial language is configuration, not an observed switch. "
            "No fluency or translation accuracy measurement."
        ),
    }


def authorize_language(
    settings: object,
    agency_id: UUID,
    config: VoiceLanguageConfiguration,
    requested: LanguageCode | None,
    channel: VoiceChannel,
) -> dict[str, object]:
    current = registry(settings, agency_id, config)
    defaults = current["effective_defaults"]
    code = requested or defaults[channel] or config.default_language
    rows = current["languages"]
    row = next(
        item for item in rows
        if item["channel"] == channel and item["code"] == code
    )
    if not row["available"]:
        raise ApiError(
            status_code=409,
            code="VOICE_LANGUAGE_UNAVAILABLE",
            message=(
                "This language requires verified provider setup for this channel. "
                "Choose an available language or contact staff."
            ),
        )
    legacy = row["status"] == "existing_english_default"
    return {
        "language": code,
        "allowed_languages": config.enabled_languages if not legacy else ["en"],
        "automatic_switching": row["automatic_switching"],
        "overrides": None if legacy else {"agent": {"language": code}},
    }


def require_readback_language(row: ConversationSession, language: LanguageCode) -> None:
    state = row.provider_metadata.get("voice_language")
    allowed = state.get("allowed_languages") if isinstance(state, dict) else ["en"]
    if not isinstance(allowed, list) or language not in allowed:
        raise ApiError(
            status_code=422,
            code="VOICE_LANGUAGE_UNAVAILABLE",
            message=(
                "Use a language authorized for this conversation. "
                "Ask staff for assistance if needed."
            ),
        )


def initial_language(row: ConversationSession) -> LanguageCode:
    state = row.provider_metadata.get("voice_language")
    code = state.get("language") if isinstance(state, dict) else "en"
    return (
        cast(LanguageCode, code)
        if isinstance(code, str) and code in LANGUAGES else "en"
    )


class LanguageSettingsInput(VoiceLanguageConfiguration):
    expected_row_version: int = Field(ge=1)


def create_voice_language_router(
    sessions: sessionmaker[Session],
    settings: object,
    actor_dependency: Callable[..., ActorContext],
    *,
    prefix: str = "/api/v1/development/voice-languages",
    administrator: bool = False,
) -> APIRouter:
    router = APIRouter(prefix=prefix)

    def authorized_actor(
        response: Response,
        actor: Annotated[ActorContext, Depends(actor_dependency)],
        token: Annotated[
            str | None, Header(alias="X-Demo-Admin-Token")
        ] = None,
    ) -> ActorContext:
        response.headers["Cache-Control"] = "no-store, private"
        if administrator:
            secret = getattr(settings, "demo_admin_token", None)
            if getattr(settings, "app_environment", None) == "production":
                raise ApiError(
                    status_code=404, code="NOT_FOUND",
                    message="This resource is unavailable.",
                )
            if not secret or not token or not secrets.compare_digest(
                token.encode(), secret.get_secret_value().encode()
            ):
                raise ApiError(
                    status_code=401, code="VOICE_LANGUAGE_ADMIN_REQUIRED",
                    message="Connect an authorized administrator workspace.",
                    headers={"Cache-Control": "no-store"},
                )
        return actor

    Actor = Annotated[ActorContext, Depends(authorized_actor)]

    @router.get("")
    def get_languages(actor: Actor) -> dict[str, object]:
        with sessions() as session:
            row = session.scalar(
                select(AgencyReceptionistSettings).where(
                    AgencyReceptionistSettings.agency_id == actor.agency_id
                )
            )
            config = VoiceLanguageConfiguration.model_validate(
                row.voice_languages if row else {}
            )
            value: dict[str, object] = dict(
                registry(settings, actor.agency_id, config)
            )
            value["row_version"] = row.row_version if row else 0
            if administrator:
                recent = session.scalars(
                    select(ConversationSession)
                    .where(ConversationSession.agency_id == actor.agency_id)
                    .order_by(ConversationSession.created_at.desc())
                    .limit(100)
                ).all()
                appointments = session.execute(
                    select(
                        HvacServiceRequest.conversation_session_id, Appointment.status
                    )
                    .join(
                        Appointment,
                        Appointment.service_request_id == HvacServiceRequest.id,
                    )
                    .where(
                        HvacServiceRequest.agency_id == actor.agency_id,
                        Appointment.agency_id == actor.agency_id,
                        HvacServiceRequest.conversation_session_id.in_(
                            [item.id for item in recent]
                        ),
                    )
                ).all()
                statuses: dict[UUID, set[str]] = {}
                for session_id, status in appointments:
                    statuses.setdefault(session_id, set()).add(status)
                diagnostics: list[dict[str, object]] = []
                for item in recent:
                    observed = statuses.get(item.id, set())
                    booking_outcome = (
                        "confirmed" if "CONFIRMED" in observed
                        else "held" if "HELD" in observed
                        else "no_confirmed_booking_observed"
                    )
                    diagnostics.append({
                        "initial_language": initial_language(item),
                        "outcome": item.status,
                        "failure_code": item.failure_code,
                        "booking_outcome": booking_outcome,
                        "source": "actual_session",
                    })
                value["diagnostics"] = diagnostics
            return value

    if administrator:

        @router.put("")
        def put_languages(
            data: LanguageSettingsInput, request: Request, actor: Actor
        ) -> dict[str, object]:
            with sessions() as session, session.begin():
                row = session.scalar(
                    select(AgencyReceptionistSettings)
                    .where(AgencyReceptionistSettings.agency_id == actor.agency_id)
                    .with_for_update()
                )
                if row is None:
                    raise ApiError(
                        status_code=409, code="RECEPTIONIST_SETTINGS_REQUIRED",
                        message="Save a business profile first.",
                    )
                if row.row_version != data.expected_row_version:
                    raise ApiError(
                        status_code=409, code="VOICE_LANGUAGE_VERSION_CONFLICT",
                        message="Settings changed. Reload before saving again.",
                    )
                config = VoiceLanguageConfiguration.model_validate(
                    data.model_dump(exclude={"expected_row_version"})
                )
                row.voice_languages = config.model_dump(mode="json")
                row.updated_by = actor.app_user_id
                session.add(AuditEvent(
                    agency_id=actor.agency_id,
                    actor_type="STAFF",
                    actor_user_id=actor.app_user_id,
                    event_type="VOICE_LANGUAGES_UPDATED",
                    occurred_at=datetime.now(UTC),
                    summary="Voice language configuration changed",
                    details={
                        "default_language": config.default_language,
                        "enabled_languages": config.enabled_languages,
                        "automatic_switching": config.automatic_switching,
                    },
                    correlation_id=UUID(request.state.correlation_id),
                    event_version=1,
                ))
                session.flush()
                session.refresh(row)
                return {
                    **registry(settings, actor.agency_id, config),
                    "row_version": row.row_version,
                }
    return router
