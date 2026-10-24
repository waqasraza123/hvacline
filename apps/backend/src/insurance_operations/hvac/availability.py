from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from insurance_operations.hvac.schemas import ScheduleInput, Slot, WorkingWindow


def utc_instant(day: date, window_time: time, zone: ZoneInfo) -> datetime | None:
    local = datetime.combine(day, window_time, tzinfo=zone)
    utc = local.astimezone(UTC)
    if utc.astimezone(zone).replace(tzinfo=None) != local.replace(tzinfo=None):
        return None
    if local.replace(fold=0).utcoffset() != local.replace(fold=1).utcoffset():
        return None
    return utc


def within_window(
    day: date,
    start: datetime,
    end: datetime,
    windows: list[WorkingWindow],
    zone: ZoneInfo,
) -> bool:
    for window in windows:
        if window.weekday != day.weekday():
            continue
        lower = utc_instant(day, window.start, zone)
        upper = utc_instant(day, window.end, zone)
        if lower is not None and upper is not None and lower <= start < end <= upper:
            return True
    return False


def candidate_slots(
    configuration: ScheduleInput, day: date, now: datetime
) -> list[Slot]:
    if not configuration.enabled:
        return []
    zone = ZoneInfo(configuration.timezone)
    local_today = now.astimezone(zone).date()
    if day < local_today or day > local_today + timedelta(
        days=configuration.horizon_days
    ):
        return []
    slots: list[Slot] = []
    duration = timedelta(minutes=configuration.duration_minutes)
    earliest = now + timedelta(minutes=configuration.notice_minutes)
    for team in configuration.teams:
        if day in team.unavailable_dates:
            continue
        seen: set[datetime] = set()
        for window in team.windows:
            if window.weekday != day.weekday():
                continue
            cursor = datetime.combine(day, window.start)
            last = datetime.combine(day, window.end)
            while cursor < last:
                start = utc_instant(day, cursor.time(), zone)
                cursor += timedelta(minutes=15)
                if start is None or start < earliest or start in seen:
                    continue
                end = start + duration
                if within_window(day, start, end, team.windows, zone) and within_window(
                    day, start, end, configuration.windows, zone
                ):
                    seen.add(start)
                    slots.append(Slot(team_key=team.key, starts_at=start, ends_at=end))
    return sorted(slots, key=lambda slot: (slot.starts_at, slot.team_key))


def overlaps(
    start: datetime, end: datetime, busy_start: datetime, busy_end: datetime
) -> bool:
    return start < busy_end and busy_start < end
