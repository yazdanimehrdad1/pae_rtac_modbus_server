"""Register map management endpoints."""

from typing import Dict, Any
from fastapi import APIRouter, HTTPException, status
from pydantic import ValidationError

from schemas.db_models.models import RegisterMapCreate
from db.device_register_map import create_register_map, get_register_map, update_register_map, delete_register_map
from db.devices import get_device_by_id_internal
from db.sites import get_site_by_id
from helpers.register_maps import validate_register_map_format, get_expected_format
from logger import get_logger

router = APIRouter(prefix="/register_maps", tags=["register_maps"])
logger = get_logger(__name__)


@router.get("/site/{site_id}/device/{device_id}", response_model=Dict[str, Any])
async def get_device_register_map(site_id: str, device_id: int):
    """
    Get register map for a device in JSON format by device ID.
    
    Retrieves the register map from the database for the specified device.
    
    Args:
        site_id: Site ID (UUID) that the device belongs to
        device_id: Device ID (database primary key)
        
    Returns:
        JSON structure with metadata and registers array
        
    Raises:
        HTTPException: If site not found, device not found, device doesn't belong to site, or register map cannot be loaded
    """
    try:
        # Get register map by device ID with site validation
        register_map = await get_register_map(device_id, site_id=site_id)
        
        if register_map is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Register map not found for device ID '{device_id}' in site '{site_id}'"
            )
        
        return register_map
        
    except ValueError as e:
        error_msg = str(e)
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
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error getting register map for device ID '{device_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve register map"
        )


@router.post("/site/{site_id}/device/{device_id}", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_device_register_map(site_id: str, device_id: int, register_map: RegisterMapCreate):
    """
    Create a register map for a device.
    
    Creates a new register map in the database for the specified device.
    The register map must include a 'registers' array with at least one register definition.
    
    Args:
        site_id: Site ID (UUID) that the device belongs to
        device_id: Device ID (database primary key)
        register_map: Register map data with metadata and registers array
        
    Returns:
        Created register map as stored in the database
        
    Raises:
        HTTPException: If site not found, device not found, device doesn't belong to site, 
                      register map already exists, or validation fails
    """
    try:
        # Validate register map format using helper function (includes all field and range validations)
        validate_register_map_format(register_map)
        
        # Convert Pydantic model to dict
        register_map_dict = register_map.to_dict()
        
        # Create register map in database with site validation
        await create_register_map(site_id, device_id, register_map_dict)
        
        # Retrieve and return the created register map
        created_map = await get_register_map(device_id, site_id=site_id)
        
        if created_map is None:
            # This shouldn't happen, but handle it just in case
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Register map was created but could not be retrieved"
            )
        
        return created_map
        
    except ValidationError as e:
        # Pydantic validation errors occur when request body doesn't match expected format
        # Extract missing or invalid fields from validation errors
        missing_fields = []
        invalid_fields = []
        for error in e.errors():
            field_path = " -> ".join(str(loc) for loc in error.get("loc", []))
            error_type = error.get("type", "")
            error_msg = error.get("msg", "")
            
            if error_type == "missing":
                missing_fields.append({
                    "field": field_path,
                    "message": error_msg
                })
            else:
                invalid_fields.append({
                    "field": field_path,
                    "message": error_msg,
                    "error_type": error_type
                })
        
        error_detail = {
            "error": "Invalid register map format",
            "message": "The request body does not match the expected register map format",
            "expected_format": get_expected_format()
        }
        
        if missing_fields:
            error_detail["missing_fields"] = missing_fields
            error_detail["message"] = "Required fields are missing from the register map"
        
        if invalid_fields:
            error_detail["invalid_fields"] = invalid_fields
            if not missing_fields:
                error_detail["message"] = "Some fields have invalid values or types"
        
        logger.warning(f"Validation error for register map on device {device_id}: {e.errors()}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=error_detail
        )
    except ValueError as e:
        # Handle site not found, device not found, device doesn't belong to site, or duplicate register map
        error_msg = str(e)
        logger.warning(f"ValueError when creating register map for device {device_id} in site {site_id}: {error_msg}")
        
        if "site" in error_msg.lower() and "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg
            )
        elif "device" in error_msg.lower() and "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg
            )
        elif "does not belong" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        elif "already exists" in error_msg.lower() or "duplicate" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=error_msg
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating register map for device ID '{device_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create register map"
        )


@router.put("/site/{site_id}/device/{device_id}", response_model=Dict[str, Any])
async def update_device_register_map(site_id: str, device_id: int, register_map: RegisterMapCreate):
    """
    Update a register map for a device.
    
    Updates the register map in the database for the specified device.
    The register map must include a 'registers' array with at least one register definition.
    
    Args:
        site_id: Site ID (UUID) that the device belongs to
        device_id: Device ID (database primary key)
        register_map: Register map data with metadata and registers array
        
    Returns:
        Updated register map as stored in the database
        
    Raises:
        HTTPException: If site not found, device not found, device doesn't belong to site, 
                      register map not found, or validation fails
    """
    try:
        # Validate register map format using helper function
        validate_register_map_format(register_map)
        
        # Convert Pydantic model to dict
        register_map_dict = register_map.to_dict()
        
        # Update register map in database with site validation
        updated = await update_register_map(site_id, device_id, register_map_dict)
        
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Register map not found for device ID '{device_id}' in site '{site_id}'"
            )
        
        # Retrieve and return the updated register map
        updated_map = await get_register_map(device_id, site_id=site_id)
        
        if updated_map is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Register map was updated but could not be retrieved"
            )
        
        return updated_map
        
    except ValidationError as e:
        error_detail = {
            "error": "Invalid register map format",
            "message": "The request body does not match the expected register map format",
            "expected_format": get_expected_format()
        }
        logger.warning(f"Validation error for register map on device {device_id}: {e.errors()}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=error_detail
        )
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg
            )
        elif "does not belong" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating register map for device ID '{device_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update register map"
        )


@router.delete("/site/{site_id}/device/{device_id}", status_code=status.HTTP_200_OK)
async def delete_device_register_map(site_id: str, device_id: int):
    """
    Delete a register map for a device.
    
    Deletes the register map from the database for the specified device.
    Validates that the device exists and belongs to the specified site.
    
    Args:
        site_id: Site ID (UUID) that the device belongs to
        device_id: Device ID (database primary key, not Modbus device_id)
        
    Returns:
        Success message with details
        
    Raises:
        HTTPException: 
            - 404: If site not found, device not found, or register map not found
            - 400: If device doesn't belong to site
            - 500: For database errors
    """
    try:
        logger.info(f"Attempting to delete register map for device ID '{device_id}' in site '{site_id}'")
        
        # Get site and device information before deletion (for response)
        site = await get_site_by_id(site_id)
        if site is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "Site not found",
                    "message": f"Site with id '{site_id}' not found",
                    "site_id": site_id
                }
            )
        
        device = await get_device_by_id_internal(device_id)
        if device is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "Device not found",
                    "message": f"Device with id '{device_id}' not found",
                    "device_id": device_id
                }
            )
        
        # Validate device belongs to site
        if device.site_id != site_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Device does not belong to site",
                    "message": f"Device with id '{device_id}' does not belong to site '{site_id}'",
                    "site_id": site_id,
                    "device_id": device_id
                }
            )
        
        # Delete register map with site validation
        deleted = await delete_register_map(site_id, device_id)
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "Register map not found",
                    "message": f"Register map not found for device ID '{device_id}' in site '{site_id}'",
                    "site_id": site_id,
                    "site_name": site.name,
                    "device_id": device_id,
                    "device_name": device.name
                }
            )
        
        logger.info(f"Successfully deleted register map for device '{device.name}' (ID: {device_id}) in site '{site.name}' (ID: {site_id})")
        return {
            "message": f"Register map deleted successfully for device '{device.name}' (ID: {device_id})",
            "site_id": site_id,
            "site_name": site.name,
            "device_id": device_id,
            "device_name": device.name
        }
        
    except ValueError as e:
        error_msg = str(e)
        logger.warning(f"ValueError when deleting register map for device {device_id} in site {site_id}: {error_msg}")
        
        if "site" in error_msg.lower() and "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "Site not found",
                    "message": error_msg,
                    "site_id": site_id
                }
            )
        elif "device" in error_msg.lower() and "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "Device not found",
                    "message": error_msg,
                    "device_id": device_id
                }
            )
        elif "does not belong" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Device does not belong to site",
                    "message": error_msg,
                    "site_id": site_id,
                    "device_id": device_id
                }
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Validation error",
                    "message": error_msg
                }
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting register map for device ID '{device_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Failed to delete register map",
                "error_type": type(e).__name__,
                "message": str(e)
            }
        )

