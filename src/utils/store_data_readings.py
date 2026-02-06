"""Helpers for storing device polling data."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from cache.cache import CacheService
from config import settings
from db.register_readings import insert_register_readings_batch
from logger import get_logger
from utils.modbus_mapper import MappedRegisterData
from schemas.db_models.orm_models import DevicePointsReading

logger = get_logger(__name__)
cache_service = CacheService()


async def store_device_data_in_cache(
    device_name: str,
    mapped_registers: List[MappedRegisterData],
    polling_config: Dict[str, Any],
    timestamp: str,
    site_name: Optional[str] = None
) -> tuple[int, int]:
    """
    Store mapped register data in Redis cache.

    Args:
        device_name: Device name for cache key
        mapped_registers: List of mapped register data
        polling_config: Polling configuration
        timestamp: ISO format timestamp string
        site_name: Optional site name to include in cache key

    Returns:
        Tuple of (successful_reads, failed_reads)
    """
    try:
        # Build register data dictionary
        register_data_dict: Dict[int, Dict[str, Any]] = {}

        # Get kind and device_id from polling_config
        kind = polling_config.get("poll_kind", "holding")
        device_id = polling_config.get("device_id", 1)

        for register_data in mapped_registers:
            register_entry: Dict[str, Any] = {
                "name": register_data.name,
                "value": register_data.value,
                "address": register_data.address,
                "size": register_data.size,
                "device_id": device_id,
            }

            # Add optional metadata
            if register_data.data_type:
                register_entry["Type"] = register_data.data_type
            if register_data.scale_factor:
                register_entry["scale_factor"] = register_data.scale_factor
            if register_data.unit:
                register_entry["unit"] = register_data.unit

            register_data_dict[register_data.address] = register_entry

        # Create cache object
        cache_data: Dict[str, Any] = {
            "ok": True,
            "timestamp": timestamp,
            "kind": polling_config["poll_kind"],
            "address": polling_config["poll_address"],
            "count": polling_config["poll_count"],
            "device_id": polling_config.get("device_id"),  # Will be set by caller if needed
            "data": register_data_dict
        }

        # Store in cache
        # Include site_name in cache key if provided, otherwise use device_name only
        if site_name:
            cache_key_latest = f"poll:{site_name}:{device_name}:latest"
            cache_key_timestamped = f"poll:{site_name}:{device_name}:{timestamp}"
        else:
            cache_key_latest = f"poll:{device_name}:latest"
            cache_key_timestamped = f"poll:{device_name}:{timestamp}"

        await cache_service.set(
            key=cache_key_latest,
            value=cache_data,
            ttl=settings.poll_cache_ttl
        )

        await cache_service.set(
            key=cache_key_timestamped,
            value=cache_data,
            ttl=settings.poll_cache_ttl
        )

        successful_reads = len(register_data_dict)
        logger.info(f"Successfully stored {successful_reads} registers in cache for device '{device_name}'")
        return successful_reads, 0

    except Exception as e:
        logger.error(f"Failed to store data in cache for device '{device_name}': {e}", exc_info=True)
        return 0, len(mapped_registers)


async def store_device_data_in_db(
    device_id: int,
    site_id: str,
    points_readings_list: List[DevicePointsReading],
    timestamp_dt: datetime
) -> tuple[int, int]:
    """
    Store mapped register data in database.

    Args:
        device_id: Database device ID (primary key)
        site_id: Site ID (UUID) to validate device belongs to site
        mapped_registers: List of mapped register data
        timestamp_dt: Datetime object for database storage

    Returns:
        Tuple of (successful_inserts, failed_inserts)
    """
    try:
        inserted_count = await insert_register_readings_batch(
            site_id=site_id,
            device_id=device_id,
            points_readings_list=points_readings_list,
            timestamp_dt=timestamp_dt
        )
        logger.info(f"Successfully stored {inserted_count} register readings in database")
        return inserted_count, 0

    except Exception as e:
        logger.error(f"Failed to store register readings in database: {e}", exc_info=True)
        return 0, len(points_readings_list)


async def store_device_data_in_db_translated(
    device_id: int,
    site_id: str,
    mapped_registers: List[MappedRegisterData],
    timestamp_dt: datetime
) -> tuple[int, int]:
    """
    Store mapped register data in database.
    """
    pass
