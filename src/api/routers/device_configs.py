"""Device config management endpoints."""

from fastapi import APIRouter, HTTPException, status

from db.device_configs import (
    get_config,
    update_config,
    delete_config,
)
from helpers.device_configs import create_config_cache_db
from schemas.db_models.models import (
    ConfigCreateRequest,
    ConfigResponse,
    ConfigDeleteResponse,
    ConfigUpdate,
)
from utils.exceptions import AppError
from logger import get_logger

router = APIRouter(prefix="/configs", tags=["configs"])
logger = get_logger(__name__)


@router.post("/site/{site_id}/device/{device_id}", response_model=ConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_new_config(site_id: int, device_id: int, config: ConfigCreateRequest):
    """Create a new config."""
    try:
        return await create_config_cache_db(site_id, device_id, config)
    except AppError as e:
        detail = {"error": type(e).__name__, "message": e.message}
        if e.payload:
            detail.update(e.payload)
        raise HTTPException(status_code=e.http_status_code, detail=detail)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred"
        )


@router.get("/{config_id}", response_model=ConfigResponse)
async def get_config_endpoint(config_id: str):
    try:
        config = await get_config(config_id)
    except AppError as e:
        detail = {"error": type(e).__name__, "message": e.message}
        if e.payload:
            detail.update(e.payload)
        raise HTTPException(status_code=e.http_status_code, detail=detail)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred"
        )

    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Config with id '{config_id}' not found"
        )
    return config


@router.put("/{config_id}", response_model=ConfigResponse)
async def update_config_endpoint(config_id: str, update: ConfigUpdate):
    try:
        config = await update_config(config_id, update)
    except AppError as e:
        detail = {"error": type(e).__name__, "message": e.message}
        if e.payload:
            detail.update(e.payload)
        raise HTTPException(status_code=e.http_status_code, detail=detail)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred"
        )

    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Config with id '{config_id}' not found"
        )
    return config


@router.delete("/{config_id}", response_model=ConfigDeleteResponse, status_code=status.HTTP_200_OK)
async def delete_config_endpoint(config_id: str):
    try:
        deleted = await delete_config(config_id)
    except AppError as e:
        detail = {"error": type(e).__name__, "message": e.message}
        if e.payload:
            detail.update(e.payload)
        raise HTTPException(status_code=e.http_status_code, detail=detail)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred"
        )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Config with id '{config_id}' not found"
        )
    return {"config_id": config_id}
