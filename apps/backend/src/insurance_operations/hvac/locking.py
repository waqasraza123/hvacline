from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from insurance_operations.database.models.hvac import BusinessSchedule
from insurance_operations.database.models.identity import Agency


def lock_business_schedule(
    session: Session, agency_id: UUID, *, skip_locked: bool = False
) -> BusinessSchedule | None:
    agency = session.scalar(
        select(Agency.id)
        .where(Agency.id == agency_id)
        .with_for_update(read=True, key_share=True, skip_locked=skip_locked)
    )
    if agency is None:
        return None
    return session.scalar(
        select(BusinessSchedule)
        .where(BusinessSchedule.agency_id == agency_id)
        .with_for_update(skip_locked=skip_locked)
    )
