"""Device management endpoints."""

from pathlib import Path
from typing import List, Dict, Any
import json

from fastapi import APIRouter, HTTPException, status, Query

from schemas.db_models.models import DeviceCreate, DeviceUpdate, DeviceResponse, DeviceListItem
from db.devices import create_device, get_all_devices, get_device_by_id, get_device_by_device_id, update_device, delete_device
from utils.map_csv_to_json import get_register_map_for_device
from logger import get_logger

router = APIRouter(prefix="/devices", tags=["devices"])
logger = get_logger(__name__)

@router.get("/device", response_model=List[DeviceListItem])
async def get_all_devices_endpoint():
    """
    Get all devices.
    
    Returns:
        List of all devices (without register_map for performance)
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
async def get_device(
    device_id: int, 
    include_register_map: bool = Query(False, description="Include register map in response")
):
    """
    Get a device by device_id (Modbus unit/slave ID).
    
    The device_id parameter refers to the Modbus unit/slave ID (e.g., 111, 222),
    not the database primary key. The function queries directly by device_id,
    which is unique and indexed for optimal performance.
    
    Args:
        device_id: Modbus unit/slave ID (not the database primary key)
        include_register_map: If True, include register map (loaded lazily from DB/CSV)
        
    Returns:
        Device data with optional register map
        
    Raises:
        HTTPException: If device not found
    """
    try:
        device = await get_device_by_device_id(device_id)
        if device is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Device with device_id {device_id} not found"
            )
        
        # Load register map if requested
        if include_register_map:
            logger.debug(f"Loading register map for device '{device.name}' (device_id: {device_id}, primary key: {device.id})")
            try:
                register_map = await get_register_map_for_device(device.name)
                logger.debug(f"Register map loaded: {register_map is not None}")
                
                # Ensure register_map is a dict, not a string
                if register_map is not None and isinstance(register_map, str):
                    try:
                        register_map = json.loads(register_map)
                        logger.debug(f"Parsed register_map from string to dict")
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse register_map JSON string: {e}")
                        register_map = None
                elif register_map is not None and not isinstance(register_map, dict):
                    logger.warning(f"register_map is not a dict (type: {type(register_map)}), setting to None")
                    register_map = None
                    
            except Exception as e:
                logger.error(f"Error loading register map for device '{device.name}': {e}", exc_info=True)
                # Set register_map to None if there's an error loading it
                register_map = None
            
            # Create a new DeviceResponse with the register_map populated
            try:
                response = DeviceResponse(
                    id=device.id,
                    name=device.name,
                    host=device.host,
                    port=device.port,
                    device_id=device.device_id,
                    description=device.description,
                    register_map=register_map,
                    poll_address=device.poll_address,
                    poll_count=device.poll_count,
                    poll_kind=device.poll_kind,
                    poll_enabled=device.poll_enabled,
                    created_at=device.created_at,
                    updated_at=device.updated_at
                )
                logger.debug(f"Successfully created DeviceResponse for device {device_id}")
                return response
            except Exception as e:
                logger.error(f"Error creating DeviceResponse for device {device_id}: {e}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to construct device response: {str(e)}"
                )
        
        return device
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting device {device_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve device"
        )


@router.put("/device/{device_id}", response_model=DeviceResponse)
async def update_existing_device(device_id: int, device_update: DeviceUpdate):
    """
    Update a Modbus device.
    
    The device_id parameter refers to the Modbus unit/slave ID (e.g., 111, 222),
    not the database primary key.
    
    Args:
        device_id: Modbus unit/slave ID (not the database primary key)
        device_update: Device update data (only provided fields will be updated)
        
    Returns:
        Updated device with new timestamps
        
    Raises:
        HTTPException: If device not found, name already exists, or database error occurs
        
    Note:
        register_map cannot be updated through this endpoint.
        Register maps can be retrieved through the /api/device/{device_name}/register_map endpoint.
    """
    try:
        # DeviceUpdate schema doesn't include register_map, so Pydantic will automatically
        # reject any attempts to update it (returns 422 validation error)
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


@router.delete("/device/{device_id}", response_model=DeviceResponse)
async def delete_existing_device(device_id: int):
    """
    Delete a Modbus device.
    
    The device_id parameter refers to the Modbus unit/slave ID (e.g., 111, 222),
    not the database primary key.
    
    Args:
        device_id: Modbus unit/slave ID (not the database primary key)
        
    Returns:
        Metadata of the deleted device
        
    Raises:
        HTTPException: If device not found or database error occurs
    """
    try:
        deleted_device = await delete_device(device_id)
        if deleted_device is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Device with device_id {device_id} not found"
            )
        return deleted_device
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting device: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete device"
        )


@router.get("/device/{device_name}/register_map", response_model=Dict[str, Any])
async def get_device_register_map(device_name: str):
    """
    Get register map for a device in JSON format.
    
    Uses lazy loading: checks DB first, then falls back to CSV if not found.
    If loaded from CSV, it will be saved to DB for future use.
    
    Args:
        device_name: Device identifier (e.g., "main-sel-751")
        
    Returns:
        JSON structure with metadata and registers array
        
    Raises:
        HTTPException: If device name not found or register map cannot be loaded
    """
    try:
        # Use wrapper function for lazy loading (DB first, then CSV)
        register_map = await get_register_map_for_device(device_name)
        
        if register_map is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Register map not found for device '{device_name}'. Device may not be mapped to a CSV file or CSV file does not exist."
            )
        
        return register_map
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error getting register map for device '{device_name}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve register map"
        )

