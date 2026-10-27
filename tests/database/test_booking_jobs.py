from unittest.mock import patch
from uuid import UUID, uuid4

from sqlalchemy import select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.booking_jobs import (
    JOB_LOCK_NAME,
    JobBatchResult,
    process_booking_jobs,
)
from insurance_operations.database.models.identity import Agency
from insurance_operations.job_execution import JobDeadlineExceeded, create_job_engine
from insurance_operations.settings import DatabaseSettings


def test_job_lock_excludes_other_connections_and_releases_after_transaction(
    database_settings: DatabaseSettings,
) -> None:
    engine = create_job_engine(database_settings)
    sessions = sessionmaker(bind=engine)
    try:
        with Session(engine) as guard, guard.begin():
            assert guard.scalar(
                text("SELECT pg_try_advisory_xact_lock(hashtextextended(:name, 0))"),
                {"name": JOB_LOCK_NAME},
            )
            with patch(
                "insurance_operations.booking_jobs.collect_booking_jobs"
            ) as jobs:
                assert process_booking_jobs(sessions) == JobBatchResult(status="busy")
                jobs.assert_not_called()
        with patch(
            "insurance_operations.booking_jobs.collect_booking_jobs", return_value=[]
        ):
            assert process_booking_jobs(sessions) == JobBatchResult()
    finally:
        engine.dispose()


def test_deadline_rolls_back_current_job_and_retry_keeps_completed_work(
    migrated_database: Engine,
) -> None:
    sessions = sessionmaker(bind=migrated_database, expire_on_commit=False)
    completed_id, pending_id = uuid4(), uuid4()

    def insert_agency(agency_id: UUID, *, expire: bool = False) -> None:
        with sessions() as session, session.begin():
            session.add(
                Agency(
                    id=agency_id,
                    name="Synthetic job fixture",
                    slug=str(agency_id),
                    environment_kind="DEVELOPMENT",
                )
            )
            session.flush()
            if expire:
                raise JobDeadlineExceeded

    def first_job() -> None:
        insert_agency(completed_id)

    def interrupted_job() -> None:
        insert_agency(pending_id, expire=True)

    def retry_job() -> None:
        insert_agency(pending_id)

    with patch(
        "insurance_operations.booking_jobs.collect_booking_jobs",
        return_value=[first_job, interrupted_job],
    ):
        assert process_booking_jobs(sessions) == JobBatchResult(
            status="deferred", processed=1
        )
    with sessions() as session:
        assert session.get(Agency, completed_id) is not None
        assert session.get(Agency, pending_id) is None
    with patch(
        "insurance_operations.booking_jobs.collect_booking_jobs", return_value=[retry_job]
    ):
        assert process_booking_jobs(sessions) == JobBatchResult(processed=1)
    with sessions() as session:
        assert set(
            session.scalars(
                select(Agency.id).where(Agency.id.in_([completed_id, pending_id]))
            )
        ) == {completed_id, pending_id}
