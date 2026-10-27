import hmac
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from threading import Lock
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Response
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.booking_jobs import JobBatchResult, process_booking_jobs
from insurance_operations.job_execution import create_job_engine
from insurance_operations.settings import JobRunnerSettings


def create_job_app(settings: JobRunnerSettings, engine: Engine | None = None) -> FastAPI:
    database_engine = engine if engine is not None else create_job_engine(settings)
    sessions = sessionmaker(
        bind=database_engine,
        expire_on_commit=False,
        info={"integration_settings": settings},
    )
    active = Lock()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        del application
        try:
            yield
        finally:
            database_engine.dispose()

    application = FastAPI(
        title="HVACLine booking jobs",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )

    def authorize(
        authorization: Annotated[str | None, Header()] = None,
    ) -> None:
        expected = b"Bearer " + settings.booking_jobs_secret.get_secret_value().encode()
        if not hmac.compare_digest((authorization or "").encode(), expected):
            raise HTTPException(
                status_code=401,
                detail="Job authorization required",
                headers={"WWW-Authenticate": "Bearer", "Cache-Control": "no-store"},
            )

    @application.post(
        "/api/v1/internal/booking-jobs/run",
        dependencies=[Depends(authorize)],
    )
    def run_jobs(response: Response) -> JobBatchResult:
        response.headers["Cache-Control"] = "no-store"
        if not active.acquire(blocking=False):
            return JobBatchResult(status="busy")
        try:
            return process_booking_jobs(sessions)
        except SQLAlchemyError:
            logging.getLogger(__name__).error("Booking job database unavailable")
            raise HTTPException(
                status_code=503,
                detail="Job database unavailable; retry later",
                headers={"Retry-After": "60"},
            ) from None
        finally:
            active.release()

    return application
