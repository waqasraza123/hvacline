import pytest

from insurance_operations.websites.schemas import WebsiteDocument


@pytest.fixture
def website_document() -> WebsiteDocument:
    colors = {
        "background": "#fbfbf7",
        "surface": "#edf1e9",
        "foreground": "#293b32",
        "muted": "#59685e",
        "accent": "#3d5c49",
        "accentInk": "#ffffff",
        "border": "#d7dfd3",
    }
    content = {
        "title": "Synthetic studio",
        "description": "Synthetic consultation business for disposable tests.",
    }
    return WebsiteDocument.model_validate(
        {
            "slug": "synthetic-studio",
            "templateId": "calm",
            "status": "published",
            "industry": "Appointments",
            "designStyle": "Calm",
            "summary": "Synthetic website",
            "brand": {
                "name": "Synthetic Studio",
                "tagline": "Test studio",
                "logo": "calm-mark",
                "favicon": "calm-mark",
            },
            "appearance": {
                "light": colors,
                "dark": colors,
                "headingFont": "humanist",
                "bodyFont": "system",
                "spacing": "airy",
            },
            "sections": ["hero", "services", "process", "voice", "faq", "contact"],
            "header": {"navigation": [{"label": "Services", "section": "services"}]},
            "hero": {
                **content,
                "eyebrow": "Welcome",
                "image": "calm-studio",
                "imageCaption": "Illustration",
            },
            "actions": {
                "primary": {"label": "Talk", "destination": {"kind": "voice"}},
                "secondary": {
                    "label": "Services",
                    "destination": {"kind": "section", "section": "services"},
                },
            },
            "services": [content],
            "showcase": [],
            "story": {**content, "eyebrow": "Our story", "image": "calm-studio"},
            "process": [content],
            "voice": {
                **content,
                "examples": [
                    {"role": "visitor", "text": "What sessions are offered?"},
                    {
                        "role": "assistant",
                        "text": "Please review the approved studio information.",
                    },
                ],
            },
            "faqs": [{"question": "What is this?", "answer": "Synthetic data."}],
            "contact": {
                **content,
                "location": "Fictional studio",
                "hours": "By request",
                "email": None,
                "phone": None,
            },
            "seo": content,
            "agentConfigurationRef": "server-managed",
        }
    )
