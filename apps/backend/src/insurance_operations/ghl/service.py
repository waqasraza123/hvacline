import json
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from datetime import UTC, datetime
from uuid import UUID, uuid4

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.actors import ActorContext
from insurance_operations.database.models.ghl import GhlConnection, GhlDelivery
from insurance_operations.database.models.operations import AuditActorType, AuditEvent
from insurance_operations.errors import ApiError
from insurance_operations.ghl.projection import project_lead
from insurance_operations.ghl.provider import Discovery, GhlClient, GhlError
from insurance_operations.ghl.schemas import (
    ConnectionInput,
    CredentialInput,
    RetryInput,
)
from insurance_operations.job_execution import (
    current_job_budget,
    job_budget,
    provider_client,
)
from insurance_operations.settings import DatabaseSettings, RuntimeEnvironment

ProviderFactory = Callable[[str, str], AbstractContextManager[GhlClient]]


@contextmanager
def open_provider(token: str, location_id: str) -> Iterator[GhlClient]:
    active_budget = current_job_budget.get()
    seconds = min(12.0, active_budget.remaining()) if active_budget else 12.0
    with job_budget(seconds), provider_client() as client:
        yield GhlClient(client, token, location_id)


class GhlBusy(RuntimeError):
    pass


@contextmanager
def agency_lock(sessions: sessionmaker[Session], agency_id: UUID) -> Iterator[None]:
    with sessions() as guard, guard.begin():
        if not guard.scalar(
            text("SELECT pg_try_advisory_xact_lock(hashtextextended(:key, 0))"),
            {"key": f"hvacline.ghl:{agency_id}"},
        ):
            raise GhlBusy
        yield


def unavailable(code: str, message: str, status: int = 409) -> ApiError:
    return ApiError(
        status_code=status,
        code=code,
        message=message,
        headers={"Cache-Control": "no-store"},
    )


class GhlVault:
    def __init__(self, settings: DatabaseSettings) -> None:
        key = settings.ghl_token_encryption_key
        if not settings.ghl_enabled or key is None:
            raise GhlError("GHL_NOT_CONFIGURED", connection_error=True)
        self.cipher = Fernet(key.get_secret_value().encode())

    def encrypt(self, token: str, agency_id: UUID, connection_id: UUID) -> str:
        return self.cipher.encrypt(
            json.dumps(
                {
                    "agency": str(agency_id),
                    "connection": str(connection_id),
                    "token": token,
                }
            ).encode()
        ).decode()

    def decrypt(self, row: GhlConnection) -> str:
        try:
            values = json.loads(
                self.cipher.decrypt((row.token_ciphertext or "").encode())
            )
            if values["agency"] != str(row.agency_id) or values["connection"] != str(
                row.id
            ):
                raise ValueError
            if not isinstance(values["token"], str):
                raise ValueError
            return str(values["token"])
        except (InvalidToken, ValueError, KeyError, TypeError):
            raise GhlError(
                "GHL_CREDENTIALS_UNAVAILABLE", connection_error=True
            ) from None


def reference_for(lead_id: UUID) -> str:
    return f"hvacline:{lead_id}"


def require_managed_opportunity(
    client: GhlClient, connection: GhlConnection, delivery: GhlDelivery, identifier: str
) -> None:
    opportunity = client.opportunity(identifier)
    if (
        opportunity.pipelineId != connection.pipeline_id
        or opportunity.contactId != delivery.contact_id
        or opportunity.field(connection.fields["reference"])
        != reference_for(delivery.lead_id)
    ):
        raise GhlError("GHL_OPPORTUNITY_OWNERSHIP_INVALID")
    if (
        opportunity.status != "open"
        or opportunity.pipelineStageId not in connection.stages.values()
    ):
        raise GhlError("GHL_OPPORTUNITY_MANAGED_EXTERNALLY")
    expected = {
        stage for stage in (delivery.last_stage_id, delivery.pending_stage_id) if stage
    }
    if expected and opportunity.pipelineStageId not in expected:
        raise GhlError("GHL_OPPORTUNITY_STAGE_CHANGED_EXTERNALLY")


def connection_view(row: GhlConnection) -> dict[str, object]:
    return {
        "id": str(row.id),
        "location_id": row.location_id,
        "pipeline_id": row.pipeline_id,
        "stages": row.stages,
        "fields": row.fields,
        "status": row.status,
        "activated_at": row.activated_at,
        "last_checked_at": row.last_checked_at,
        "last_error": row.last_error,
        "blocked_until": row.blocked_until,
    }


def delivery_view(row: GhlDelivery, connection: GhlConnection) -> dict[str, object]:
    return {
        "id": str(row.id),
        "connection_id": str(row.connection_id),
        "connection_status": connection.status,
        "location_id": connection.location_id,
        "lead_id": str(row.lead_id),
        "reference": reference_for(row.lead_id),
        "status": row.status,
        "attempts": row.attempts,
        "desired_version": row.desired_version,
        "delivered_version": row.delivered_version,
        "contact_id": row.contact_id,
        "opportunity_id": row.opportunity_id,
        "contact_unknown": row.contact_unknown,
        "opportunity_unknown": row.opportunity_unknown,
        "last_stage_id": row.last_stage_id,
        "pending_stage_id": row.pending_stage_id,
        "created_at": row.created_at,
        "next_attempt_at": row.next_attempt_at,
        "last_synced_at": row.last_synced_at,
        "last_error": row.last_error,
    }


def audit(session: Session, actor: ActorContext, event: str, resource_id: UUID) -> None:
    session.add(
        AuditEvent(
            agency_id=actor.agency_id,
            actor_type=AuditActorType.STAFF.value,
            actor_user_id=actor.app_user_id,
            event_type=event,
            occurred_at=datetime.now(UTC),
            summary="GHL integration configuration or recovery changed",
            details={"resource_id": str(resource_id)},
            correlation_id=uuid4(),
            event_version=1,
        )
    )


class GhlService:
    def __init__(
        self,
        sessions: sessionmaker[Session],
        settings: DatabaseSettings,
        factory: ProviderFactory = open_provider,
    ) -> None:
        self.sessions, self.settings, self.factory = sessions, settings, factory

    def enabled(self) -> None:
        if (
            not self.settings.ghl_enabled
            or self.settings.app_environment is RuntimeEnvironment.PRODUCTION
        ):
            raise unavailable(
                "GHL_DISABLED", "GoHighLevel is not enabled for this workspace.", 404
            )

    def latest(self, session: Session, agency_id: UUID) -> GhlConnection | None:
        return session.scalar(
            select(GhlConnection)
            .where(
                GhlConnection.agency_id == agency_id,
            )
            .order_by(GhlConnection.activated_at.desc(), GhlConnection.id.desc())
            .limit(1)
        )

    def current(self, session: Session, agency_id: UUID) -> GhlConnection:
        row = self.latest(session, agency_id)
        if not row or row.status == "DISCONNECTED":
            raise unavailable("GHL_NOT_CONNECTED", "Connect a GHL sub-account first.")
        return row

    def status(self, actor: ActorContext) -> dict[str, object]:
        if not self.settings.ghl_enabled:
            return {"enabled": False, "connection": None}
        with self.sessions() as session:
            row = self.latest(session, actor.agency_id)
            return {
                "enabled": True,
                "connection": connection_view(row) if row else None,
            }

    def discover(self, data: CredentialInput) -> Discovery:
        self.enabled()
        with self.factory(data.token.get_secret_value(), data.location_id) as client:
            return client.discover()

    def connect(self, actor: ActorContext, data: ConnectionInput) -> dict[str, object]:
        self.enabled()
        with agency_lock(self.sessions, actor.agency_id):
            with self.sessions() as session:
                existing = self.latest(session, actor.agency_id)
                if existing and existing.status != "DISCONNECTED":
                    raise unavailable(
                        "GHL_ALREADY_CONNECTED",
                        "Disconnect before changing the destination or mappings.",
                    )
            with self.factory(
                data.token.get_secret_value(), data.location_id
            ) as client:
                client.validate_mapping(data)
            identifier = uuid4()
            ciphertext = GhlVault(self.settings).encrypt(
                data.token.get_secret_value(), actor.agency_id, identifier
            )
            try:
                with self.sessions() as session, session.begin():
                    row = GhlConnection(
                        id=identifier,
                        agency_id=actor.agency_id,
                        location_id=data.location_id,
                        pipeline_id=data.pipeline_id,
                        stages=data.stages.model_dump(),
                        fields=data.fields.model_dump(),
                        token_ciphertext=ciphertext,
                        status="ACTIVE",
                        activated_at=datetime.now(UTC),
                        last_checked_at=datetime.now(UTC),
                    )
                    session.add(row)
                    session.flush()
                    audit(session, actor, "GHL_CONNECTED", row.id)
                    result = connection_view(row)
                return result
            except IntegrityError:
                raise unavailable(
                    "GHL_DESTINATION_IN_USE",
                    "This business or GHL sub-account already has an active connection.",
                ) from None

    def action(self, actor: ActorContext, action: str) -> dict[str, object]:
        self.enabled()
        with agency_lock(self.sessions, actor.agency_id):
            if action == "resume":
                with self.sessions() as session:
                    row = self.current(session, actor.agency_id)
                    configuration = self.configuration(
                        row, GhlVault(self.settings).decrypt(row)
                    )
                with self.factory(
                    configuration.token.get_secret_value(), configuration.location_id
                ) as client:
                    client.validate_mapping(configuration)
            with self.sessions() as session, session.begin():
                row = self.current(session, actor.agency_id)
                row.status = {
                    "pause": "PAUSED",
                    "resume": "ACTIVE",
                    "disconnect": "DISCONNECTED",
                }[action]
                if action == "disconnect":
                    row.token_ciphertext = None
                if action == "resume":
                    row.last_checked_at, row.last_error = datetime.now(UTC), None
                audit(session, actor, f"GHL_{action.upper()}", row.id)
                return connection_view(row)

    def rotate(self, actor: ActorContext, data: CredentialInput) -> dict[str, object]:
        self.enabled()
        with agency_lock(self.sessions, actor.agency_id):
            with self.sessions() as session:
                row = self.current(session, actor.agency_id)
                if row.location_id != data.location_id:
                    raise unavailable(
                        "GHL_LOCATION_IMMUTABLE",
                        "Disconnect before changing the location.",
                    )
                configuration = self.configuration(row, data.token.get_secret_value())
                identifier = row.id
            with self.factory(
                data.token.get_secret_value(), data.location_id
            ) as client:
                client.validate_mapping(configuration)
            with self.sessions() as session, session.begin():
                row = self.current(session, actor.agency_id)
                row.token_ciphertext = GhlVault(self.settings).encrypt(
                    data.token.get_secret_value(), actor.agency_id, identifier
                )
                row.last_checked_at, row.last_error = datetime.now(UTC), None
                row.status = "PAUSED"
                audit(session, actor, "GHL_TOKEN_REPLACED", row.id)
                return connection_view(row)

    @staticmethod
    def configuration(row: GhlConnection, token: str) -> ConnectionInput:
        try:
            return ConnectionInput.model_validate(
                {
                    "location_id": row.location_id,
                    "token": token,
                    "pipeline_id": row.pipeline_id,
                    "stages": row.stages,
                    "fields": row.fields,
                    "multiple_opportunities_confirmed": True,
                }
            )
        except ValueError:
            raise GhlError("GHL_CONNECTION_INVALID", connection_error=True) from None

    def deliveries(
        self, actor: ActorContext, offset: int, limit: int
    ) -> dict[str, object]:
        self.enabled()
        with self.sessions() as session:
            items = session.execute(
                select(GhlDelivery, GhlConnection)
                .join(
                    GhlConnection,
                    (GhlConnection.id == GhlDelivery.connection_id)
                    & (GhlConnection.agency_id == GhlDelivery.agency_id),
                )
                .where(GhlDelivery.agency_id == actor.agency_id)
                .order_by(
                    GhlDelivery.created_at.desc(),
                    GhlDelivery.id.desc(),
                )
                .offset(offset)
                .limit(limit)
            ).all()
            total = (
                session.scalar(
                    select(func.count())
                    .select_from(GhlDelivery)
                    .where(
                        GhlDelivery.agency_id == actor.agency_id,
                    )
                )
                or 0
            )
            return {
                "items": [delivery_view(d, c) for d, c in items],
                "total": total,
                "offset": offset,
                "limit": limit,
            }

    def retry(self, actor: ActorContext, identifier: UUID, data: RetryInput) -> None:
        self.enabled()
        with agency_lock(self.sessions, actor.agency_id):
            with self.sessions() as session:
                delivery = session.scalar(
                    select(GhlDelivery).where(
                        GhlDelivery.id == identifier,
                        GhlDelivery.agency_id == actor.agency_id,
                    )
                )
                if not delivery:
                    raise unavailable(
                        "GHL_DELIVERY_NOT_FOUND", "Delivery was not found.", 404
                    )
                connection = self.current(session, actor.agency_id)
                if (
                    delivery.connection_id != connection.id
                    or connection.status != "ACTIVE"
                ):
                    raise unavailable(
                        "GHL_CONNECTION_PAUSED",
                        "Resume the delivery's original connection first.",
                    )
                if delivery.status == "SYNCED":
                    raise unavailable(
                        "GHL_ALREADY_SYNCED", "This delivery is already synchronized."
                    )
                token = GhlVault(self.settings).decrypt(connection)
                self.configuration(connection, token)
            recovered_id = delivery.opportunity_id
            recovered_contact = delivery.contact_id
            with self.factory(token, connection.location_id) as client:
                if data.remote_opportunity_id:
                    if recovered_id and recovered_id != data.remote_opportunity_id:
                        raise unavailable(
                            "GHL_MAPPING_IMMUTABLE",
                            "A mapped opportunity cannot be replaced.",
                        )
                    require_managed_opportunity(
                        client, connection, delivery, data.remote_opportunity_id
                    )
                    recovered_id = data.remote_opportunity_id
                elif data.confirm_remote_absent:
                    if recovered_id or not (
                        delivery.contact_unknown or delivery.opportunity_unknown
                    ):
                        raise unavailable(
                            "GHL_RECOVERY_INVALID",
                            "Only unresolved creation can be cleared after absence review.",
                        )
                    if delivery.contact_unknown:
                        with self.sessions() as session:
                            projection = project_lead(
                                session, actor.agency_id, delivery.lead_id
                            )
                        recovered_contact = client.match_contact(
                            projection.email, projection.phone
                        )
                    if delivery.opportunity_unknown:
                        found = client.find_opportunity(
                            reference_for(delivery.lead_id),
                            connection.pipeline_id,
                            connection.fields["reference"],
                        )
                        if found:
                            require_managed_opportunity(
                                client, connection, delivery, found.id
                            )
                            recovered_id = found.id
                elif recovered_id:
                    require_managed_opportunity(
                        client, connection, delivery, recovered_id
                    )
            with self.sessions() as session, session.begin():
                row = session.get(GhlDelivery, identifier)
                assert row is not None
                if recovered_id:
                    row.opportunity_id, row.opportunity_unknown = recovered_id, False
                elif data.confirm_remote_absent:
                    row.opportunity_unknown = False
                if data.confirm_remote_absent and delivery.contact_unknown:
                    row.contact_id, row.contact_unknown = recovered_contact, False
                row.status, row.attempts, row.last_error = "PENDING", 0, None
                row.next_attempt_at = datetime.now(UTC)
                audit(session, actor, "GHL_DELIVERY_RETRIED", identifier)
