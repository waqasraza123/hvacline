from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from insurance_operations.database.connection import create_database_engine
from insurance_operations.settings import DatabaseSettings, RuntimeEnvironment

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def clear_disposable_conversations(database_engine: Engine) -> None:
    with database_engine.begin() as connection:
        if inspect(connection).has_table("conversation_sessions"):
            connection.execute(text("TRUNCATE TABLE conversation_sessions CASCADE"))


@pytest.fixture(scope="session")
def database_settings() -> DatabaseSettings:
    settings = DatabaseSettings()
    if settings.app_environment is not RuntimeEnvironment.TEST:
        pytest.fail("database tests require APP_ENVIRONMENT=test")
    return settings


@pytest.fixture(scope="session")
def migrated_database(database_settings: DatabaseSettings) -> Iterator[Engine]:
    alembic_config = Config(str(REPOSITORY_ROOT / "alembic.ini"))
    database_engine = create_database_engine(
        database_settings,
        service_name="migration-tests",
    )
    try:
        clear_disposable_conversations(database_engine)
        command.downgrade(alembic_config, "base")
        command.upgrade(alembic_config, "head")
        yield database_engine
    finally:
        try:
            clear_disposable_conversations(database_engine)
            command.downgrade(alembic_config, "base")
        finally:
            database_engine.dispose()
