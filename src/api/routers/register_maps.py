"""Register map management endpoints."""

from typing import Dict, Any
from fastapi import APIRouter, HTTPException, status
from pydantic import ValidationError

from schemas.db_models.models import RegisterMapCreate
from utils.map_csv_to_json import get_register_map_for_device
from db.device_register_map import create_register_map
from helpers.register_maps import validate_register_map_format, get_expected_format
from logger import get_logger

router = APIRouter(prefix="/register_maps", tags=["register_maps"])
logger = get_logger(__name__)


@router.get("/device/{device_id}", response_model=Dict[str, Any])
async def get_device_register_map(device_id: int):
    """
    Get register map for a device in JSON format by device ID.
    
    Retrieves the register map from the database for the specified device.
    
    Args:
        device_id: Device ID (primary key)
        
    Returns:
        JSON structure with metadata and registers array
        
    Raises:
        HTTPException: If device ID not found or register map cannot be loaded
    """

    try:
        # Get register map by device ID
        register_map = await get_register_map_for_device(device_id)
        
        if register_map is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Register map not found for device ID '{device_id}'"
            )
        
        return register_map
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error getting register map for device ID '{device_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve register map"
        )


@router.post("/device/{device_id}", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_device_register_map(device_id: int, register_map: RegisterMapCreate):
    """
    Create a register map for a device.
    
    Creates a new register map in the database for the specified device.
    The register map must include a 'registers' array with at least one register definition.
    
    Args:
        device_id: Device ID (primary key)
        register_map: Register map data with metadata and registers array
        
    Returns:
        Created register map as stored in the database
        
    Raises:
        HTTPException: If device ID not found, register map already exists, or validation fails
    """
    try:
        # Validate register map format using helper function (includes all field and range validations)
        validate_register_map_format(register_map)
        
        # Convert Pydantic model to dict
        register_map_dict = register_map.to_dict()
        
        # Create register map in database
        await create_register_map(device_id, register_map_dict)
        
        # Retrieve and return the created register map
        created_map = await get_register_map_for_device(device_id)
        
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
        # Handle device not found or duplicate register map
        error_msg = str(e)
        if "not found" in error_msg.lower() or "does not exist" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
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


    # 2. Read register map endpoint (GET /device/{device_id}) - implemented above
    # 3. Update register map endpoint (PUT /device/{device_id})
    # 4. Delete register map endpoint (DELETE /device/{device_id})

