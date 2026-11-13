from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from functools import partial
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.database.models.ghl import GhlConnection, GhlDelivery
from insurance_operations.ghl.projection import project_lead
from insurance_operations.ghl.provider import GhlError
from insurance_operations.ghl.service import (
    GhlBusy,
    GhlService,
    GhlVault,
    ProviderFactory,
    agency_lock,
    open_provider,
    reference_for,
    require_managed_opportunity,
)
from insurance_operations.job_execution import check_job_deadline
from insurance_operations.settings import DatabaseSettings

MAX_ATTEMPTS = 8


def retry_seconds(attempt: int, retry_after: int = 0) -> int:
    return max(min(3600, 30 * 2 ** min(max(0, attempt - 1), 7)), retry_after)


def set_delivery(
    sessions: sessionmaker[Session], identifier: UUID, **values: object
) -> None:
    with sessions() as session, session.begin():
        row = session.get(GhlDelivery, identifier)
        if row is None:
            raise GhlError("GHL_DELIVERY_UNAVAILABLE")
        for key, value in values.items():
            setattr(row, key, value)


def record_failure(
    sessions: sessionmaker[Session], identifier: UUID, error: GhlError
) -> None:
    with sessions() as session, session.begin():
        row = session.get(GhlDelivery, identifier)
        if row is None:
            return
        connection = session.get(GhlConnection, row.connection_id)
        row.last_error = error.code
        row.status = (
            "RETRYING"
            if error.retryable and row.attempts < MAX_ATTEMPTS
            else "NEEDS_REVIEW"
        )
        row.next_attempt_at = datetime.now(UTC) + timedelta(
            seconds=retry_seconds(row.attempts, error.retry_after)
        )
        if connection:
            connection.last_error, connection.last_checked_at = (
                error.code,
                datetime.now(UTC),
            )
            if error.connection_error:
                connection.status = "ERROR"
            if error.code == "GHL_RATE_LIMITED":
                connection.blocked_until = row.next_attempt_at


def collect_ghl_jobs(
    sessions: sessionmaker[Session], limit: int
) -> list[Callable[[], None]]:
    with sessions() as session:
        settings = session.info.get("integration_settings")
        if not isinstance(settings, DatabaseSettings) or not settings.ghl_enabled:
            return []
        now = datetime.now(UTC)
        identifiers = session.scalars(
            select(GhlDelivery.id)
            .join(
                GhlConnection,
                (GhlConnection.id == GhlDelivery.connection_id)
                & (GhlConnection.agency_id == GhlDelivery.agency_id),
            )
            .where(
                GhlConnection.status == "ACTIVE",
                GhlConnection.blocked_until.is_(None)
                | (GhlConnection.blocked_until <= now),
                GhlDelivery.status.in_(["PENDING", "PROCESSING", "RETRYING"]),
                GhlDelivery.next_attempt_at <= now,
            )
            .order_by(GhlDelivery.next_attempt_at, GhlDelivery.id)
            .limit(limit)
        ).all()
    return [partial(deliver_ghl, sessions, identifier) for identifier in identifiers]


def deliver_ghl(
    sessions: sessionmaker[Session],
    identifier: UUID,
    factory: ProviderFactory = open_provider,
) -> None:
    with sessions() as session:
        settings = session.info.get("integration_settings")
        row = session.get(GhlDelivery, identifier)
        if (
            not isinstance(settings, DatabaseSettings)
            or not settings.ghl_enabled
            or not row
        ):
            return
        agency_id = row.agency_id
    try:
        with agency_lock(sessions, agency_id):
            try:
                deliver_locked(sessions, settings, identifier, factory)
            except GhlError as error:
                record_failure(sessions, identifier, error)
    except GhlBusy:
        return


def deliver_locked(
    sessions: sessionmaker[Session],
    settings: DatabaseSettings,
    identifier: UUID,
    factory: ProviderFactory,
) -> None:
    with sessions() as session, session.begin():
        row = session.get(GhlDelivery, identifier)
        if row is None or row.status not in {"PENDING", "PROCESSING", "RETRYING"}:
            return
        connection = session.get(GhlConnection, row.connection_id)
        now = datetime.now(UTC)
        if not connection or connection.status != "ACTIVE" or row.next_attempt_at > now:
            return
        if connection.blocked_until and connection.blocked_until > now:
            return
        if row.attempts >= MAX_ATTEMPTS:
            row.status, row.last_error = "NEEDS_REVIEW", "GHL_RETRY_LIMIT"
            return
        row.status, row.attempts = "PROCESSING", row.attempts + 1
    with sessions() as session:
        row = session.get(GhlDelivery, identifier)
        assert row is not None
        connection = session.get(GhlConnection, row.connection_id)
        assert connection is not None
        projection = project_lead(session, row.agency_id, row.lead_id)
        version = row.desired_version
        token = GhlVault(settings).decrypt(connection)
        configuration = GhlService.configuration(connection, token)
        target_stage = connection.stages[projection.outcome]
        reference = reference_for(row.lead_id)
    with factory(token, connection.location_id) as client:
        client.validate_mapping(configuration)
        check_job_deadline()
        contact_id = client.match_contact(projection.email, projection.phone)
        if row.contact_id:
            if contact_id != row.contact_id:
                raise GhlError("GHL_CONTACT_MAPPING_CHANGED")
            contact_id = row.contact_id
        elif contact_id:
            set_delivery(
                sessions, identifier, contact_id=contact_id, contact_unknown=False
            )
        else:
            if row.contact_unknown:
                raise GhlError("GHL_CONTACT_CREATION_UNKNOWN")
            set_delivery(sessions, identifier, contact_unknown=True)
            try:
                contact_id = client.create_contact(projection.contact_values())
            except GhlError as error:
                if not error.ambiguous:
                    set_delivery(sessions, identifier, contact_unknown=False)
                raise
            set_delivery(
                sessions, identifier, contact_id=contact_id, contact_unknown=False
            )
        row.contact_id = contact_id
        opportunity_id = row.opportunity_id
        if not opportunity_id and row.opportunity_unknown:
            found = client.find_opportunity(
                reference, connection.pipeline_id, connection.fields["reference"]
            )
            if found is None:
                raise GhlError("GHL_OPPORTUNITY_CREATION_UNKNOWN")
            opportunity_id = found.id
            require_managed_opportunity(client, connection, row, opportunity_id)
            set_delivery(
                sessions,
                identifier,
                opportunity_id=opportunity_id,
                opportunity_unknown=False,
            )
        fields: list[dict[str, object]] = [
            {"id": connection.fields["reference"], "fieldValue": reference},
            {"id": connection.fields["summary"], "fieldValue": projection.summary},
            {"id": connection.fields["booking"], "fieldValue": projection.booking},
        ]
        if opportunity_id:
            require_managed_opportunity(client, connection, row, opportunity_id)
            set_delivery(sessions, identifier, pending_stage_id=target_stage)
            client.update_opportunity(
                opportunity_id,
                {"pipelineStageId": target_stage, "customFields": fields},
            )
        else:
            set_delivery(
                sessions,
                identifier,
                opportunity_unknown=True,
                pending_stage_id=target_stage,
            )
            try:
                opportunity_id = client.create_opportunity(
                    {
                        "pipelineId": connection.pipeline_id,
                        "pipelineStageId": target_stage,
                        "contactId": contact_id,
                        "name": reference,
                        "status": "open",
                        "customFields": fields,
                    }
                )
            except GhlError as error:
                if not error.ambiguous:
                    set_delivery(sessions, identifier, opportunity_unknown=False)
                raise
            set_delivery(
                sessions,
                identifier,
                opportunity_id=opportunity_id,
                opportunity_unknown=False,
            )
        check_job_deadline()
        saved = client.opportunity(opportunity_id)
        if saved.pipelineId != connection.pipeline_id or saved.contactId != contact_id:
            raise GhlError("GHL_OPPORTUNITY_OWNERSHIP_INVALID")
        if saved.status != "open" or saved.pipelineStageId != target_stage:
            raise GhlError("GHL_OPPORTUNITY_MANAGED_EXTERNALLY")
        if any(
            saved.field(str(field["id"])) != field["fieldValue"] for field in fields
        ):
            raise GhlError("GHL_FIELD_WRITE_UNCONFIRMED", connection_error=True)
    with sessions() as session, session.begin():
        current = session.get(GhlDelivery, identifier)
        assert current is not None
        current.delivered_version = version
        current.status = "SYNCED" if current.desired_version == version else "PENDING"
        current.last_stage_id, current.pending_stage_id = target_stage, None
        current.last_synced_at, current.last_error = datetime.now(UTC), None
        current.attempts, current.next_attempt_at = 0, datetime.now(UTC)
        connected = session.get(GhlConnection, current.connection_id)
        assert connected is not None
        connected.last_checked_at, connected.last_error = datetime.now(UTC), None
