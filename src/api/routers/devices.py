"""Device management endpoints."""

from typing import List, Literal

from fastapi import APIRouter, HTTPException, Query, status

from schemas.api_models import (
    DeviceCreateRequest,
    DeviceUpdate,
    DeviceWithConfigs,
    DeviceDeleteResponse,
)
from api.controllers.devices import (
    create_device,
    delete_device,
    get_all_devices,
    get_device_by_id,
    restore_device,
    update_device,
)
from utils.exceptions import AppError
from logger import get_logger

router = APIRouter(prefix="/devices", tags=["devices"])
logger = get_logger(__name__)


@router.get("/site/{site_id}/devices", response_model=List[DeviceWithConfigs])
async def get_all_devices_endpoint(
    site_id: int,
    include_deleted: bool = Query(False, description="Include soft-deleted devices"),
):
    try:
        devices = await get_all_devices(site_id, include_deleted=include_deleted)
    except AppError as e:
        detail = {"error": type(e).__name__, "message": e.message}
        if e.payload:
            detail.update(e.payload)
        raise HTTPException(status_code=e.http_status_code, detail=detail)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An internal server error occurred")

    if not devices:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No devices found for site '{site_id}'")
    return devices


@router.post("/site/{site_id}/devices", response_model=DeviceWithConfigs, status_code=status.HTTP_201_CREATED)
async def create_new_device(site_id: int, device: DeviceCreateRequest):
    try:
        return await create_device(device, site_id=site_id)
    except AppError as e:
        detail = {"error": type(e).__name__, "message": e.message}
        if e.payload:
            detail.update(e.payload)
        raise HTTPException(status_code=e.http_status_code, detail=detail)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An internal server error occurred")


@router.get("/site/{site_id}/devices/{device_id}", response_model=DeviceWithConfigs)
async def get_device(
    site_id: int,
    device_id: int,
    include_deleted: bool = Query(False, description="Return the device even if soft-deleted"),
):
    try:
        return await get_device_by_id(site_id, device_id, include_deleted=include_deleted)
    except AppError as e:
        detail = {"error": type(e).__name__, "message": e.message}
        if e.payload:
            detail.update(e.payload)
        raise HTTPException(status_code=e.http_status_code, detail=detail)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An internal server error occurred")


@router.put("/site/{site_id}/devices/{device_id}", response_model=DeviceWithConfigs)
async def update_existing_device(site_id: int, device_id: int, device_update: DeviceUpdate):
    try:
        return await update_device(device_id, device_update, site_id=site_id)
    except AppError as e:
        detail = {"error": type(e).__name__, "message": e.message}
        if e.payload:
            detail.update(e.payload)
        raise HTTPException(status_code=e.http_status_code, detail=detail)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An internal server error occurred")


@router.delete("/site/{site_id}/devices/{device_id}", response_model=DeviceDeleteResponse)
async def delete_existing_device(
    site_id: int,
    device_id: int,
    mode: Literal["soft", "hard"] = Query(
        "soft",
        description="soft: preserves device_id — restorable via /restore. hard: permanent deletion, requires confirm=true.",
    ),
    confirm: bool = Query(False, description="Must be true to execute a hard delete"),
):
    try:
        deleted_device = await delete_device(device_id, site_id=site_id, mode=mode, confirm=confirm)
    except AppError as e:
        detail = {"error": type(e).__name__, "message": e.message}
        if e.payload:
            detail.update(e.payload)
        raise HTTPException(status_code=e.http_status_code, detail=detail)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An internal server error occurred")

    if deleted_device is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Device with id {device_id} not found in site '{site_id}'")
    return DeviceDeleteResponse(device_id=deleted_device.device_id, site_id=deleted_device.site_id, mode=mode)


@router.post("/site/{site_id}/devices/{device_id}/restore", response_model=DeviceWithConfigs)
async def restore_existing_device(site_id: int, device_id: int):
    """Restore a soft-deleted device and all its soft-deleted points under the same device_id."""
    try:
        return await restore_device(device_id, site_id=site_id)
    except AppError as e:
        detail = {"error": type(e).__name__, "message": e.message}
        if e.payload:
            detail.update(e.payload)
        raise HTTPException(status_code=e.http_status_code, detail=detail)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An internal server error occurred")
