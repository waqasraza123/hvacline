import json
from uuid import uuid4

import httpx
import pytest
from pydantic import ValidationError

from insurance_operations.errors import ApiError
from insurance_operations.telephony.outbound.settings import OutboundDemoSettings
from insurance_operations.telephony.outbound.sms_provider import (
    TelnyxVerificationProvider,
)
from insurance_operations.telephony.outbound.verification_schemas import SmsStartInput

NUMBER = "+12025550123"


@pytest.fixture
def config(monkeypatch: pytest.MonkeyPatch) -> OutboundDemoSettings:
    for field in OutboundDemoSettings.model_fields:
        monkeypatch.delenv(field.upper(), raising=False)
    return OutboundDemoSettings(
        _env_file=None,
        app_environment="test",
        telnyx_verify_api_key="synthetic-verify-key",
        telnyx_verify_profile_id=uuid4(),
    )


@pytest.mark.parametrize(
    "lookup",
    [
        {"phone_number": "+12125550123", "country_code": "US", "carrier": {}},
        {"phone_number": NUMBER, "country_code": "CA", "carrier": {}},
        {"phone_number": NUMBER, "country_code": None, "carrier": {}},
        {"phone_number": NUMBER, "country_code": "US", "carrier": None},
        {"phone_number": NUMBER, "country_code": "US", "carrier": []},
        {
            "phone_number": NUMBER,
            "country_code": "US",
            "carrier": {
                "type": "voip",
                "error_code": "synthetic-carrier-error",
            },
        },
    ],
)
def test_invalid_lookup_never_sends_an_sms(
    config: OutboundDemoSettings,
    lookup: dict[str, object],
) -> None:
    requests: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"data": lookup})

    with (
        httpx.Client(
            base_url="https://api.telnyx.com", transport=httpx.MockTransport(respond)
        ) as client,
        pytest.raises(ApiError) as caught,
    ):
        TelnyxVerificationProvider(config, client).send(NUMBER)
    assert caught.value.code == "DEMO_SMS_NUMBER_UNSUPPORTED"
    assert len(requests) == 1
    assert requests[0].method == "GET"


@pytest.mark.parametrize("line_type", ["mobile", "landline", "voip", None, "unknown"])
def test_sms_accepts_line_types_but_requires_provider_code_verification(
    config: OutboundDemoSettings,
    line_type: str | None,
) -> None:
    verification_id = str(uuid4())
    requests: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "GET":
            return httpx.Response(
                200,
                json={
                    "data": {
                        "phone_number": NUMBER,
                        "country_code": "US",
                        "carrier": {"type": line_type, "error_code": None},
                    }
                },
            )
        if request.url.path.endswith("/sms"):
            body = json.loads(request.content)
            assert "custom_code" not in body
            assert "status" not in body
            return httpx.Response(
                200,
                json={
                    "data": {
                        "id": verification_id,
                        "phone_number": NUMBER,
                        "type": "sms",
                        "status": "pending",
                        "verify_profile_id": str(config.telnyx_verify_profile_id),
                    }
                },
            )
        assert request.url.path == (
            f"/v2/verifications/{verification_id}/actions/verify"
        )
        assert json.loads(request.content) == {"code": "123456"}
        return httpx.Response(
            200,
            json={
                "data": {
                    "phone_number": NUMBER,
                    "response_code": "accepted",
                }
            },
        )

    with httpx.Client(
        base_url="https://api.telnyx.com", transport=httpx.MockTransport(respond)
    ) as client:
        provider = TelnyxVerificationProvider(config, client)
        assert provider.send(NUMBER) == verification_id
        assert provider.verify(verification_id, "123456") == NUMBER
    assert len(requests) == 3


@pytest.mark.parametrize(
    "response",
    [
        {"data": {"phone_number": NUMBER, "response_code": "rejected"}},
        {"data": {"phone_number": NUMBER, "response_code": "expired"}},
    ],
)
def test_invalid_codes_never_produce_proof(
    config: OutboundDemoSettings,
    response: dict[str, object],
) -> None:
    with httpx.Client(
        base_url="https://api.telnyx.com",
        transport=httpx.MockTransport(
            lambda _: httpx.Response(200, json=response),
        ),
    ) as client:
        provider = TelnyxVerificationProvider(config, client)
        assert provider.verify(str(uuid4()), "123456") is None


def test_provider_failure_is_sanitized_and_never_retried(
    config: OutboundDemoSettings,
) -> None:
    requests: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        raise httpx.ReadTimeout("private diagnostic", request=request)

    with (
        httpx.Client(
            base_url="https://api.telnyx.com", transport=httpx.MockTransport(respond)
        ) as client,
        pytest.raises(ApiError) as caught,
    ):
        TelnyxVerificationProvider(config, client).verify(str(uuid4()), "123456")
    assert caught.value.code == "DEMO_SMS_UNAVAILABLE"
    assert NUMBER not in caught.value.message
    assert "private diagnostic" not in caught.value.message
    assert len(requests) == 1


@pytest.mark.parametrize("consent", [False, 1, "true", None])
def test_sms_requires_explicit_versioned_consent(consent: object) -> None:
    with pytest.raises(ValidationError):
        SmsStartInput.model_validate(
            {
                "phone_number": NUMBER,
                "sms_consent": consent,
                "sms_consent_version": "outbound-sms-v1",
            }
        )
