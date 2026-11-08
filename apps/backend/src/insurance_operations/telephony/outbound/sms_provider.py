from typing import Any
from urllib.parse import quote

import httpx

from insurance_operations.errors import ApiError
from insurance_operations.telephony.outbound.destinations import US_REGIONS
from insurance_operations.telephony.outbound.settings import OutboundDemoSettings


def sms_unavailable() -> ApiError:
    return ApiError(
        status_code=503, code="DEMO_SMS_UNAVAILABLE",
        message="Phone verification is unavailable. Please try again later.",
    )


class TelnyxVerificationProvider:
    def __init__(
        self, settings: OutboundDemoSettings, client: httpx.Client | None = None
    ) -> None:
        self.settings = settings
        self.client = client

    def _request(
        self, method: str, path: str, payload: dict[str, object] | None = None,
        *, invalid_code: bool = False,
    ) -> dict[str, Any]:
        key = self.settings.telnyx_verify_api_key
        if key is None:
            raise sms_unavailable()
        client = self.client or httpx.Client(
            base_url="https://api.telnyx.com", timeout=12, follow_redirects=False
        )
        try:
            response = client.request(
                method, path, json=payload,
                headers={"Authorization": f"Bearer {key.get_secret_value()}"},
            )
            if invalid_code and response.status_code in {400, 404}:
                return {"response_code": "rejected"}
            response.raise_for_status()
            body = response.json()
            data = body.get("data") if isinstance(body, dict) else None
            if not isinstance(data, dict):
                raise sms_unavailable()
            return data
        except (httpx.HTTPError, ValueError, TypeError):
            raise sms_unavailable() from None
        finally:
            if self.client is None:
                client.close()

    def send(self, number: str) -> str:
        lookup = self._request(
            "GET", f"/v2/number_lookup/{quote(number, safe='')}?type=carrier"
        )
        carrier = lookup.get("carrier")
        if (
            lookup.get("phone_number") != number
            or lookup.get("country_code") not in US_REGIONS
            or not isinstance(carrier, dict)
            or carrier.get("error_code") is not None
        ):
            raise ApiError(
                status_code=422, code="DEMO_SMS_NUMBER_UNSUPPORTED",
                message="Use a US phone number that can receive text messages.",
            )
        data = self._request(
            "POST", "/v2/verifications/sms",
            {
                "phone_number": number,
                "verify_profile_id": str(self.settings.telnyx_verify_profile_id),
                "timeout_secs": self.settings.outbound_demo_sms_ttl_seconds,
            },
        )
        verification_id = data.get("id")
        if (
            not isinstance(verification_id, str)
            or not 1 <= len(verification_id) <= 200
            or data.get("phone_number") != number
            or data.get("type") != "sms"
            or data.get("status") != "pending"
            or data.get("verify_profile_id")
            != str(self.settings.telnyx_verify_profile_id)
        ):
            raise sms_unavailable()
        return verification_id

    def verify(self, verification_id: str, code: str) -> str | None:
        data = self._request(
            "POST",
            f"/v2/verifications/{quote(verification_id, safe='')}/actions/verify",
            {"code": code},
            invalid_code=True,
        )
        if data.get("response_code") in {
            "rejected", "expired", "max_attempts_exceeded",
        }:
            return None
        number = data.get("phone_number")
        if data.get("response_code") != "accepted" or not isinstance(number, str):
            raise sms_unavailable()
        return number
