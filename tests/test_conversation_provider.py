import httpx
import pytest

from insurance_operations.conversations.contracts import (
    ConversationInputMode,
    ConversationProviderError,
)
from insurance_operations.conversations.providers.elevenlabs import (
    ELEVENLABS_API_BASE_URL,
    ElevenLabsConversationProvider,
)


def test_provider_mints_webrtc_token_without_exposing_api_key() -> None:
    captured_request: httpx.Request | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_request
        captured_request = request
        return httpx.Response(
            200,
            json={"token": "short-lived-token", "conversation_id": "conv_test"},
        )

    client = httpx.Client(
        base_url=ELEVENLABS_API_BASE_URL,
        transport=httpx.MockTransport(handler),
    )
    provider = ElevenLabsConversationProvider(
        api_key="server-only-secret",
        agent_id="agent_test",
        client=client,
    )

    grant = provider.authorize_session()

    assert grant.transport == "webrtc"
    assert grant.credential == "short-lived-token"
    assert grant.metadata.external_session_reference == "conv_test"
    assert captured_request is not None
    assert captured_request.url.path == "/v1/convai/conversation/token"
    assert captured_request.url.params["agent_id"] == "agent_test"
    assert captured_request.headers["xi-api-key"] == "server-only-secret"


@pytest.mark.parametrize("input_mode", ["VOICE", "TEXT"])
def test_provider_returns_sanitized_error_for_invalid_response(
    input_mode: ConversationInputMode,
) -> None:
    client = httpx.Client(
        base_url=ELEVENLABS_API_BASE_URL,
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(
                502,
                text="upstream detail containing server-only-secret",
            )
        ),
    )
    provider = ElevenLabsConversationProvider(
        api_key="server-only-secret",
        agent_id="agent_test",
        client=client,
    )

    with pytest.raises(ConversationProviderError) as error:
        provider.authorize_session(input_mode=input_mode)

    assert str(error.value) == "conversation provider authorization failed"
    assert "server-only-secret" not in str(error.value)


@pytest.mark.parametrize("include_reference", [True, False])
def test_text_provider_mints_signed_socket_url_without_storing_credentials(
    include_reference: bool,
) -> None:
    captured_request: httpx.Request | None = None
    signed_url = (
        "wss://api.elevenlabs.io/v1/convai/conversation"
        "?conversation_signature=private-test-signature"
    )

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_request
        captured_request = request
        body = {"signed_url": signed_url}
        if include_reference:
            body["conversation_id"] = "conv_text_test"
        return httpx.Response(200, json=body)

    provider = ElevenLabsConversationProvider(
        api_key="server-only-secret",
        agent_id="agent_test",
        client=httpx.Client(
            base_url=ELEVENLABS_API_BASE_URL,
            transport=httpx.MockTransport(handler),
        ),
    )
    grant = provider.authorize_session(input_mode="TEXT")

    assert grant.transport == "websocket"
    assert grant.credential == signed_url
    stored = grant.metadata.as_storage_value()
    assert "private-test-signature" not in str(stored)
    assert "server-only-secret" not in str(stored)
    assert stored.get("external_session_reference") == (
        "conv_text_test" if include_reference else None
    )
    assert captured_request is not None
    assert captured_request.url.path == "/v1/convai/conversation/get-signed-url"
    assert captured_request.url.params["agent_id"] == "agent_test"
    assert captured_request.url.params["include_conversation_id"] == "true"
    assert captured_request.headers["xi-api-key"] == "server-only-secret"


@pytest.mark.parametrize(
    "signed_url",
    [
        "https://api.elevenlabs.io/v1/convai/conversation?signature=private",
        "wss://untrusted.example/v1/convai/conversation?signature=private",
        "wss://api.elevenlabs.io/v1/convai/conversation",
        "wss://user:private@api.elevenlabs.io/v1/convai/conversation?signature=private",
    ],
)
def test_text_provider_rejects_invalid_urls_with_a_sanitized_error(
    signed_url: str,
) -> None:
    provider = ElevenLabsConversationProvider(
        api_key="server-only-secret",
        agent_id="agent_test",
        client=httpx.Client(
            base_url=ELEVENLABS_API_BASE_URL,
            transport=httpx.MockTransport(
                lambda _request: httpx.Response(200, json={"signed_url": signed_url})
            ),
        ),
    )
    with pytest.raises(ConversationProviderError) as error:
        provider.authorize_session(input_mode="TEXT")
    assert str(error.value) == "conversation provider authorization failed"
