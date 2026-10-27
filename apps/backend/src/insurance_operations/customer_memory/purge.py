import json
from datetime import UTC, datetime

from pydantic import Field
from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.orm import Session

from insurance_operations.database.connection import create_database_engine
from insurance_operations.database.models.customer_memory import (
    CustomerMemoryFact, CustomerMemoryPairing, CustomerMemoryPolicy, CustomerMemorySummary,
    CustomerWhatsAppIdentity,
)
from insurance_operations.settings import DatabaseConnectionSettings


class MemoryRetentionSettings(DatabaseConnectionSettings):
    customer_memory_retention_days: int = Field(default=90, ge=1, le=365)


def purge_expired(session: Session, retention_days: int, *, batch_size: int = 500) -> int:
    if not 1 <= retention_days <= 365 or not 1 <= batch_size <= 500:
        raise ValueError("Invalid memory retention batch limits")
    now = datetime.now(UTC)
    session.execute(update(CustomerMemoryPolicy).where(
        CustomerMemoryPolicy.retention_days > retention_days
    ).values(retention_days=retention_days, updated_at=now))
    removed = 0
    for model, primary, created in (
        (CustomerMemoryFact, CustomerMemoryFact.id, CustomerMemoryFact.updated_at),
        (CustomerMemorySummary, CustomerMemorySummary.intake_id,
         CustomerMemorySummary.created_at),
        (CustomerWhatsAppIdentity, CustomerWhatsAppIdentity.id,
         CustomerWhatsAppIdentity.verified_at),
    ):
        policy_days = select(CustomerMemoryPolicy.retention_days).where(
            CustomerMemoryPolicy.account_id == model.account_id,
            CustomerMemoryPolicy.agency_id == model.agency_id,
        ).scalar_subquery()
        policy_expiry = created + func.make_interval(
            0, 0, 0, func.coalesce(policy_days, retention_days)
        )
        expired = or_(model.expires_at <= now, policy_expiry <= now)
        identifiers = select(primary).where(expired).limit(batch_size)
        removed += len(session.scalars(delete(model).where(
            primary.in_(identifiers),
            expired,
        ).returning(primary)).all())
    expired_pairs = select(CustomerMemoryPairing.id).where(
        CustomerMemoryPairing.expires_at <= now
    ).limit(batch_size)
    removed += len(session.scalars(delete(CustomerMemoryPairing).where(
        CustomerMemoryPairing.id.in_(expired_pairs)
        & (CustomerMemoryPairing.expires_at <= now)
    ).returning(CustomerMemoryPairing.id)).all())
    return removed


def main() -> None:
    settings = MemoryRetentionSettings()
    engine = create_database_engine(settings, service_name="memory-retention")
    try:
        with Session(engine) as session, session.begin():
            count = purge_expired(session, settings.customer_memory_retention_days)
        print(json.dumps({"deleted": count}))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
