"""Device helper functions for API routes."""

from fastapi import HTTPException, status

from db.devices import get_device_by_id
from cache.cache import CacheService
from logger import get_logger
from schemas.db_models.models import DeviceResponse

logger = get_logger(__name__)

# Initialize cache service
cache_service = CacheService()

#TODO: lets try cache first and if not successful then db
async def get_device_with_cache(device_id: int) -> DeviceResponse:
    """
    Get device by ID with cache-first lookup.
    
    Args:
        device_id: Device ID (database primary key)
        
    Returns:
        DeviceResponse if found
        
    Raises:
        HTTPException: If device not found
    """
    # First try cache
    cache_key = f"device:id:{device_id}"
    cached_device = await cache_service.get(cache_key)
    
    if cached_device is not None:
        logger.debug(f"Device ID {device_id} found in cache")
        return DeviceResponse(**cached_device)
    else:
        logger.debug(f"Device ID {device_id} not in cache, querying database")
        try:
            device = await get_device_by_id(device_id)
            if device is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Device with ID {device_id} not found"
                )
            return device
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )

