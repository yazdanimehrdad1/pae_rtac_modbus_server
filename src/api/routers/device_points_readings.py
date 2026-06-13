"""Device point readings endpoints — query timeseries by device_point_id."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status

from helpers.reads.calculate_reads import translate_bitfield_to_named_map, translate_reading
from helpers.reads.device_points_readings import (
    get_latest_readings_by_point_ids,
    get_timeseries_by_point_ids,
)
from logger import get_logger
from schemas.api_models import (
    LatestMeta,
    LatestResponse,
    PointLatest,
    PointTimeseries,
    TimeseriesMeta,
    TimeseriesPoint,
    TimeseriesResponse,
)

router = APIRouter(prefix="/device-point-readings", tags=["device-point-readings"])
logger = get_logger(__name__)


# --- Helpers ---

def _parse_point_ids(raw: Optional[str]) -> list[int]:
    if not raw:
        return []
    try:
        return [int(p.strip()) for p in raw.split(",") if p.strip()]
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="point_ids must be a comma-separated list of integers (e.g. '1,2,3')",
        )


# --- Endpoints ---

@router.get("/site/{site_id}/device/{device_id}/latest", response_model=LatestResponse, response_model_exclude_none=True)
async def get_latest_readings(
    site_id: int,
    device_id: int,
    point_ids: Optional[str] = Query(None, description="Comma-separated device_point_ids (e.g. '1,2,3'). If omitted, returns all points for the device."),
    translate: bool = Query(False, description="Translate enum/bitfield values to human-readable form"),
):
    """Get the latest reading for each requested device point, keyed by device_point_id."""
    ids = _parse_point_ids(point_ids)

    try:
        rows = await get_latest_readings_by_point_ids(ids, site_id=site_id, device_id=device_id)
    except Exception as e:
        logger.error("get_latest_readings failed site=%s device=%s point_ids=%s: %s", site_id, device_id, ids, e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve readings")

    readings = {
        str(row["device_point_id"]): PointLatest.model_validate({
            **row,
            "translated_value": translate_reading(
                row["derived_value"],
                row["bitfield_detail"],
                row["enum_detail"],
            ) if translate else None,
        })
        for row in rows
    }
    return LatestResponse(
        meta=LatestMeta(
            site_id=site_id,
            device_id=device_id,
            point_ids=ids or None,
            total_count=len(readings),
        ),
        readings=readings,
    )


@router.get("/timeseries/site/{site_id}/device/{device_id}", response_model=TimeseriesResponse, response_model_exclude_none=True)
async def get_timeseries_readings(
    site_id: int,
    device_id: int,
    point_ids: Optional[str] = Query(None, description="Comma-separated device_point_ids (e.g. '1,2,3'). If omitted, returns all points for the device."),
    start_time: Optional[datetime] = Query(None, description="Start time in ISO format (e.g. '2025-01-18T08:00:00Z')"),
    end_time: Optional[datetime] = Query(None, description="End time in ISO format (e.g. '2025-01-18T09:00:00Z')"),
    limit: int = Query(1000, ge=1, le=10000, description="Maximum rows per point (each point gets up to this many readings)"),
    translate: bool = Query(False, description="Translate enum/bitfield values to human-readable form"),
):
    """
    Get time-series readings for each requested device point, keyed by device_point_id.
    Each entry contains point metadata and a timeseries array sorted oldest-first.
    """
    ids = _parse_point_ids(point_ids)

    if start_time and end_time and start_time >= end_time:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="start_time must be before end_time",
        )

    try:
        rows = await get_timeseries_by_point_ids(
            ids, site_id=site_id, device_id=device_id,
            start_time=start_time, end_time=end_time, limit=limit,
        )
    except Exception as e:
        logger.error("get_timeseries_readings failed site=%s device=%s point_ids=%s: %s", site_id, device_id, ids, e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve timeseries")

    readings: dict[str, PointTimeseries] = {}
    for row in rows:
        key = str(row["device_point_id"])
        if key not in readings:
            extra: dict = {}
            if translate:
                extra["enum_map"] = row["enum_detail"] or None
                if row["bitfield_detail"]:
                    extra["bit_labels"] = list(
                        translate_bitfield_to_named_map(0.0, row["bitfield_detail"]).keys()
                    )
            readings[key] = PointTimeseries.model_validate({**row, **extra})
        readings[key].timeseries.append(TimeseriesPoint.model_validate({
            **row,
            "translated_value": translate_reading(
                row["derived_value"],
                row["bitfield_detail"],
                row["enum_detail"],
            ) if translate else None,
        }))
        readings[key].count += 1

    return TimeseriesResponse(
        meta=TimeseriesMeta(
            site_id=site_id,
            device_id=device_id,
            point_ids=ids or None,
            total_count=len(rows),
            start_time=start_time,
            end_time=end_time,
        ),
        readings=readings,
    )
