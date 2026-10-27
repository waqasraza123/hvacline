import base64
import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr, ValidationError

from insurance_operations.database.models.booking_integrations import (
    BookingNotification,
)
from insurance_operations.errors import ApiError
from insurance_operations.hvac.calendar import (
    CalendarAuthorizationRequired,
    CalendarConflict,
    CalendarUnavailable,
    GoogleCalendarAdapter,
)
from insurance_operations.hvac.google_connection import GoogleOAuth, TokenVault
from insurance_operations.notifications.booking import ResendBookingEmail
from insurance_operations.notifications.email_events import verify_email_event
from insurance_operations.settings import DatabaseSettings


def integration_configuration(**overrides: object) -> DatabaseSettings:
    values: dict[str, object] = {
        "app_environment": "development",
        "database_url": "postgresql://synthetic:synthetic@localhost/development",
        "google_calendar_enabled": True,
        "booking_email_enabled": False,
        "google_client_id": "synthetic-client",
        "google_client_secret": SecretStr("synthetic-secret"),
        "google_redirect_uri": "http://localhost:8000/api/v1/development/hvac/integrations/google/callback",
        "calendar_token_encryption_key": SecretStr(Fernet.generate_key().decode()),
    }
    return DatabaseSettings.model_validate({**values, **overrides})


def test_token_vault_binds_ciphertext_to_tenant_and_team() -> None:
    vault = TokenVault(integration_configuration())
    ciphertext = vault.encrypt("synthetic-refresh", "tenant-a:team-a")
    assert "synthetic-refresh" not in ciphertext
    assert vault.decrypt(ciphertext, "tenant-a:team-a") == "synthetic-refresh"
    with pytest.raises(CalendarUnavailable):
        vault.decrypt(ciphertext, "tenant-b:team-a")


def test_google_refresh_revocation_requires_reauthorization() -> None:
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(400, json={"error": "invalid_grant"})
        )
    ) as client:
        oauth = GoogleOAuth(integration_configuration(), client)
        with pytest.raises(CalendarUnavailable, match="renewed"):
            oauth.tokens({"grant_type": "refresh_token", "refresh_token": "synthetic"})


def test_google_authorization_uses_offline_access_and_pkce() -> None:
    from urllib.parse import parse_qs, urlsplit

    with httpx.Client() as client:
        url = GoogleOAuth(integration_configuration(), client).authorization_url(
            "synthetic-state", "synthetic-verifier"
        )
    values = parse_qs(urlsplit(url).query)
    assert values["state"] == ["synthetic-state"]
    assert values["access_type"] == ["offline"]
    assert values["code_challenge_method"] == ["S256"]
    assert values["code_challenge"] == [
        base64.urlsafe_b64encode(hashlib.sha256(b"synthetic-verifier").digest())
        .rstrip(b"=")
        .decode()
    ]


def test_calendar_lists_all_pages_recurring_and_all_day_busy_times() -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        assert request.url.params["singleEvents"] == "true"
        if "pageToken" not in request.url.params:
            return httpx.Response(
                200,
                json={
                    "timeZone": "America/New_York",
                    "items": [
                        {
                            "id": "all-day",
                            "start": {"date": "2026-11-01"},
                            "end": {"date": "2026-11-02"},
                        },
                        {"id": "transparent", "transparency": "transparent"},
                    ],
                    "nextPageToken": "next",
                },
            )
        return httpx.Response(
            200,
            json={
                "timeZone": "America/New_York",
                "items": [
                    {
                        "id": "recurrence",
                        "start": {"dateTime": "2026-11-01T10:00:00-05:00"},
                        "end": {"dateTime": "2026-11-01T11:00:00-05:00"},
                    },
                ],
            },
        )

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        adapter = GoogleCalendarAdapter(
            calendar_id="synthetic", access_token=lambda: "synthetic", client=client
        )
        periods = adapter.busy_events(
            datetime(2026, 11, 1, tzinfo=UTC), datetime(2026, 11, 3, tzinfo=UTC)
        )
    assert len(periods) == 2
    assert periods[0].ends_at.astimezone(UTC) - periods[0].starts_at.astimezone(
        UTC
    ) == timedelta(hours=25)


def test_incomplete_calendar_page_fails_closed() -> None:
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={"timeZone": "UTC"})
        )
    ) as client:
        adapter = GoogleCalendarAdapter(
            calendar_id="synthetic", access_token=lambda: "synthetic", client=client
        )
        with pytest.raises(CalendarUnavailable):
            adapter.busy_events(
                datetime.now(UTC), datetime.now(UTC) + timedelta(hours=1)
            )


def test_changed_event_cannot_be_silently_overwritten() -> None:
    appointment_id = uuid4()
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200, json={"id": appointment_id.hex, "status": "cancelled"}
            )
        )
    ) as client:
        adapter = GoogleCalendarAdapter(
            calendar_id="synthetic", access_token=lambda: "synthetic", client=client
        )
        with pytest.raises(CalendarConflict):
            adapter.verify(
                appointment_id,
                datetime.now(UTC),
                datetime.now(UTC) + timedelta(hours=1),
            )


def test_owned_event_cancellation_requires_matching_etag() -> None:
    appointment_id = uuid4()
    starts_at = datetime.now(UTC) + timedelta(days=1)
    ends_at = starts_at + timedelta(hours=1)
    methods: list[str] = []

    def respond(request: httpx.Request) -> httpx.Response:
        methods.append(request.method)
        if request.method == "GET":
            return httpx.Response(
                200,
                json={
                    "id": appointment_id.hex,
                    "status": "confirmed",
                    "start": {"dateTime": starts_at.isoformat()},
                    "end": {"dateTime": ends_at.isoformat()},
                    "etag": '"version-1"',
                    "extendedProperties": {
                        "private": {"hvacline_appointment_id": str(appointment_id)}
                    },
                },
            )
        assert request.headers["If-Match"] == '"version-1"'
        return httpx.Response(412)

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        adapter = GoogleCalendarAdapter(
            calendar_id="synthetic", access_token=lambda: "synthetic", client=client
        )
        with pytest.raises(CalendarConflict):
            adapter.cancel_owned(appointment_id, starts_at, ends_at)
    assert methods == ["GET", "DELETE"]


def test_email_retries_keep_identical_payload_and_idempotency_key() -> None:
    sent: list[tuple[str, bytes]] = []

    def respond(request: httpx.Request) -> httpx.Response:
        sent.append((request.headers["Idempotency-Key"], request.content))
        return (
            httpx.Response(503)
            if len(sent) == 1
            else httpx.Response(200, json={"id": "synthetic-email"})
        )

    row = BookingNotification(
        id=uuid4(),
        payload={
            "from": "sender@example.com",
            "to": ["recipient@example.com"],
            "subject": "Synthetic booking",
            "text": "Synthetic",
        },
    )
    settings = integration_configuration(resend_api_key=SecretStr("synthetic"))
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        provider = ResendBookingEmail(settings, client)
        assert provider.send(row)[0] == "PENDING"
        assert provider.send(row) == ("ACCEPTED", "synthetic-email")
    assert sent[0] == sent[1]


@pytest.mark.parametrize(
    ("name", "outcome"),
    [
        ("concurrent_idempotent_requests", "PENDING"),
        ("invalid_idempotent_request", "FAILED"),
    ],
)
def test_email_idempotency_conflicts_are_classified(name: str, outcome: str) -> None:
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(409, json={"name": name})
        )
    ) as client:
        provider = ResendBookingEmail(
            integration_configuration(resend_api_key=SecretStr("synthetic")), client
        )
        assert provider.send(BookingNotification(id=uuid4(), payload={}))[0] == outcome


def test_signed_email_events_reject_tampering_and_stale_replays() -> None:
    now = datetime.now(UTC)
    key = b"synthetic-signing-key-not-a-live-secret"
    secret = "whsec_" + base64.b64encode(key).decode()
    body = json.dumps(
        {
            "type": "email.delivered",
            "created_at": now.isoformat(),
            "data": {"email_id": "synthetic-email"},
        }
    ).encode()
    timestamp = str(int(now.timestamp()))
    signature = base64.b64encode(
        hmac.new(
            key, b"synthetic-event." + timestamp.encode() + b"." + body, hashlib.sha256
        ).digest()
    ).decode()
    headers = {
        "svix-id": "synthetic-event",
        "svix-timestamp": timestamp,
        "svix-signature": "v1," + signature,
    }
    event = verify_email_event(body, headers, secret, now)
    assert event and event.status == "DELIVERED"
    with pytest.raises(ApiError):
        verify_email_event(body + b" ", headers, secret, now)
    with pytest.raises(ApiError):
        verify_email_event(body, headers, secret, now + timedelta(minutes=6))


def test_integrations_remain_disabled_for_production_identity() -> None:
    with pytest.raises(ValidationError, match="development identity"):
        integration_configuration(app_environment="production")


def test_google_quota_failure_does_not_discard_calendar_authorization() -> None:
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                403, json={"error": {"errors": [{"reason": "rateLimitExceeded"}]}}
            )
        )
    ) as client:
        adapter = GoogleCalendarAdapter(
            calendar_id="synthetic", access_token=lambda: "synthetic", client=client
        )
        with pytest.raises(CalendarUnavailable) as error:
            adapter.busy_events(
                datetime.now(UTC), datetime.now(UTC) + timedelta(hours=1)
            )
    assert not isinstance(error.value, CalendarAuthorizationRequired)
