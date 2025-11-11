"""Device management endpoints."""

from typing import List

from fastapi import APIRouter, HTTPException, status

from schemas.db_models.models import DeviceCreate, DeviceUpdate, DeviceResponse
from db.devices import create_device, get_all_devices, get_device_by_id, update_device, delete_device
from logger import get_logger

router = APIRouter(prefix="/devices", tags=["devices"])
logger = get_logger(__name__)


@router.get("/device", response_model=List[DeviceResponse])
async def get_all_devices_endpoint():
    """
    Get all devices.
    
    Returns:
        List of all devices
    """
    try:
        devices = await get_all_devices()
        return devices
    except Exception as e:
        logger.error(f"Error getting all devices: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve devices"
        )


@router.post("/device", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED)
async def create_new_device(device: DeviceCreate):
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
        created_device = await create_device(device)
        return created_device
    except ValueError as e:
        # Handle unique constraint violation (duplicate name)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating device: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create device"
        )


@router.get("/device/{device_id}", response_model=DeviceResponse)
async def get_device(device_id: int):
    """
    Get a device by ID.
    
    Args:
        device_id: Device ID
        
    Returns:
        Device data
        
    Raises:
        HTTPException: If device not found
    """
    device = await get_device_by_id(device_id)
    if device is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device with ID {device_id} not found"
        )
    return device


@router.put("/device/{device_id}", response_model=DeviceResponse)
async def update_existing_device(device_id: int, device_update: DeviceUpdate):
    """
    Update a Modbus device.
    
    Args:
        device_id: Device ID to update
        device_update: Device update data (only provided fields will be updated)
        
    Returns:
        Updated device with new timestamps
        
    Raises:
        HTTPException: If device not found, name already exists, or database error occurs
    """
    try:
        updated_device = await update_device(device_id, device_update)
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


@router.delete("/device/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_device(device_id: int):
    """
    Delete a Modbus device.
    
    Args:
        device_id: Device ID to delete
        
    Raises:
        HTTPException: If device not found or database error occurs
    """
    try:
        deleted = await delete_device(device_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Device with ID {device_id} not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting device: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete device"
        )

