"""Register map endpoints."""

from typing import Dict, Any

from fastapi import APIRouter, HTTPException, status

from db.device_register_map import get_register_map_by_device_name, get_register_map_by_device_id
from logger import get_logger

router = APIRouter(prefix="/register_map", tags=["register_map"])
logger = get_logger(__name__)


@router.get("/device/{device_name}", response_model=Dict[str, Any])
async def get_register_map(device_name: str):
    """
    Get register map for a device by device name.
    
    Args:
        device_name: Device name/identifier (e.g., "sel_751")
        
    Returns:
        JSON structure with metadata and registers array
        
    Raises:
        HTTPException: If device name not found or register map doesn't exist
    """
    try:
        register_map = await get_register_map_by_device_name(device_name)
        
        if register_map is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Register map not found for device '{device_name}'"
            )
        
        logger.info(f"Retrieved register map for device '{device_name}' from database")
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


@router.get("/device/id/{device_id}", response_model=Dict[str, Any])
async def get_register_map_by_id(device_id: int):
    """
    Get register map for a device by device ID.
    
    Args:
        device_id: Device ID
        
    Returns:
        JSON structure with metadata and registers array
        
    Raises:
        HTTPException: If device ID not found or register map doesn't exist
    """
    try:
        register_map = await get_register_map_by_device_id(device_id)
        
        if register_map is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Register map not found for device ID {device_id}"
            )
        
        logger.info(f"Retrieved register map for device ID {device_id} from database")
        return register_map
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error getting register map for device ID {device_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve register map"
        )

