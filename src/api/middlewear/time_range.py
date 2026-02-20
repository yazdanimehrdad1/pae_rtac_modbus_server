"""Middleware for validating time range query params."""

from datetime import datetime
from typing import Optional

from fastapi import Request
from fastapi.responses import JSONResponse


def _parse_iso_datetime(value: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None

# TODO : take care of datetime format
async def validate_time_range(request: Request, call_next):
    start_time = request.query_params.get("start_time")
    end_time = request.query_params.get("end_time")

    if start_time and end_time:
        start_dt = _parse_iso_datetime(start_time)
        end_dt = _parse_iso_datetime(end_time)
        if start_dt is None or end_dt is None:
            return JSONResponse(
                status_code=400,
                content={
                    "detail": "Invalid time format. Expected ISO format (e.g., '2025-01-18T08:00:00Z')"
                },
            )
        if start_dt > end_dt:
            return JSONResponse(
                status_code=400,
                content={"detail": "start_time must be less than or equal to end_time"},
            )

    return await call_next(request)
