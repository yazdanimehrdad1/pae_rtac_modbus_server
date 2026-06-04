from fastapi import APIRouter, HTTPException, Query, status
from typing import List, Literal, Optional

from helpers.device_points import (
    get_device_points,
    get_device_point,
    create_device_point,
    update_device_point,
    delete_device_point,
    bulk_upsert_device_points,
)
from api.controllers.devices import get_device_by_id
from db.devices import lock_device_scan_ranges, reset_device_scan_ranges
from schemas.api_models import DevicePointResponse
from schemas.api_models.requests import (
    DevicePointCreateRequest,
    DevicePointUpdateRequest,
    DevicePointsBulkRequest,
    DeviceScanRanges,
)
from utils.exceptions import AppError

router = APIRouter(
    prefix="/device-points",
    tags=["device-points"],
)


def _point_error(e: Exception):
    if isinstance(e, AppError):
        detail = {"error": type(e).__name__, "message": e.message}
        if e.payload:
            detail.update(e.payload)
        raise HTTPException(status_code=e.http_status_code, detail=detail)
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=str(e),
    )


@router.get("/site/{site_id}/device/{device_id}", response_model=List[DevicePointResponse])
async def get_points_for_device(
    site_id: int,
    device_id: int,
    category: Optional[Literal["NATIVE", "STANDARDIZED", "VIRTUAL"]] = Query(
        default=None,
        description="Filter points by category",
    ),
):
    """Get all registered points for a specific device."""
    try:
        await get_device_by_id(site_id, device_id)
        points = await get_device_points(device_id, category=category)
        return points
    except Exception as e:
        _point_error(e)


@router.post(
    "/site/{site_id}/device/{device_id}",
    response_model=DevicePointResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_point(
    site_id: int,
    device_id: int,
    body: DevicePointCreateRequest,
):
    """Create a device point directly (Config-free). Triggers scan range recompute unless locked."""
    try:
        await get_device_by_id(site_id, device_id)
        point = await create_device_point(site_id, device_id, body)
        return DevicePointResponse.model_validate(point, from_attributes=True)
    except Exception as e:
        _point_error(e)


# --- Fixed-path PUT/DELETE routes MUST come before /{point_id} variants ---

@router.put("/site/{site_id}/device/{device_id}/scan-ranges", response_model=DeviceScanRanges)
async def override_scan_ranges(
    site_id: int,
    device_id: int,
    body: DeviceScanRanges,
):
    """Manually set scan ranges and lock them (auto-recompute disabled until reset)."""
    try:
        await get_device_by_id(site_id, device_id)
        await lock_device_scan_ranges(device_id, body)
        return body
    except Exception as e:
        _point_error(e)


@router.delete("/site/{site_id}/device/{device_id}/scan-ranges", response_model=DeviceScanRanges)
async def reset_scan_ranges(
    site_id: int,
    device_id: int,
):
    """Clear the scan ranges lock and recompute from current NATIVE points."""
    try:
        await get_device_by_id(site_id, device_id)
        ranges = await reset_device_scan_ranges(device_id)
        return ranges
    except Exception as e:
        _point_error(e)


@router.put(
    "/site/{site_id}/device/{device_id}/bulk",
    response_model=List[DevicePointResponse],
)
async def bulk_upsert_points(
    site_id: int,
    device_id: int,
    body: DevicePointsBulkRequest,
):
    """
    Upsert multiple device points in one call.
    Points matched by name: existing names are updated, new names are created.
    Scan range recompute runs once at the end.
    """
    try:
        await get_device_by_id(site_id, device_id)
        points = await bulk_upsert_device_points(site_id, device_id, body)
        return [DevicePointResponse.model_validate(p, from_attributes=True) for p in points]
    except Exception as e:
        _point_error(e)


@router.put("/site/{site_id}/device/{device_id}/{point_id}", response_model=DevicePointResponse)
async def update_point(
    site_id: int,
    device_id: int,
    point_id: int,
    body: DevicePointUpdateRequest,
):
    """Update a device point. Triggers scan range recompute unless locked."""
    try:
        await get_device_by_id(site_id, device_id)
        point = await update_device_point(point_id, body)
        return DevicePointResponse.model_validate(point, from_attributes=True)
    except Exception as e:
        _point_error(e)


@router.delete("/site/{site_id}/device/{device_id}/{point_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_point(
    site_id: int,
    device_id: int,
    point_id: int,
):
    """Delete a device point. Triggers scan range recompute unless locked."""
    try:
        await get_device_by_id(site_id, device_id)
        deleted = await delete_device_point(point_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Point {point_id} not found")
    except HTTPException:
        raise
    except Exception as e:
        _point_error(e)
