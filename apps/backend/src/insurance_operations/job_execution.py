from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from time import monotonic
from typing import Any

import httpx
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Connection, Engine, ExecutionContext

from insurance_operations.database.connection import (
    database_engine_options,
    psycopg_url,
)
from insurance_operations.settings import DatabaseConnectionSettings


class JobDeadlineExceeded(Exception):
    pass


@dataclass(frozen=True)
class JobBudget:
    deadline: float

    def remaining(self) -> float:
        remaining = self.deadline - monotonic()
        if remaining <= 0:
            raise JobDeadlineExceeded
        return remaining


current_job_budget: ContextVar[JobBudget | None] = ContextVar(
    "current_job_budget", default=None
)


@contextmanager
def job_budget(seconds: float) -> Iterator[JobBudget]:
    budget = JobBudget(monotonic() + seconds)
    token = current_job_budget.set(budget)
    try:
        yield budget
    finally:
        current_job_budget.reset(token)


def check_job_deadline() -> None:
    budget = current_job_budget.get()
    if budget is not None:
        budget.remaining()


class DeadlineStream(httpx.SyncByteStream):
    def __init__(self, stream: httpx.SyncByteStream, budget: JobBudget) -> None:
        self.stream = stream
        self.budget = budget

    def __iter__(self) -> Iterator[bytes]:
        iterator = iter(self.stream)
        while True:
            self.budget.remaining()
            try:
                chunk = next(iterator)
            except StopIteration:
                return
            self.budget.remaining()
            yield chunk

    def close(self) -> None:
        self.stream.close()


class DeadlineTransport(httpx.HTTPTransport):
    def __init__(self, budget: JobBudget) -> None:
        super().__init__(retries=0)
        self.budget = budget

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        timeout = min(2.0, self.budget.remaining() / 4)
        request.extensions["timeout"] = dict.fromkeys(
            ("connect", "read", "write", "pool"), timeout
        )
        response = super().handle_request(request)
        try:
            self.budget.remaining()
        except JobDeadlineExceeded:
            response.close()
            raise
        assert isinstance(response.stream, httpx.SyncByteStream)
        response.stream = DeadlineStream(response.stream, self.budget)
        return response


def provider_client() -> httpx.Client:
    budget = current_job_budget.get()
    if budget is None:
        return httpx.Client()
    budget.remaining()
    return httpx.Client(transport=DeadlineTransport(budget))


def limit_job_statement(
    connection: Connection,
    cursor: Any,
    statement: str,
    parameters: Any,
    context: ExecutionContext,
    executemany: bool,
) -> None:
    del connection, statement, parameters, context, executemany
    budget = current_job_budget.get()
    milliseconds = 2000 if budget is None else min(2000, int(budget.remaining() * 1000))
    if milliseconds < 1:
        raise JobDeadlineExceeded
    cursor.execute(f"SET LOCAL statement_timeout = '{milliseconds}ms'")
    cursor.execute("SET LOCAL lock_timeout = '250ms'")


def create_job_engine(settings: DatabaseConnectionSettings) -> Engine:
    options = database_engine_options(settings, service_name="booking-jobs")
    options.update(pool_size=2, max_overflow=0, pool_timeout=1)
    options["connect_args"].update(connect_timeout=3)
    engine = create_engine(psycopg_url(settings.runtime_database_url), **options)
    event.listen(engine, "before_cursor_execute", limit_job_statement)
    return engine
