import base64
import hashlib
import json
import secrets
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from urllib.parse import quote, urlencode

import httpx
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.orm import Session

from insurance_operations.database.models.booking_integrations import CalendarConnection
from insurance_operations.hvac.calendar import (
    CalendarAuthorizationRequired,
    CalendarUnavailable,
    GoogleCalendarAdapter,
)
from insurance_operations.job_execution import provider_client
from insurance_operations.settings import DatabaseSettings

SCOPES = (
    "https://www.googleapis.com/auth/calendar.events "
    "https://www.googleapis.com/auth/calendar.calendarlist.readonly"
)


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def integration_settings(session: Session) -> DatabaseSettings:
    settings = session.info.get("integration_settings")
    if not isinstance(settings, DatabaseSettings):
        raise CalendarUnavailable("Calendar runtime is not configured")
    return settings


class TokenVault:
    def __init__(self, settings: DatabaseSettings) -> None:
        if (
            not settings.google_calendar_enabled
            or settings.calendar_token_encryption_key is None
        ):
            raise CalendarUnavailable("Google Calendar is not enabled")
        self.cipher = Fernet(
            settings.calendar_token_encryption_key.get_secret_value().encode()
        )

    def encrypt(self, value: str, context: str) -> str:
        return self.cipher.encrypt(
            json.dumps({"context": context, "value": value}).encode()
        ).decode()

    def decrypt(self, value: str, context: str) -> str:
        try:
            data = json.loads(self.cipher.decrypt(value.encode()))
            if data["context"] != context or not isinstance(data["value"], str):
                raise ValueError("token context differs")
            return str(data["value"])
        except (InvalidToken, ValueError, KeyError, TypeError) as error:
            raise CalendarUnavailable(
                "Calendar credentials could not be decrypted"
            ) from error


class GoogleOAuth:
    def __init__(self, settings: DatabaseSettings, client: httpx.Client) -> None:
        self.settings = settings
        self.client = client
        self.vault = TokenVault(settings)

    def authorization_url(self, state: str, verifier: str) -> str:
        challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
            .rstrip(b"=")
            .decode()
        )
        return "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(
            {
                "client_id": self.settings.google_client_id,
                "redirect_uri": self.settings.google_redirect_uri,
                "response_type": "code",
                "scope": SCOPES,
                "state": state,
                "access_type": "offline",
                "prompt": "consent",
                "code_challenge": challenge,
                "code_challenge_method": "S256",
            }
        )

    def tokens(self, values: dict[str, str]) -> dict[str, object]:
        secret = self.settings.google_client_secret
        if secret is None or not self.settings.google_client_id:
            raise CalendarUnavailable("Google OAuth is not configured")
        try:
            response = self.client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    **values,
                    "client_id": self.settings.google_client_id,
                    "client_secret": secret.get_secret_value(),
                },
                timeout=10,
            )
            if response.status_code in {400, 401}:
                raise CalendarAuthorizationRequired(
                    "Google authorization must be renewed"
                )
            response.raise_for_status()
            data = response.json()
            if (
                not isinstance(data, dict)
                or not isinstance(data.get("access_token"), str)
                or not data["access_token"]
            ):
                raise ValueError("access token missing")
            lifetime = int(str(data.get("expires_in", 300)))
            if lifetime <= 0 or lifetime > 86400:
                raise ValueError("invalid token lifetime")
            return data
        except (httpx.HTTPError, ValueError) as error:
            raise CalendarUnavailable(
                "Google authorization is temporarily unavailable"
            ) from error

    def calendar(self, access_token: str, calendar_id: str) -> str:
        try:
            response = self.client.get(
                "https://www.googleapis.com/calendar/v3/users/me/calendarList/"
                + quote(calendar_id, safe=""),
                headers={"Authorization": "Bearer " + access_token},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            if (
                data.get("accessRole") not in {"owner", "writer"}
                or not isinstance(data.get("id"), str)
                or not data["id"]
                or data.get("deleted")
            ):
                raise ValueError("writable calendar required")
            return str(data["id"])
        except (httpx.HTTPError, ValueError, AttributeError) as error:
            raise CalendarUnavailable(
                "Select a Google calendar with write access"
            ) from error


@contextmanager
def calendar_adapter(
    session: Session, connection: CalendarConnection
) -> Iterator[GoogleCalendarAdapter]:
    if connection.status != "CONNECTED":
        raise CalendarAuthorizationRequired(
            "Reconnect this team's Google Calendar before booking"
        )
    settings = integration_settings(session)
    with provider_client() as client:
        oauth = GoogleOAuth(settings, client)
        context = f"{connection.agency_id}:{connection.team_key}"
        refresh_token = oauth.vault.decrypt(
            connection.refresh_token_ciphertext, context
        )
        token: str | None = None
        expires_at = datetime.now(UTC)

        def access_token() -> str:
            nonlocal token, expires_at, refresh_token
            if token is None or datetime.now(UTC) >= expires_at:
                data = oauth.tokens(
                    {"grant_type": "refresh_token", "refresh_token": refresh_token}
                )
                token = str(data["access_token"])
                expires_at = datetime.now(UTC) + timedelta(
                    seconds=max(1, int(str(data.get("expires_in", 300))) - 30)
                )
                rotated = data.get("refresh_token")
                if isinstance(rotated, str) and rotated:
                    refresh_token = rotated
                    connection.refresh_token_ciphertext = oauth.vault.encrypt(
                        rotated, context
                    )
            return token

        yield GoogleCalendarAdapter(
            calendar_id=connection.calendar_id, access_token=access_token, client=client
        )


def authorization_values() -> tuple[str, str, str]:
    return (
        secrets.token_urlsafe(32),
        secrets.token_urlsafe(32),
        secrets.token_urlsafe(64),
    )
