from fastapi import APIRouter, HTTPException, Query, status
from typing import List, Literal, Optional

from helpers.device_points import (
    get_device_points,
    get_deleted_device_points,
    get_device_point,
    update_device_point,
    delete_device_points,
    restore_device_point,
    bulk_upsert_device_points,
)
from api.controllers.devices import get_device_by_id
from db.devices import lock_device_scan_ranges, reset_device_scan_ranges
from schemas.api_models import DevicePointResponse
from schemas.api_models.requests import (
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
    include_deleted: bool = Query(default=False, description="Include soft-deleted points"),
):
    """Get all registered points for a specific device."""
    try:
        await get_device_by_id(site_id, device_id)
        points = await get_device_points(device_id, category=category, include_deleted=include_deleted)
        return points
    except Exception as e:
        _point_error(e)


@router.get("/site/{site_id}/device/{device_id}/deleted", response_model=List[DevicePointResponse])
async def get_deleted_points_for_device(
    site_id: int,
    device_id: int,
):
    """Get all soft-deleted points for a specific device, ordered by most recently deleted."""
    try:
        await get_device_by_id(site_id, device_id)
        points = await get_deleted_device_points(device_id)
        return points
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


@router.delete("/site/{site_id}/device/{device_id}", response_model=List[DevicePointResponse])
async def delete_points(
    site_id: int,
    device_id: int,
    point_ids: str = Query(..., description="Comma-separated point IDs, e.g. 1,2,3"),
    mode: Literal["soft", "hard"] = Query(default="soft", description="soft=preserve readings, hard=cascade delete"),
    confirm: bool = Query(default=False, description="Required for mode=hard"),
):
    """Delete one or more device points. Returns the deleted points. Soft delete preserves readings; hard delete is permanent."""
    try:
        if mode == "hard" and not confirm:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "ConfirmationRequired", "message": "Set confirm=true to permanently delete points and all their readings"},
            )
        ids = [int(i.strip()) for i in point_ids.split(",") if i.strip()]
        await get_device_by_id(site_id, device_id)
        missing, deleted = await delete_device_points(device_id, ids, hard=(mode == "hard"))
        if missing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "NotFoundError", "message": f"Points not found: {missing}"},
            )
        return [DevicePointResponse.model_validate(p, from_attributes=True) for p in deleted]
    except HTTPException:
        raise
    except Exception as e:
        _point_error(e)


@router.post("/site/{site_id}/device/{device_id}/{point_id}/restore", response_model=DevicePointResponse)
async def restore_point(
    site_id: int,
    device_id: int,
    point_id: int,
):
    """Restore a soft-deleted device point. Triggers scan range recompute."""
    try:
        await get_device_by_id(site_id, device_id)
        point = await restore_device_point(point_id)
        return DevicePointResponse.model_validate(point, from_attributes=True)
    except Exception as e:
        _point_error(e)
