"""Device management endpoints."""

from typing import List

from fastapi import APIRouter, HTTPException, status

from schemas.db_models.models import (
    DeviceCreateRequest,
    DeviceUpdate,
    DeviceWithConfigs,
    DeviceDeleteResponse,
)
from db.devices import get_all_devices
from helpers.devices import (
    create_device_cache_db,
    delete_device_cache_db,
    get_device_cache_db,
    update_device_cache_db,
)
from utils.exceptions import AppError, NotFoundError, ConflictError, ValidationError, InternalError
from logger import get_logger

router = APIRouter(prefix="/devices", tags=["devices"])
logger = get_logger(__name__)

@router.get("/site/{site_id}/devices", response_model=List[DeviceWithConfigs])
async def get_all_devices_endpoint(site_id: int):
    """
    Get all devices.
    
    Returns:
        List of all devices
        
    Raises:
        HTTPException: If database error occurs
    """
    try:
        devices = await get_all_devices(site_id)
        if not devices:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No devices found for site '{site_id}'"
            )
        return devices
    except AppError as e:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        if isinstance(e, NotFoundError):
            status_code = status.HTTP_404_NOT_FOUND
        elif isinstance(e, ConflictError):
            status_code = status.HTTP_409_CONFLICT
        elif isinstance(e, ValidationError):
            status_code = status.HTTP_400_BAD_REQUEST
            
        detail = {"error": type(e).__name__, "message": e.message}
        if e.payload:
            detail.update(e.payload)
        raise HTTPException(status_code=status_code, detail=detail)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred"
        )


@router.post("/site/{site_id}/devices", response_model=DeviceWithConfigs, status_code=status.HTTP_201_CREATED)
async def create_new_device(site_id: int, device: DeviceCreateRequest):
    """
    Create a new Modbus device.
    
    Args:
        device: Device configuration data
        
    Returns:
        Created device with ID and timestamps
        
    Raises:
        HTTPException: If device name already exists or database error occurs
    """
    try:
        return await create_device_cache_db(device, site_id=site_id)
    except AppError as e:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        if isinstance(e, NotFoundError):
            status_code = status.HTTP_404_NOT_FOUND
        elif isinstance(e, ConflictError):
            status_code = status.HTTP_409_CONFLICT
        elif isinstance(e, ValidationError):
            status_code = status.HTTP_400_BAD_REQUEST
            
        detail = {"error": type(e).__name__, "message": e.message}
        if e.payload:
            detail.update(e.payload)
        raise HTTPException(status_code=status_code, detail=detail)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred"
        )


@router.get("/site/{site_id}/devices/{device_id}", response_model=DeviceWithConfigs)
async def get_device(site_id: int, device_id: int):
    """
    Get a device by its database primary key.
    
    Args:
        device_id: Device ID (database primary key)
        
    Returns:
        Device data
        
    Raises:
        HTTPException: If device not found
    """
    try:
        return await get_device_cache_db(site_id, device_id)
    except AppError as e:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        if isinstance(e, NotFoundError):
            status_code = status.HTTP_404_NOT_FOUND
        elif isinstance(e, ConflictError):
            status_code = status.HTTP_409_CONFLICT
        elif isinstance(e, ValidationError):
            status_code = status.HTTP_400_BAD_REQUEST
            
        detail = {"error": type(e).__name__, "message": e.message}
        if e.payload:
            detail.update(e.payload)
        raise HTTPException(status_code=status_code, detail=detail)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred"
        )


@router.put("/site/{site_id}/devices/{device_id}", response_model=DeviceWithConfigs)
async def update_existing_device(site_id: int, device_id: int, device_update: DeviceUpdate):
    """
    Update a Modbus device.
    
    Args:
        device_id: Device ID (database primary key)
        device_update: Device update data (only provided fields will be updated)
        
    Returns:
        Updated device with new timestamps
        
    Raises:
        HTTPException: If device not found, name already exists, or database error occurs
    """
    try:
        return await update_device_cache_db(device_id, device_update, site_id=site_id)
    except AppError as e:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        if isinstance(e, NotFoundError):
            status_code = status.HTTP_404_NOT_FOUND
        elif isinstance(e, ConflictError):
            status_code = status.HTTP_409_CONFLICT
        elif isinstance(e, ValidationError):
            status_code = status.HTTP_400_BAD_REQUEST
            
        detail = {"error": type(e).__name__, "message": e.message}
        if e.payload:
            detail.update(e.payload)
        raise HTTPException(status_code=status_code, detail=detail)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred"
        )

# TODO: lets make sure cascade delete is implemented and soft delete is implemented
@router.delete("/site/{site_id}/devices/{device_id}", response_model=DeviceDeleteResponse)
async def delete_existing_device(site_id: int, device_id: int):
    """
    Delete a Modbus device.
    
    Args:
        device_id: Device ID (database primary key)
        
    Returns:
        Metadata of the deleted device
        
    Raises:
        HTTPException: If device not found or database error occurs
    """
    try:
        deleted_device = await delete_device_cache_db(device_id, site_id=site_id)
        if deleted_device is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Device with id {device_id} not found in site '{site_id}'"
            )
        return {"device_id": deleted_device.device_id, "site_id": deleted_device.site_id}
    except AppError as e:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        if isinstance(e, NotFoundError):
            status_code = status.HTTP_404_NOT_FOUND
        elif isinstance(e, ConflictError):
            status_code = status.HTTP_409_CONFLICT
        elif isinstance(e, ValidationError):
            status_code = status.HTTP_400_BAD_REQUEST
            
        detail = {"error": type(e).__name__, "message": e.message}
        if e.payload:
            detail.update(e.payload)
        raise HTTPException(status_code=status_code, detail=detail)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred"
        )

