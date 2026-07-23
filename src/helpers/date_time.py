"""Datetime parsing and time-range helpers."""

from datetime import datetime, timedelta, timezone
from typing import Literal, Optional


def parse_iso_datetime(value: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


TimeRange = Literal['1H', '6H', '12H', '1D', '2D', '3D', '1W', '1M', '3M']

_TIME_RANGE_DELTAS: dict[str, timedelta] = {
    '1H':  timedelta(hours=1),
    '6H':  timedelta(hours=6),
    '12H': timedelta(hours=12),
    '1D':  timedelta(days=1),
    '2D':  timedelta(days=2),
    '3D':  timedelta(days=3),
    '1W':  timedelta(weeks=1),
    '1M':  timedelta(days=30),
    '3M':  timedelta(days=90),
}


def resolve_time_range(time_range: str) -> tuple[datetime, datetime]:
    """Return (start, end) UTC datetimes for the given time_range token relative to now."""
    delta = _TIME_RANGE_DELTAS.get(time_range)
    if delta is None:
        raise ValueError(
            f"Unknown time_range '{time_range}'. Valid values: {list(_TIME_RANGE_DELTAS)}"
        )
    end = datetime.now(timezone.utc)
    return end - delta, end
