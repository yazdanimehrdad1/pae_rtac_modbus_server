"""Device management endpoints."""

from typing import List

from fastapi import APIRouter, HTTPException, status

from schemas.db_models.models import (
    DeviceCreate,
    DeviceUpdate,
    DeviceResponse,
    DeviceListItem,
    DeviceDeleteResponse,
)
from db.devices import get_all_devices
from helpers.devices import (
    create_device_cache_db,
    delete_device_cache_db,
    get_device_cache_db,
    update_device_cache_db,
)
from logger import get_logger

router = APIRouter(prefix="/devices", tags=["devices"])
logger = get_logger(__name__)

@router.get("/site/{site_id}/devices", response_model=List[DeviceListItem])
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
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting devices: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve devices"
        )


@router.post("/site/{site_id}/devices", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED)
async def create_new_device(site_id: int, device: DeviceCreate):
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
        created_device = await create_device_cache_db(device, site_id=site_id)
        return created_device
    except ValueError as e:
        error_msg = str(e)
        # Handle unique constraint violations
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=error_msg
        )
    except Exception as e:
        logger.error(f"Error creating device: {e}", exc_info=True)
        error_detail = {
            "error": "Failed to create device",
            "error_type": type(e).__name__,
            "message": str(e)
        }
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_detail
        )


@router.get("/site/{site_id}/devices/{device_id}", response_model=DeviceResponse)
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting device {device_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve device"
        )


@router.put("/site/{site_id}/devices/{device_id}", response_model=DeviceResponse)
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
        updated_device = await update_device_cache_db(device_id, device_update, site_id=site_id)
        return updated_device
    except ValueError as e:
        # Handle not found or unique constraint violation
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(e)
            )
    except Exception as e:
        logger.error(f"Error updating device: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update device"
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
        return {"device_id": deleted_device.id, "site_id": deleted_device.site_id}
    except ValueError as e:
        error_msg = str(e)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=error_msg
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting device: {e}", exc_info=True)
        error_detail = {
            "error": "Failed to delete device",
            "error_type": type(e).__name__,
            "message": str(e)
        }
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_detail
        )

