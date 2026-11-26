from datetime import UTC, datetime
from unittest.mock import patch
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.database.models.hvac import HvacServiceRequest
from insurance_operations.database.models.identity import Agency
from insurance_operations.database.models.staff_alert import StaffAlert, StaffAlertPolicy
from insurance_operations.notifications.staff_alerts import deliver_staff_alert
from insurance_operations.settings import DatabaseSettings


def request(agency: Agency, hazardous: bool = True) -> HvacServiceRequest:
    return HvacServiceRequest(
        agency_id=agency.id,
        customer_details={"full_name": "Fictional private caller"},
        service_details={"hazardous_condition": hazardous},
        status="HANDOFF_REQUESTED" if hazardous else "OPEN",
        fingerprint=str(uuid4()), confirmed_at=datetime.now(UTC),
    )


def setup_alert(engine: Engine) -> tuple[UUID, UUID]:
    with Session(engine) as session, session.begin():
        agency = Agency(name="Fictional alert business", slug=str(uuid4()), environment_kind="DEVELOPMENT")
        session.add(agency)
        session.flush()
        policy = StaffAlertPolicy(agency_id=agency.id, enabled=True, recipients=["staff@example.com"], sender="alerts@example.com")
        session.add(policy)
        session.flush()
        source = request(agency)
        session.add(source)
        session.flush()
        row = session.scalar(select(StaffAlert).where(StaffAlert.agency_id == agency.id))
        assert row is not None
        return row.id, agency.id


def test_staff_capture_is_prospective_deduplicated_and_payload_is_immutable(migrated_database: Engine) -> None:
    with Session(migrated_database) as session, session.begin():
        agency = Agency(name="Fictional policy business", slug=str(uuid4()), environment_kind="DEVELOPMENT")
        session.add(agency)
        session.flush()
        policy = StaffAlertPolicy(agency_id=agency.id, enabled=False, recipients=["staff@example.com"], sender="alerts@example.com")
        session.add(policy)
        session.flush()
        previous = request(agency)
        session.add(previous)
        session.flush()
        policy.enabled = True
        session.flush()
        session.refresh(policy)
        assert session.scalar(select(func.count()).select_from(StaffAlert).where(StaffAlert.agency_id == agency.id)) == 0
        source = request(agency)
        routine = request(agency, False)
        session.add_all([source, routine])
        session.flush()
        alerts = session.scalars(select(StaffAlert).where(StaffAlert.agency_id == agency.id)).all()
        assert len(alerts) == 1
        row = alerts[0]
        assert row.source_id == source.id
        assert row.policy_version == policy.row_version
        assert "Fictional private caller" not in str(row.payload)
        source.status = "CLOSED"
        session.flush()
        source.status = "HANDOFF_REQUESTED"
        session.flush()
        assert session.scalar(select(func.count()).select_from(StaffAlert).where(StaffAlert.agency_id == agency.id)) == 1
        with pytest.raises(DBAPIError), session.begin_nested():
            row.payload = {"text": "Changed payload"}
            session.flush()


def test_hazard_updates_capture_once_and_rollback_with_the_request(migrated_database: Engine) -> None:
    with Session(migrated_database) as session, session.begin():
        agency = Agency(name="Fictional rollback business", slug=str(uuid4()), environment_kind="DEVELOPMENT")
        session.add(agency)
        session.flush()
        session.add(StaffAlertPolicy(agency_id=agency.id, enabled=True, recipients=["staff@example.com"], sender="alerts@example.com"))
        session.flush()
        source = request(agency, False)
        session.add(source)
        session.flush()
        source_id = source.id
        with session.begin_nested() as transaction:
            source.status = "HANDOFF_REQUESTED"
            source.service_details = {"hazardous_condition": True}
            session.flush()
            assert session.scalar(select(func.count()).select_from(StaffAlert).where(StaffAlert.source_id == source_id)) == 1
            transaction.rollback()
        assert session.scalar(select(func.count()).select_from(StaffAlert).where(StaffAlert.source_id == source_id)) == 0


def test_worker_commits_retry_horizon_and_reuses_the_original_email_request(migrated_database: Engine) -> None:
    identifier, _ = setup_alert(migrated_database)
    settings = DatabaseSettings(
        _env_file=None, app_environment="development", database_url="postgresql://synthetic:synthetic@localhost/dev",
        staff_alert_email_enabled=True, resend_api_key="synthetic-key",
        resend_webhook_secret="whsec_c3ludGhldGljLXNpZ25pbmcta2V5LWF0LWxlYXN0LTMy",
        booking_email_from="alerts@example.com",
    )
    sessions = sessionmaker(migrated_database, info={"integration_settings": settings})
    keys: list[str] = []
    bodies: list[bytes] = []

    def send(request: httpx.Request) -> httpx.Response:
        keys.append(request.headers["Idempotency-Key"])
        bodies.append(request.content)
        if len(keys) == 1:
            raise httpx.ReadTimeout("fictional lost response", request=request)
        return httpx.Response(200, json={"id": "fictional-staff-email"})

    with patch("insurance_operations.notifications.staff_alerts.provider_client", side_effect=lambda: httpx.Client(transport=httpx.MockTransport(send))):
        deliver_staff_alert(sessions, identifier)
        with Session(migrated_database) as session, session.begin():
            row = session.get(StaffAlert, identifier)
            assert row is not None and row.first_attempt_at is not None
            first = row.first_attempt_at
            assert row.status == "PENDING"
            row.due_at = datetime.now(UTC)
        deliver_staff_alert(sessions, identifier)
    assert keys[0] == keys[1]
    assert bodies[0] == bodies[1]
    with Session(migrated_database) as session:
        row = session.get(StaffAlert, identifier)
        assert row is not None and row.status == "ACCEPTED"
        assert row.delivery_status is None
        assert row.first_attempt_at == first


def test_disabled_runtime_never_contacts_resend(migrated_database: Engine) -> None:
    identifier, _ = setup_alert(migrated_database)
    settings = DatabaseSettings(_env_file=None, app_environment="development", database_url="postgresql://synthetic:synthetic@localhost/dev")
    sessions = sessionmaker(migrated_database, info={"integration_settings": settings})
    with patch("insurance_operations.notifications.staff_alerts.provider_client") as provider:
        deliver_staff_alert(sessions, identifier)
    provider.assert_not_called()
    with Session(migrated_database) as session:
        row = session.get(StaffAlert, identifier)
        assert row is not None and row.status == "PENDING"
        assert row.first_attempt_at is None
