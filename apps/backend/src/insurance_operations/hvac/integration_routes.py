import secrets
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from html import escape
from typing import Annotated
from urllib.parse import parse_qs, urlsplit
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.actors import (
    ActorContext,
    ActorResolutionError,
    resolve_development_actor,
)
from insurance_operations.database.models.booking_integrations import (
    BookingNotification,
    CalendarAuthorization,
    CalendarBooking,
    CalendarConnection,
)
from insurance_operations.database.models.hvac import Appointment
from insurance_operations.errors import ApiError
from insurance_operations.hvac.calendar import CalendarUnavailable
from insurance_operations.hvac.google_connection import (
    SCOPES,
    GoogleOAuth,
    TokenVault,
    authorization_values,
    digest,
)
from insurance_operations.hvac.locking import lock_business_schedule
from insurance_operations.hvac.schemas import ScheduleInput
from insurance_operations.settings import ApiSettings
from insurance_operations.telephony.phone_service import system_audit

PREFIX = "/api/v1/development/hvac/integrations"


class GoogleConnectionInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    team_key: str = Field(pattern=r"^[a-z0-9-]{1,40}$")
    calendar_id: str = Field(min_length=1, max_length=1024)


def integration_error(message: str) -> ApiError:
    return ApiError(
        status_code=409, code="CALENDAR_CONNECTION_UNAVAILABLE", message=message
    )


def lock_schedule(session: Session, agency_id: UUID) -> ScheduleInput:
    schedule = lock_business_schedule(session, agency_id)
    if schedule is None:
        raise integration_error("Configure scheduling before connecting a calendar.")
    return ScheduleInput.model_validate(schedule.configuration)


def create_booking_integration_router(
    settings: ApiSettings,
    sessions: sessionmaker[Session],
    actor_dependency: Callable[..., ActorContext],
) -> APIRouter:
    router = APIRouter(prefix=PREFIX)
    Actor = Annotated[ActorContext, Depends(actor_dependency)]

    @router.get("")
    def status(actor: Actor, response: Response) -> dict[str, object]:
        response.headers["Cache-Control"] = "no-store"
        with sessions() as session:
            return {
                "google_enabled": settings.google_calendar_enabled,
                "email_enabled": settings.booking_email_enabled,
                "connections": [
                    {
                        "id": str(row.id),
                        "team_key": row.team_key,
                        "calendar_id": row.calendar_id,
                        "status": row.status,
                        "last_checked_at": row.last_checked_at,
                        "last_error": row.last_error,
                    }
                    for row in session.scalars(
                        select(CalendarConnection).where(
                            CalendarConnection.agency_id == actor.agency_id
                        )
                    )
                ],
                "sync": [
                    {
                        "appointment_id": str(row.appointment_id),
                        "status": row.status,
                        "last_error": row.last_error,
                    }
                    for row in session.scalars(
                        select(CalendarBooking)
                        .where(CalendarBooking.agency_id == actor.agency_id)
                        .order_by(CalendarBooking.next_attempt_at)
                        .limit(100)
                    )
                ],
                "notifications": [
                    {
                        "id": str(row.id),
                        "appointment_id": str(row.appointment_id),
                        "kind": row.kind,
                        "status": row.status,
                        "due_at": row.due_at,
                        "attempts": row.attempts,
                        "delivery_status": row.delivery_status,
                        "last_error": row.last_error,
                    }
                    for row in session.scalars(
                        select(BookingNotification)
                        .where(BookingNotification.agency_id == actor.agency_id)
                        .order_by(BookingNotification.due_at.desc())
                        .limit(100)
                    )
                ],
            }

    @router.post("/google/authorize")
    def authorize(
        data: GoogleConnectionInput, actor: Actor, response: Response
    ) -> dict[str, str]:
        response.headers["Cache-Control"] = "no-store"
        try:
            vault = TokenVault(settings)
            state, browser_secret, verifier = authorization_values()
            with sessions() as session, session.begin():
                configuration = lock_schedule(session, actor.agency_id)
                if data.team_key not in {team.key for team in configuration.teams}:
                    raise integration_error("Select a configured team.")
                session.execute(
                    delete(CalendarAuthorization).where(
                        CalendarAuthorization.expires_at <= datetime.now(UTC)
                    )
                )
                session.execute(
                    delete(CalendarAuthorization).where(
                        CalendarAuthorization.agency_id == actor.agency_id,
                        CalendarAuthorization.actor_id == actor.app_user_id,
                    )
                )
                session.add(
                    CalendarAuthorization(
                        agency_id=actor.agency_id,
                        actor_id=actor.app_user_id,
                        state_digest=digest(state),
                        browser_digest=digest(browser_secret),
                        verifier_ciphertext=vault.encrypt(verifier, digest(state)),
                        team_key=data.team_key,
                        calendar_id=data.calendar_id,
                        expires_at=datetime.now(UTC) + timedelta(minutes=10),
                    )
                )
            uri = urlsplit(settings.google_redirect_uri or "")
            return {
                "state": state,
                "browser_secret": browser_secret,
                "launch_url": f"{uri.scheme}://{uri.netloc}{PREFIX}/google/launch",
            }
        except CalendarUnavailable as error:
            raise integration_error(str(error)) from error

    @router.post("/google/launch", include_in_schema=False)
    async def launch(request: Request) -> Response:
        if (
            request.headers.get("origin") != settings.web_origin
            or not settings.google_calendar_enabled
        ):
            raise integration_error(
                "Start the connection from the operations workspace."
            )
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > 2048:
                raise integration_error("Calendar authorization is invalid.")
        values = parse_qs(body.decode("utf-8", errors="replace"))
        state = values.get("state", [""])[0]
        browser_secret = values.get("browser_secret", [""])[0]
        with sessions() as session:
            row = session.scalar(
                select(CalendarAuthorization).where(
                    CalendarAuthorization.state_digest == digest(state)
                )
            )
            if (
                row is None
                or row.expires_at <= datetime.now(UTC)
                or not secrets.compare_digest(
                    row.browser_digest, digest(browser_secret)
                )
            ):
                raise integration_error("Calendar authorization expired. Start again.")
            with httpx.Client() as client:
                oauth = GoogleOAuth(settings, client)
                url = oauth.authorization_url(
                    state, oauth.vault.decrypt(row.verifier_ciphertext, digest(state))
                )
        response = RedirectResponse(
            url,
            status_code=303,
            headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"},
        )
        response.set_cookie(
            "hvacline_google_" + digest(state)[:16],
            browser_secret,
            max_age=600,
            secure=(urlsplit(settings.google_redirect_uri or "").scheme == "https"),
            httponly=True,
            samesite="lax",
            path=PREFIX + "/google/callback",
        )
        return response

    @router.get("/google/callback", include_in_schema=False)
    def callback(
        request: Request, state: str = "", code: str = "", error: str = ""
    ) -> Response:
        cookie = "hvacline_google_" + digest(state)[:16]
        try:
            with sessions() as session, session.begin():
                row = session.scalar(
                    select(CalendarAuthorization)
                    .where(CalendarAuthorization.state_digest == digest(state))
                    .with_for_update()
                )
                if (
                    row is None
                    or row.expires_at <= datetime.now(UTC)
                    or not secrets.compare_digest(
                        row.browser_digest, digest(request.cookies.get(cookie, ""))
                    )
                ):
                    raise integration_error(
                        "Calendar authorization expired. Start again."
                    )
                actor = resolve_development_actor(session, row.actor_id)
                if actor.agency_id != row.agency_id:
                    raise integration_error(
                        "Calendar authorization is no longer valid."
                    )
                agency_id, team_key, calendar_id = (
                    row.agency_id,
                    row.team_key,
                    row.calendar_id,
                )
                verifier = TokenVault(settings).decrypt(
                    row.verifier_ciphertext, digest(state)
                )
                session.delete(row)
            if error or not code or len(code) > 4096:
                raise integration_error(
                    "Google authorization was not completed. Start again."
                )
            with httpx.Client() as client:
                oauth = GoogleOAuth(settings, client)
                tokens = oauth.tokens(
                    {
                        "grant_type": "authorization_code",
                        "code": code,
                        "redirect_uri": settings.google_redirect_uri or "",
                        "code_verifier": verifier,
                    }
                )
                granted = set(str(tokens.get("scope", "")).split())
                if not set(SCOPES.split()).issubset(granted):
                    raise integration_error(
                        "Grant both calendar permissions before connecting."
                    )
                resolved_id = oauth.calendar(str(tokens["access_token"]), calendar_id)
                refresh = tokens.get("refresh_token")
                if not isinstance(refresh, str) or not refresh:
                    raise integration_error(
                        "Google did not grant offline access. Reconnect with consent."
                    )
                encrypted = oauth.vault.encrypt(refresh, f"{agency_id}:{team_key}")
            with sessions() as session, session.begin():
                configuration = lock_schedule(session, agency_id)
                current_actor = resolve_development_actor(session, actor.app_user_id)
                if current_actor.agency_id != agency_id:
                    raise integration_error(
                        "Calendar authorization is no longer valid."
                    )
                if team_key not in {team.key for team in configuration.teams}:
                    raise integration_error("The selected team no longer exists.")
                connection = session.scalar(
                    select(CalendarConnection).where(
                        CalendarConnection.agency_id == agency_id,
                        CalendarConnection.team_key == team_key,
                    )
                )
                other = session.scalar(
                    select(CalendarConnection).where(
                        CalendarConnection.agency_id == agency_id,
                        CalendarConnection.calendar_id == resolved_id,
                        CalendarConnection.team_key != team_key,
                    )
                )
                if other:
                    raise integration_error(
                        "That calendar is already assigned to another team."
                    )
                active = session.scalar(
                    select(Appointment.id)
                    .where(
                        Appointment.agency_id == agency_id,
                        Appointment.team_key == team_key,
                        (
                            (Appointment.status == "CONFIRMED")
                            & (Appointment.ends_at > datetime.now(UTC))
                        )
                        | (
                            (Appointment.status == "HELD")
                            & (Appointment.hold_expires_at > datetime.now(UTC))
                        ),
                    )
                    .limit(1)
                )
                pending = (
                    session.scalar(
                        select(CalendarBooking.appointment_id)
                        .where(
                            CalendarBooking.connection_id == connection.id,
                            CalendarBooking.status.not_in(["CANCELLED", "COMPLETED"]),
                        )
                        .limit(1)
                    )
                    if connection
                    else None
                )
                if (active or pending) and (
                    connection is None or connection.calendar_id != resolved_id
                ):
                    raise integration_error(
                        "Finish existing bookings and calendar cleanup before changing this team's calendar."
                    )
                if connection is None:
                    connection = CalendarConnection(
                        agency_id=agency_id,
                        team_key=team_key,
                        calendar_id=resolved_id,
                        refresh_token_ciphertext=encrypted,
                        status="CONNECTED",
                    )
                    session.add(connection)
                else:
                    connection.calendar_id = resolved_id
                    connection.refresh_token_ciphertext = encrypted
                    connection.status = "CONNECTED"
                    connection.last_error = None
                session.add(
                    system_audit(
                        agency_id=agency_id,
                        event_type="HVAC_CALENDAR_CONNECTED",
                        summary="Google Calendar connected to a team",
                        details={"team_key": team_key},
                        correlation_id=UUID(request.state.correlation_id),
                    )
                )
            message = "Google Calendar connected. Close this tab and refresh Scheduling in your operations workspace."
        except (CalendarUnavailable, ApiError) as failure:
            message = (
                "Google Calendar was not connected. "
                + str(failure)
                + " Close this tab and return to Scheduling. Existing bookings were preserved."
            )
        except ActorResolutionError:
            message = "Google Calendar was not connected. Close this tab, refresh Scheduling, and start again. Existing bookings were preserved."
        response = HTMLResponse(
            "<!doctype html><html lang='en'><meta name='referrer' content='no-referrer'><title>Calendar connection</title><body><p>"
            + escape(message)
            + "</p></body></html>",
            headers={
                "Cache-Control": "no-store",
                "Referrer-Policy": "no-referrer",
                "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
            },
        )
        response.delete_cookie(cookie, path=PREFIX + "/google/callback")
        return response

    @router.post("/google/{connection_id}/disconnect")
    def disconnect(
        connection_id: UUID, actor: Actor, request: Request
    ) -> dict[str, str]:
        with sessions() as session, session.begin():
            lock_schedule(session, actor.agency_id)
            connection = session.scalar(
                select(CalendarConnection).where(
                    CalendarConnection.id == connection_id,
                    CalendarConnection.agency_id == actor.agency_id,
                )
            )
            if connection is None:
                raise integration_error("Calendar connection was not found.")
            active = session.scalar(
                select(CalendarBooking.appointment_id)
                .where(
                    CalendarBooking.connection_id == connection.id,
                    CalendarBooking.status.not_in(["CANCELLED", "COMPLETED"]),
                )
                .limit(1)
            )
            if active:
                raise integration_error(
                    "Finish or cancel bookings and wait for calendar cleanup before disconnecting."
                )
            connection.status = "DISCONNECTED"
            connection.refresh_token_ciphertext = ""
            session.add(
                system_audit(
                    agency_id=actor.agency_id,
                    event_type="HVAC_CALENDAR_DISCONNECTED",
                    summary="Google Calendar disconnected; team booking paused",
                    details={"team_key": connection.team_key},
                    correlation_id=UUID(request.state.correlation_id),
                )
            )
        return {"status": "DISCONNECTED"}

    return router
