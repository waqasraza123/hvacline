import base64
import binascii
import hashlib
import hmac
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import APIRouter, Request, Response
from sqlalchemy import case, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.database.models.booking_integrations import (
    BookingEmailEvent,
    BookingNotification,
)
from insurance_operations.errors import ApiError
from insurance_operations.settings import ApiSettings

DELIVERY_STATES = {
    "email.sent": "ACCEPTED",
    "email.delivered": "DELIVERED",
    "email.delivery_delayed": "DELAYED",
    "email.bounced": "BOUNCED",
    "email.complained": "COMPLAINED",
    "email.failed": "FAILED",
    "email.suppressed": "SUPPRESSED",
}


@dataclass(frozen=True)
class EmailEvent:
    id: str
    provider_reference: str
    status: str
    occurred_at: datetime


def verify_email_event(
    body: bytes, headers: Mapping[str, str], secret: str, now: datetime
) -> EmailEvent | None:
    try:
        event_id = headers["svix-id"]
        timestamp = headers["svix-timestamp"]
        if (
            not event_id
            or len(event_id) > 256
            or abs(now.timestamp() - int(timestamp)) > 300
        ):
            raise ValueError("invalid webhook metadata")
        if not secret.startswith("whsec_"):
            raise ValueError("invalid signing secret")
        key = base64.b64decode(secret[6:], validate=True)
        if len(key) < 16:
            raise ValueError("invalid signing secret")
        signed = event_id.encode() + b"." + timestamp.encode() + b"." + body
        expected = base64.b64encode(
            hmac.new(key, signed, hashlib.sha256).digest()
        ).decode()
        if not any(
            hmac.compare_digest(value[3:], expected)
            for value in headers["svix-signature"].split()
            if value.startswith("v1,")
        ):
            raise ValueError("invalid signature")
        payload = json.loads(body)
        status = DELIVERY_STATES.get(payload["type"])
        if status is None:
            return None
        email_id = payload["data"]["email_id"]
        occurred_at = datetime.fromisoformat(
            payload["created_at"].replace("Z", "+00:00")
        )
        if (
            not isinstance(email_id, str)
            or not email_id
            or len(email_id) > 256
            or occurred_at.utcoffset() is None
            or occurred_at.timestamp() > now.timestamp() + 300
        ):
            raise ValueError("invalid email event")
        return EmailEvent(event_id, email_id, status, occurred_at)
    except (KeyError, ValueError, TypeError, AttributeError, binascii.Error) as error:
        raise ApiError(
            status_code=400,
            code="EMAIL_WEBHOOK_REJECTED",
            message="Email webhook could not be verified",
        ) from error


def apply_delivery_events(session: Session) -> None:
    ranks = {
        "ACCEPTED": 1,
        "DELAYED": 2,
        "DELIVERED": 3,
        "FAILED": 4,
        "SUPPRESSED": 5,
        "BOUNCED": 6,
        "COMPLAINED": 7,
    }
    states = (
        select(
            BookingEmailEvent.provider_reference,
            func.max(case(ranks, value=BookingEmailEvent.status, else_=0)).label(
                "rank"
            ),
        )
        .group_by(BookingEmailEvent.provider_reference)
        .subquery()
    )
    rows = session.execute(
        select(BookingNotification, states.c.rank)
        .join(
            states,
            states.c.provider_reference == BookingNotification.provider_reference,
        )
        .where(
            states.c.rank
            > case(ranks, value=BookingNotification.delivery_status, else_=0)
        )
        .limit(100)
        .with_for_update(of=BookingNotification, skip_locked=True)
    )
    by_rank = {value: key for key, value in ranks.items()}
    for row, rank in rows:
        row.delivery_status = by_rank[rank]


def create_email_event_router(
    settings: ApiSettings, sessions: sessionmaker[Session]
) -> APIRouter:
    router = APIRouter()

    @router.post("/api/v1/providers/resend/booking-events", include_in_schema=False)
    async def receive(request: Request) -> Response:
        secret = settings.resend_webhook_secret
        if not settings.booking_email_enabled or secret is None:
            raise ApiError(
                status_code=404,
                code="NOT_FOUND",
                message="The requested resource was not found",
            )
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > 262144:
                raise ApiError(
                    status_code=413,
                    code="EMAIL_WEBHOOK_TOO_LARGE",
                    message="Email webhook is too large",
                )
        event = verify_email_event(
            bytes(body), request.headers, secret.get_secret_value(), datetime.now(UTC)
        )
        if event:
            with sessions() as session, session.begin():
                session.execute(
                    insert(BookingEmailEvent)
                    .values(
                        id=event.id,
                        provider_reference=event.provider_reference,
                        status=event.status,
                        occurred_at=event.occurred_at,
                    )
                    .on_conflict_do_nothing(index_elements=["id"])
                )
        return Response(status_code=204)

    return router
