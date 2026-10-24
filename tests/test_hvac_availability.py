from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from insurance_operations.hvac.availability import (
    candidate_slots,
    overlaps,
    utc_instant,
)
from insurance_operations.hvac.schemas import ScheduleInput, WorkingWindow


def schedule() -> ScheduleInput:
    return ScheduleInput(
        expected_version=0,
        enabled=True,
        timezone="America/New_York",
        postal_codes=["10001"],
        windows=[WorkingWindow(weekday=0, start="09:00", end="17:00")],
        teams=[
            {
                "key": "team-a",
                "name": "Service team",
                "windows": [{"weekday": 0, "start": "10:00", "end": "14:00"}],
            }
        ],
        notice_minutes=120,
        duration_minutes=60,
    )


def test_slots_intersect_business_and_team_hours_and_use_utc() -> None:
    slots = candidate_slots(
        schedule(), date(2026, 10, 26), datetime(2026, 10, 26, 12, tzinfo=UTC)
    )
    assert slots[0].starts_at == datetime(2026, 10, 26, 14, tzinfo=UTC)
    assert slots[-1].ends_at == datetime(2026, 10, 26, 18, tzinfo=UTC)
    assert len(slots) == 13


def test_disabled_schedule_and_team_time_off_produce_no_slots() -> None:
    configuration = schedule()
    configuration.enabled = False
    now = datetime(2026, 10, 25, tzinfo=UTC)
    assert candidate_slots(configuration, date(2026, 10, 26), now) == []
    configuration.enabled = True
    configuration.teams[0].unavailable_dates = [date(2026, 10, 26)]
    assert candidate_slots(configuration, date(2026, 10, 26), now) == []


def test_nonexistent_and_ambiguous_daylight_saving_times_are_not_offered() -> None:
    from datetime import time

    zone = ZoneInfo("America/New_York")
    assert utc_instant(date(2026, 3, 8), time(2, 30), zone) is None
    assert utc_instant(date(2026, 11, 1), time(1, 30), zone) is None


def test_adjacent_appointments_do_not_conflict() -> None:
    start = datetime(2026, 10, 26, 14, tzinfo=UTC)
    end = datetime(2026, 10, 26, 15, tzinfo=UTC)
    assert not overlaps(start, end, end, datetime(2026, 10, 26, 16, tzinfo=UTC))
    assert overlaps(start, end, start, end)


def test_service_area_and_duplicate_team_validation() -> None:
    value = schedule().model_dump()
    value["postal_codes"] = ["not-a-zip"]
    with pytest.raises(ValidationError):
        ScheduleInput.model_validate(value)
    value = schedule().model_dump()
    value["teams"] = [value["teams"][0], value["teams"][0]]
    with pytest.raises(ValidationError):
        ScheduleInput.model_validate(value)
