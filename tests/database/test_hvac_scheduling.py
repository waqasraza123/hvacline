from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.database.models.hvac import Appointment
from insurance_operations.database.models.identity import Agency
from insurance_operations.errors import ApiError
from insurance_operations.hvac.schemas import (
    AvailabilityInput,
    ReservationInput,
    ScheduleInput,
    ServiceRequestInput,
)
from insurance_operations.hvac.service import SchedulingService


def configure(engine: Engine) -> tuple[SchedulingService, UUID, ReservationInput]:
    with Session(engine) as session, session.begin():
        agency = Agency(
            name="Synthetic HVAC company",
            slug=str(uuid4()),
            environment_kind="DEVELOPMENT",
        )
        session.add(agency)
        session.flush()
        agency_id = agency.id
    service = SchedulingService(sessionmaker(bind=engine, expire_on_commit=False))
    day = (datetime.now(UTC) + timedelta(days=2)).date()
    windows = [{"weekday": day.weekday(), "start": "08:00", "end": "17:00"}]
    service.configure(
        agency_id,
        ScheduleInput(
            expected_version=0,
            enabled=True,
            timezone="America/New_York",
            postal_codes=["10001"],
            windows=windows,
            teams=[{"key": "team-a", "name": "Service team", "windows": windows}],
            notice_minutes=0,
        ),
        uuid4(),
    )
    request_id = service.create_request(agency_id, service_request(), uuid4())
    slot = service.availability(
        agency_id, AvailabilityInput(postal_code="10001", day=day)
    ).slots[0]
    return (
        service,
        agency_id,
        ReservationInput(
            service_request_id=request_id,
            team_key=slot.team_key,
            starts_at=slot.starts_at,
            idempotency_key=str(uuid4()),
        ),
    )


def service_request(hazardous: bool = False) -> ServiceRequestInput:
    return ServiceRequestInput.model_validate(
        {
            "customer": {
                "full_name": "Synthetic Caller",
                "phone": "+15559991002",
                "address": {
                    "line1": "123 Example St",
                    "city": "New York",
                    "state_code": "NY",
                    "postal_code": "10001",
                },
            },
            "service": {
                "kind": "AC_REPAIR",
                "equipment_issue": "AC stopped cooling",
                "preferred_window": "Morning",
                "hazardous_condition": hazardous,
            },
            "explicit_confirmation": True,
        }
    )


def test_booking_is_persistent_idempotent_and_tenant_scoped(
    migrated_database: Engine,
) -> None:
    service, agency_id, request = configure(migrated_database)
    reserved = service.reserve(agency_id, request, uuid4())
    assert reserved.status == "HELD"
    assert service.reserve(agency_id, request, uuid4()).id == reserved.id
    confirmed = service.confirm(agency_id, reserved.id, True, uuid4())
    assert confirmed.status == "CONFIRMED"
    with Session(migrated_database) as session:
        assert (
            session.scalar(
                select(Appointment.status).where(Appointment.id == confirmed.id)
            )
            == "CONFIRMED"
        )
    with pytest.raises(ApiError) as error:
        service.confirm(uuid4(), reserved.id, True, uuid4())
    assert error.value.status_code in {404, 409}
    with pytest.raises(ApiError) as error:
        service.reserve(
            agency_id, request.model_copy(update={"team_key": "other"}), uuid4()
        )
    assert error.value.code == "BOOKING_KEY_CONFLICT"


def test_concurrent_requests_cannot_double_book_one_technician(
    migrated_database: Engine,
) -> None:
    service, agency_id, first = configure(migrated_database)
    second_id = service.create_request(agency_id, service_request(), uuid4())
    second = first.model_copy(
        update={"service_request_id": second_id, "idempotency_key": str(uuid4())}
    )

    def reserve(request: ReservationInput) -> str:
        try:
            return service.reserve(agency_id, request, uuid4()).status
        except ApiError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(reserve, [first, second]))
    assert sorted(results) == ["HELD", "SLOT_CONFLICT"]


def test_expired_hold_and_hazard_cannot_be_confirmed_or_booked(
    migrated_database: Engine,
) -> None:
    service, agency_id, request = configure(migrated_database)
    reserved = service.reserve(agency_id, request, uuid4())
    with Session(migrated_database) as session, session.begin():
        appointment = session.get(Appointment, reserved.id)
        assert appointment is not None
        appointment.hold_expires_at = datetime.now(UTC) - timedelta(seconds=1)
    with pytest.raises(ApiError) as error:
        service.confirm(agency_id, reserved.id, True, uuid4())
    assert error.value.code == "RESERVATION_EXPIRED"
    hazardous = service.create_request(agency_id, service_request(True), uuid4())
    with pytest.raises(ApiError) as error:
        service.reserve(
            agency_id,
            request.model_copy(
                update={
                    "service_request_id": hazardous,
                    "idempotency_key": str(uuid4()),
                }
            ),
            uuid4(),
        )
    assert error.value.code == "HUMAN_ATTENTION_REQUIRED"


def test_reschedule_is_atomic_and_cancellation_releases_capacity(
    migrated_database: Engine,
) -> None:
    service, agency_id, request = configure(migrated_database)
    reserved = service.reserve(agency_id, request, uuid4())
    service.confirm(agency_id, reserved.id, True, uuid4())
    replacement = request.model_copy(
        update={
            "starts_at": request.starts_at + timedelta(hours=2),
            "idempotency_key": str(uuid4()),
        }
    )
    changed = service.reschedule(agency_id, reserved.id, replacement, uuid4())
    assert changed.status == "CONFIRMED"
    assert (
        service.reschedule(agency_id, reserved.id, replacement, uuid4()).id
        == changed.id
    )
    service.cancel(agency_id, changed.id, uuid4())
    assert (
        service.reserve(
            agency_id,
            request.model_copy(update={"idempotency_key": str(uuid4())}),
            uuid4(),
        ).status
        == "HELD"
    )


def test_phone_request_rejects_unresolved_call_context(
    migrated_database: Engine,
) -> None:
    service, agency_id, _ = configure(migrated_database)
    with pytest.raises(ApiError) as error:
        service.create_request(agency_id, service_request(), uuid4(), call_id=uuid4())
    assert error.value.status_code == 404
