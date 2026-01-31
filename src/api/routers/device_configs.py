"""Device config management endpoints."""

from fastapi import APIRouter, HTTPException, status

from db.device_configs import (
    get_config,
    update_config,
    delete_config,
)
from helpers.device_configs import create_config_cache_db
from schemas.db_models.models import (
    ConfigCreate,
    ConfigResponse,
    ConfigDeleteResponse,
    ConfigUpdate,
)
from logger import get_logger

router = APIRouter(prefix="/configs", tags=["configs"])
logger = get_logger(__name__)


@router.post("/site/{site_id}/device/{device_id}", response_model=ConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_new_config(site_id: int, device_id: int, config: ConfigCreate):
    """Create a new config."""
    try:
        return await create_config_cache_db(site_id, device_id, config)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating config: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create config"
        )


@router.get("/{config_id}", response_model=ConfigResponse)
async def get_config_endpoint(config_id: str):
    """Get a config by ID."""
    try:
        config = await get_config(config_id)
        if config is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Config with id '{config_id}' not found"
            )
        return config
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting config '{config_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve config"
        )


@router.put("/{config_id}", response_model=ConfigResponse)
async def update_config_endpoint(config_id: str, update: ConfigUpdate):
    """Update a config by ID."""
    try:
        config = await update_config(config_id, update)
        if config is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Config with id '{config_id}' not found"
            )
        return config
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating config '{config_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update config"
        )


@router.delete("/{config_id}", response_model=ConfigDeleteResponse, status_code=status.HTTP_200_OK)
async def delete_config_endpoint(config_id: str):
    """Delete a config by ID."""
    try:
        deleted = await delete_config(config_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Config with id '{config_id}' not found"
            )
        return {"config_id": config_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting config '{config_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete config"
        )

