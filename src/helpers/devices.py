"""Device helper functions for DB/cache coordination."""

from fastapi import HTTPException, status

from cache.cache import CacheService
from db.devices import create_device, delete_device, get_all_devices, get_device_by_id, update_device
from utils.exceptions import NotFoundError, InternalError
from logger import get_logger
from schemas.api_models import DeviceCreateRequest, DeviceUpdate, DeviceWithConfigs

logger = get_logger(__name__)
cache_service = CacheService()


async def get_devices_cache_db(site_id: int) -> list[DeviceWithConfigs]:
    """
    Get all devices for a site with cache-first lookup.
    
    Args:
        site_id: Site ID (4-digit number)
    
    Returns:
        List of devices for the site
    """
    cache_key = f"device:site:{site_id}:devices"
    cached_devices = await cache_service.get(cache_key)
    
    if cached_devices is not None:
        logger.debug(f"Devices for site {site_id} found in cache")
        return [DeviceWithConfigs(**item) for item in cached_devices]
    
    logger.debug(f"Devices for site {site_id} not in cache, querying database")
    devices = await get_all_devices(site_id)
    if not devices:
        return []
    
    cached = await cache_service.set(
        key=cache_key,
        value=[device.model_dump(mode="json") for device in devices]
    )
    if not cached:
        logger.error(f"Failed to cache devices list for site {site_id}")
    return devices


async def get_device_cache_db(site_id: int, device_id: int) -> DeviceWithConfigs:
    """
    Get device by ID with cache-first lookup.
    
    Args:
        site_id: Site ID (4-digit number)
        device_id: Device ID (database primary key)
        
    Returns:
        DeviceWithConfigs if found
        
    Raises:
        HTTPException: If device not found
    """
    cache_key = f"device:site:{site_id}:device_id:{device_id}"
    cached_device = await cache_service.get(cache_key)
    
    if cached_device is not None:
        logger.debug(f"Device ID {device_id} found in cache")
        cached_response = DeviceWithConfigs(**cached_device)
        if cached_response.configs:
            return cached_response
    
    logger.debug(f"Device ID {device_id} not in cache, querying database")
    device = await get_device_by_id(device_id, site_id)
    if device is None:
        raise NotFoundError(f"Device with ID {device_id} not found in site {site_id}")
    
    cached = await cache_service.set(
        key=cache_key,
        value=device.model_dump(mode="json")
    )
    if not cached:
        logger.error(
            f"Failed to cache device {device_id} for site {site_id} after DB read"
        )
    return device


async def create_device_cache_db(device: DeviceCreateRequest, site_id: int) -> DeviceWithConfigs:
    """
    Create a new device in the database and cache.
    
    Args:
        device: Device creation data
        site_id: Site ID (4-digit number)
    
    Returns:
        Created device with ID and timestamps
    
    Raises:
        RuntimeError: If caching fails after DB creation
    """
    created_device = await create_device(device, site_id=site_id)
    cache_key = f"device:site:{site_id}:device_id:{created_device.device_id}"
    cached = await cache_service.set(
        key=cache_key,
        value=created_device.model_dump(mode="json")
    )
    if not cached:
        logger.error(
            f"Failed to cache created device {created_device.device_id} for site {site_id}"
        )
        raise InternalError("Failed to cache created device")
    return created_device


async def update_device_cache_db(
    device_id: int,
    device_update: DeviceUpdate,
    site_id: int
) -> DeviceWithConfigs:
    """
    Update a device in the database and cache.
    
    Args:
        device_id: Device ID (database primary key)
        device_update: Device update data
        site_id: Site ID (4-digit number)
    
    Returns:
        Updated device with ID and timestamps
    
    Raises:
        RuntimeError: If caching fails after DB update
    """
    updated_device = await update_device(device_id, device_update, site_id=site_id)
    cache_key = f"device:site:{site_id}:device_id:{updated_device.device_id}"
    cached = await cache_service.set(
        key=cache_key,
        value=updated_device.model_dump(mode="json")
    )
    if not cached:
        logger.error(
            f"Failed to cache updated device {updated_device.device_id} for site {site_id}"
        )
        raise InternalError("Failed to cache updated device")
    return updated_device


async def delete_device_cache_db(
    device_id: int,
    site_id: int
) -> DeviceWithConfigs | None:
    """
    Delete a device from the database and cache.
    
    Args:
        device_id: Device ID (database primary key)
        site_id: Site ID (4-digit number)
    
    Returns:
        Deleted device metadata, or None if not found
    
    Raises:
        RuntimeError: If cache delete fails for existing key
    """
    deleted_device = await delete_device(device_id, site_id=site_id)
    if deleted_device is None:
        return None
    cache_key = f"device:site:{site_id}:device_id:{deleted_device.device_id}"
    cache_deleted = await cache_service.delete(cache_key)
    if not cache_deleted:
        cache_exists = await cache_service.exists(cache_key)
        if cache_exists:
            logger.error(
                f"Failed to delete cached device {deleted_device.device_id} for site {site_id}"
            )
            raise InternalError("Failed to delete cached device")
    return deleted_device
