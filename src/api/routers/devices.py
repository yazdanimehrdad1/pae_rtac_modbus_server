"""Device management endpoints."""

from pathlib import Path
from typing import List, Dict, Any
import json

from fastapi import APIRouter, HTTPException, status, Query

from schemas.db_models.models import DeviceCreate, DeviceUpdate, DeviceResponse, DeviceListItem
from db.devices import create_device, get_devices_by_site_id, get_device_by_device_id, update_device, delete_device, delete_device_by_id
from db.sites import get_site_by_id
from db.device_register_map import get_register_map
from logger import get_logger

router = APIRouter(prefix="/devices", tags=["devices"])
logger = get_logger(__name__)

@router.get("/site/{site_id}/device", response_model=List[DeviceListItem])
async def get_all_devices_endpoint(site_id: str):
    """
    Get all devices for a specific site.
    
    Args:
        site_id: Site ID (UUID) to filter devices by
    
    Returns:
        List of all devices for the specified site (without register_map for performance)
        
    Raises:
        HTTPException: If site not found or database error occurs
    """
    try:
        # Validate site exists
        site = await get_site_by_id(site_id)
        if site is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Site with id '{site_id}' not found"
            )
        
        devices = await get_devices_by_site_id(site_id)
        return devices
    except HTTPException:
        raise
    except ValueError as e:
        error_msg = str(e)
        if "site" in error_msg.lower() and "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    except Exception as e:
        logger.error(f"Error getting devices for site '{site_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve devices"
        )


@router.post("/site/{site_id}/device", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED)
async def create_new_device(site_id: str, device: DeviceCreate):
    """
    Create a new Modbus device and associate it with a site.
    
    Args:
        site_id: Site ID (UUID) to associate this device with
        device: Device configuration data
        
    Returns:
        Created device with ID and timestamps
        
    Raises:
        HTTPException: If site not found, device name already exists, or database error occurs
    """
    try:
        created_device = await create_device(device, site_id=site_id)
        return created_device
    except ValueError as e:
        error_msg = str(e)
        # Handle site not found
        if "not found" in error_msg.lower() and "site" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg
            )
        # Handle unique constraint violation (duplicate name)
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


@router.get("/site/{site_id}/device/{device_id}", response_model=DeviceResponse)
async def get_device(
    site_id: str,
    device_id: int, 
    include_register_map: bool = Query(False, description="Include register map in response")
):
    """
    Get a device by device_id (Modbus unit/slave ID) and site_id.
    
    The device_id parameter refers to the Modbus unit/slave ID (e.g., 111, 222),
    not the database primary key. The function queries by both device_id and site_id
    to ensure the device belongs to the specified site.
    
    Args:
        site_id: Site ID (UUID) that the device belongs to
        device_id: Modbus unit/slave ID (not the database primary key)
        include_register_map: If True, include register map (loaded lazily from DB)
        
    Returns:
        Device data with optional register map
        
    Raises:
        HTTPException: If site not found, device not found, or device doesn't belong to site
    """
    try:
        # Validate site exists
        site = await get_site_by_id(site_id)
        if site is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Site with id '{site_id}' not found"
            )
        
        device = await get_device_by_device_id(device_id, site_id=site_id)
        if device is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Device with device_id {device_id} not found in site '{site_id}'"
            )
        
        # Load register map if requested
        if include_register_map:
            logger.debug(f"Loading register map for device '{device.name}' (device_id: {device_id}, primary key: {device.id})")
            try:
                register_map = await get_register_map(device.id, site_id=site_id)
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
                    main_type=device.main_type,
                    sub_type=device.sub_type,
                    register_map=register_map,
                    poll_address=device.poll_address,
                    poll_count=device.poll_count,
                    poll_kind=device.poll_kind,
                    poll_enabled=device.poll_enabled,
                    site_id=device.site_id,
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


@router.put("/site/{site_id}/device/{device_id}", response_model=DeviceResponse)
async def update_existing_device(site_id: str, device_id: int, device_update: DeviceUpdate):
    """
    Update a Modbus device.
    
    The device_id parameter refers to the Modbus unit/slave ID (e.g., 111, 222),
    not the database primary key.
    
    Args:
        site_id: Site ID (UUID) that the device belongs to
        device_id: Modbus unit/slave ID (not the database primary key)
        device_update: Device update data (only provided fields will be updated)
        
    Returns:
        Updated device with new timestamps
        
    Raises:
        HTTPException: If site not found, device not found, device doesn't belong to site, name already exists, or database error occurs
        
    Note:
        register_map cannot be updated through this endpoint.
        Register maps are managed through the /api/register_maps endpoints.
    """
    try:
        # Validate site exists
        site = await get_site_by_id(site_id)
        if site is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Site with id '{site_id}' not found"
            )
        
        # DeviceUpdate schema doesn't include register_map, so Pydantic will automatically
        # reject any attempts to update it (returns 422 validation error)
        updated_device = await update_device(device_id, device_update, site_id=site_id)
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
@router.delete("/site/{site_id}/device/{device_id}", response_model=DeviceResponse)
async def delete_existing_device(site_id: str, device_id: int):
    """
    Delete a Modbus device from a specific site.
    
    Args:
        site_id: Site ID (UUID) that the device belongs to
        device_id: Modbus unit/slave ID (not the database primary key)
        
    Returns:
        Metadata of the deleted device
        
    Raises:
        HTTPException: If site not found, device not found, device doesn't belong to site, or database error occurs
    """
    try:
        deleted_device = await delete_device(device_id, site_id=site_id)
        if deleted_device is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Device with device_id {device_id} not found in site '{site_id}'"
            )
        return deleted_device
    except ValueError as e:
        error_msg = str(e)
        # Handle site not found or device doesn't belong to site
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
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

