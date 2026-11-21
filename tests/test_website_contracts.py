import pytest
from pydantic import ValidationError

from insurance_operations.settings import ApiSettings
from insurance_operations.websites.schemas import (
    WebsiteDocument,
    WebsiteSave,
    WebsiteSessionCreateInput,
)


@pytest.mark.parametrize(
    "field,value",
    [
        ("slug", "../other"),
        ("agentConfigurationRef", "arbitrary-agent"),
        ("templateId", "unknown"),
    ],
)
def test_invalid_configuration(
    website_document: WebsiteDocument, field: str, value: str
) -> None:
    data = website_document.model_dump()
    data[field] = value
    with pytest.raises(ValidationError):
        WebsiteDocument.model_validate(data)


def test_unknown_provider_and_business_fields_are_rejected(
    website_document: WebsiteDocument,
) -> None:
    for field in ("agent_id", "business_id", "agency_id", "api_key"):
        with pytest.raises(ValidationError):
            WebsiteSave.model_validate(
                {
                    "configuration": website_document.model_dump(),
                    "status": "draft",
                    "expected_row_version": 0,
                    field: "foreign",
                }
            )
        with pytest.raises(ValidationError):
            WebsiteSessionCreateInput.model_validate(
                {
                    "input_mode": "TEXT",
                    "ai_disclosure_accepted": True,
                    "microphone_consent_granted": False,
                    field: "foreign",
                }
            )


def test_section_asset_url_and_color_validation(
    website_document: WebsiteDocument,
) -> None:
    for mutate in (
        lambda data: data.update(sections=["hero", "hero", "contact"]),
        lambda data: data["hero"].update(image="https://unapproved.example/image.svg"),
        lambda data: data["appearance"]["light"].update(accent="red;script()"),
        lambda data: data["brand"].update(name="Unsafe\nname"),
        lambda data: data["actions"]["primary"].update(
            destination={"kind": "url", "href": "/book?agent_id=foreign"}
        ),
        lambda data: data["actions"]["primary"].update(
            destination={"kind": "url", "href": "javascript:alert(1)"}
        ),
    ):
        data = website_document.model_dump()
        mutate(data)
        with pytest.raises(ValidationError):
            WebsiteDocument.model_validate(data)


def test_website_identity_does_not_require_a_default_hvac_agent() -> None:
    from uuid import uuid4

    from cryptography.fernet import Fernet

    settings = ApiSettings(
        _env_file=None,
        app_environment="development",
        database_url="postgresql://127.0.0.1/synthetic",
        api_host="127.0.0.1",
        api_port=8000,
        website_platform_enabled=True,
        customer_portal_enabled=True,
        demo_sandbox_enabled=True,
        development_actor_user_id=uuid4(),
        demo_admin_token="synthetic-admin-token-at-least-32-characters",
        customer_portal_secret="synthetic-portal-key-at-least-32-characters",
        customer_mfa_encryption_key=Fernet.generate_key().decode(),
    )
    assert settings.elevenlabs_agent_id is None
    assert settings.conversation_ai_enabled is False
