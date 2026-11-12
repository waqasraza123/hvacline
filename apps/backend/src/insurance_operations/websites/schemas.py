import re
from typing import Annotated, Literal, Self
from urllib.parse import unquote, urlsplit
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from insurance_operations.conversations.schemas import (
    ConversationIntakeConfirmationInput,
    ConversationSessionCreateInput,
)


class WebsiteSessionCreateInput(ConversationSessionCreateInput):
    model_config = ConfigDict(extra="forbid")


class WebsiteInquiry(ConversationIntakeConfirmationInput):
    service: None = None
    spoken_confirmation: Literal[False] = False
    explicit_confirmation: Literal[True]


Section = Literal[
    "hero", "services", "showcase", "story", "process", "voice", "faq", "contact"
]
Asset = Literal[
    "hvac-mark",
    "estate-mark",
    "calm-mark",
    "hvac-equipment",
    "courtyard-home",
    "city-residence",
    "calm-studio",
]
Font = Literal["system", "industrial", "serif", "humanist"]
HexColor = Annotated[str, StringConstraints(pattern=r"^#[a-fA-F0-9]{6}$")]


class StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid", str_strip_whitespace=True, str_min_length=1, str_max_length=800
    )

    @model_validator(mode="before")
    @classmethod
    def reject_control_characters(cls, value: object) -> object:
        if isinstance(value, dict):
            for field in value.values():
                if isinstance(field, str) and re.search(r"[\x00-\x1f\x7f]", field):
                    raise ValueError("Text cannot contain control characters")
        return value


class Colors(StrictModel):
    background: HexColor
    surface: HexColor
    foreground: HexColor
    muted: HexColor
    accent: HexColor
    accentInk: HexColor
    border: HexColor


class Appearance(StrictModel):
    light: Colors
    dark: Colors
    headingFont: Font
    bodyFont: Font
    spacing: Literal["compact", "balanced", "airy"]


class Brand(StrictModel):
    name: str = Field(max_length=70)
    tagline: str = Field(max_length=100)
    logo: Asset
    favicon: Asset


class SectionDestination(StrictModel):
    kind: Literal["section"]
    section: Section


class UrlDestination(StrictModel):
    kind: Literal["url"]
    href: str = Field(max_length=500)

    @field_validator("href")
    @classmethod
    def safe_url(cls, value: str) -> str:
        if re.search(r"[\s\\\x00-\x1f\x7f]", value) or re.search(
            r"%(?:0[0-9a-f]|1[0-9a-f]|7f|2f|5c)", value, re.I
        ):
            raise ValueError("Unsafe URL")
        parsed = urlsplit(value)
        if value.startswith("/") and not value.startswith("//"):
            if parsed.query or re.search(
                r"(?:^|/)\.{1,2}(?:/|$)", unquote(parsed.path)
            ):
                raise ValueError("Local URLs cannot contain queries or traversal")
        elif (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.port
        ):
            raise ValueError("External URLs require HTTPS without credentials or ports")
        return value


class VoiceDestination(StrictModel):
    kind: Literal["voice"]


class Action(StrictModel):
    label: str = Field(max_length=70)
    destination: Annotated[
        SectionDestination | UrlDestination | VoiceDestination,
        Field(discriminator="kind"),
    ]


class Actions(StrictModel):
    primary: Action
    secondary: Action


class Navigation(StrictModel):
    label: str = Field(max_length=40)
    section: Section


class Header(StrictModel):
    navigation: list[Navigation] = Field(min_length=1, max_length=5)


class Hero(StrictModel):
    eyebrow: str = Field(max_length=90)
    title: str = Field(max_length=160)
    description: str
    image: Asset
    imageCaption: str = Field(max_length=180)


class Content(StrictModel):
    title: str = Field(max_length=140)
    description: str


class Showcase(Content):
    image: Asset
    label: str = Field(max_length=80)


class Story(Content):
    eyebrow: str = Field(max_length=90)
    image: Asset


class Example(StrictModel):
    role: Literal["visitor", "assistant"]
    text: str = Field(max_length=500)


class Voice(Content):
    examples: list[Example] = Field(min_length=2, max_length=6)


class Faq(StrictModel):
    question: str = Field(max_length=180)
    answer: str


class Contact(StrictModel):
    title: str = Field(max_length=140)
    description: str
    location: str = Field(max_length=160)
    hours: str = Field(max_length=160)
    email: str | None
    phone: str | None

    @model_validator(mode="after")
    def contact_valid(self) -> Self:
        if self.email and not re.fullmatch(
            r"[a-zA-Z0-9._+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", self.email
        ):
            raise ValueError("Invalid contact email")
        if self.phone and not re.fullmatch(r"\+[1-9]\d{7,14}", self.phone):
            raise ValueError("Contact phone must use E.164")
        return self


class Seo(StrictModel):
    title: str = Field(max_length=120)
    description: str = Field(max_length=240)


class WebsiteDocument(StrictModel):
    slug: str = Field(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$", max_length=64)
    templateId: Literal["industrial", "editorial", "calm"]
    status: Literal["demo", "published"]
    industry: str = Field(max_length=60)
    designStyle: str = Field(max_length=60)
    summary: str = Field(max_length=220)
    brand: Brand
    appearance: Appearance
    sections: list[Section] = Field(min_length=3, max_length=12)
    header: Header
    hero: Hero
    actions: Actions
    services: list[Content] = Field(min_length=1, max_length=6)
    showcase: list[Showcase] = Field(max_length=4)
    story: Story
    process: list[Content] = Field(min_length=1, max_length=5)
    voice: Voice
    faqs: list[Faq] = Field(min_length=1, max_length=8)
    contact: Contact
    seo: Seo
    agentConfigurationRef: Literal["server-managed"]

    @model_validator(mode="after")
    def compatible(self) -> Self:
        supported = {
            "industrial": {"hero", "services", "process", "voice", "faq", "contact"},
            "editorial": {
                "hero",
                "services",
                "showcase",
                "story",
                "voice",
                "faq",
                "contact",
            },
            "calm": {"hero", "services", "process", "voice", "faq", "contact"},
        }[self.templateId]
        if (
            len(set(self.sections)) != len(self.sections)
            or not {"hero", "voice", "contact"}.issubset(self.sections)
            or not set(self.sections).issubset(supported)
        ):
            raise ValueError("Unsupported, duplicate or missing template sections")
        if self.templateId == "editorial" and (
            "showcase" not in self.sections or not self.showcase
        ):
            raise ValueError("Editorial websites require a property showcase")
        for link in self.header.navigation:
            if link.section not in self.sections:
                raise ValueError("Navigation targets a missing section")
        for action in (self.actions.primary, self.actions.secondary):
            if (
                isinstance(action.destination, SectionDestination)
                and action.destination.section not in self.sections
            ):
                raise ValueError("Action targets a missing section")
        return self


class WebsiteSave(StrictModel):
    expected_row_version: int = Field(ge=0)
    configuration: WebsiteDocument
    status: Literal["draft", "published", "disabled"]
    agent_binding_id: UUID | None = None
    knowledge_faq_ids: list[UUID] = Field(default_factory=list, max_length=100)
    voice_enabled: bool = False
    lead_capture_enabled: bool = False

    @model_validator(mode="after")
    def unique_knowledge(self) -> Self:
        if len(set(self.knowledge_faq_ids)) != len(self.knowledge_faq_ids):
            raise ValueError("Knowledge references must be unique")
        return self
