"""Device config management endpoints."""

from fastapi import APIRouter, HTTPException, status

from db.device_configs import (
    create_device_config_for_device,
    get_device_config,
    update_device_config,
    delete_device_config
)
from schemas.db_models.models import DeviceConfigData, DeviceConfigResponse
from logger import get_logger

router = APIRouter(prefix="/device-configs", tags=["device-configs"])
logger = get_logger(__name__)


@router.post("/site/{site_id}/device/{device_id}", response_model=DeviceConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_new_device_config(site_id: int, device_id: int, config: DeviceConfigData):
    """Create a new device config."""
    try:
        return await create_device_config_for_device(site_id, device_id, config)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating device config: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create device config"
        )


@router.get("/{config_id}", response_model=DeviceConfigResponse)
async def get_device_config_endpoint(config_id: str):
    """Get a device config by ID."""
    try:
        config = await get_device_config(config_id)
        if config is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Device config with id '{config_id}' not found"
            )
        return config
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting device config '{config_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve device config"
        )


@router.put("/{config_id}", response_model=DeviceConfigResponse)
async def update_device_config_endpoint(config_id: str, update: DeviceConfigData):
    """Update a device config by ID."""
    try:
        config = await update_device_config(config_id, update)
        if config is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Device config with id '{config_id}' not found"
            )
        return config
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating device config '{config_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update device config"
        )


@router.delete("/{config_id}", status_code=status.HTTP_200_OK)
async def delete_device_config_endpoint(config_id: str):
    """Delete a device config by ID."""
    try:
        deleted = await delete_device_config(config_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Device config with id '{config_id}' not found"
            )
        return {"message": f"Device config '{config_id}' deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting device config '{config_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete device config"
        )

