"""Datetime parsing helpers."""

from datetime import datetime
from typing import Optional


def parse_iso_datetime(value: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
