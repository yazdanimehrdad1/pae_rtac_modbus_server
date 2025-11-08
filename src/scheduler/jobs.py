"""Polling jobs for Modbus data collection."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any

from modbus.client import ModbusClient, translate_modbus_error
from modbus.modbus_utills import ModbusUtils
from cache.cache import CacheService
from config import settings
from logger import get_logger
from utils.dataframe import load_register_map_from_csv
from utils.modbus_mapper import map_modbus_data_to_registers

logger = get_logger(__name__)

# Initialize services
modbus_client = ModbusClient()
cache_service = CacheService()
modbus_utils = ModbusUtils(modbus_client)


async def cron_job_poll_modbus_registers() -> None:
    """
    Scheduled job to poll Modbus registers and store data in Redis cache.
    
    This job:
    1. Loads register map from CSV configuration
    2. Makes a single modbus client call to poll points from a fixed index, and fixed range
    3. Uses map_modbus_data_to_registers() to map register points to their values
    4. Stores data in Redis cache with timestamp
    5. Handles errors gracefully
    """
    logger.info("Starting Modbus polling job")
    
    try:
        # 1. Load register map from CSV configuration
        register_map_path = Path(settings.poll_register_map_path)
        if not register_map_path.exists():
            logger.error(f"Register map file not found: {register_map_path}")
            return
        
        register_map = load_register_map_from_csv(register_map_path)
        logger.info(f"Loaded {len(register_map.points)} register points from {register_map_path}")
        
        if not register_map.points:
            logger.warning("No register points to poll")
            return
        
        # 2. Make a single modbus client call to poll points from a fixed index, and fixed range
        logger.debug(
            f"Reading Modbus registers: kind={settings.poll_kind}, "
            f"address={settings.poll_address}, count={settings.poll_count}, "
            f"unit_id={settings.poll_unit_id}"
        )
        
        modbus_data = modbus_utils.read_device_registers_main_sel_751()
        
        logger.info(f"Successfully read {len(modbus_data)} registers from Modbus")
        
        # 3. Use map_modbus_data_to_registers() to map register points to their values
        mapped_registers = map_modbus_data_to_registers(
            register_map=register_map,
            modbus_read_data=modbus_data,
            poll_start_address=settings.main_sel_751_poll_address
        )
        
        if not mapped_registers:
            logger.warning("No register points mapped from Modbus data, skipping storage")
            return
        
        # 4. Store data in Redis cache with timestamp
        timestamp = datetime.now(timezone.utc).isoformat()
        successful_reads = 0
        failed_reads = 0
        
        for register_data in mapped_registers:
            try:
                # Prepare data structure for cache using the mapped register data
                cache_data: Dict[str, Any] = {
                    "name": register_data.name,
                    "address": register_data.address,
                    "kind": register_data.kind,
                    "size": register_data.size,
                    "unit_id": register_data.unit_id,
                    "timestamp": timestamp,
                    "value": register_data.value,
                }
                
                # Add optional metadata
                if register_data.data_type:
                    cache_data["data_type"] = register_data.data_type
                if register_data.scale_factor:
                    cache_data["scale_factor"] = register_data.scale_factor
                if register_data.unit:
                    cache_data["unit"] = register_data.unit
                if register_data.tags:
                    cache_data["tags"] = register_data.tags
                
                # Store in cache with key: poll:{point_name}:{timestamp}
                # Also store latest with key: poll:{point_name}:latest
                cache_key_latest = f"poll:{register_data.name}:latest"
                cache_key_timestamped = f"poll:{register_data.name}:{timestamp}"
                
                # Store latest value (overwrites previous latest)
                await cache_service.set(
                    key=cache_key_latest,
                    value=cache_data,
                    ttl=settings.poll_cache_ttl
                )
                
                # Store timestamped value (for historical tracking)
                await cache_service.set(
                    key=cache_key_timestamped,
                    value=cache_data,
                    ttl=settings.poll_cache_ttl
                )
                
                successful_reads += 1
                logger.debug(
                    f"Polled register point: {register_data.name} "
                    f"(address={register_data.address}, value={register_data.value})"
                )
                
            except Exception as e:
                failed_reads += 1
                logger.warning(
                    f"Failed to process point '{register_data.name}' (address={register_data.address}): {e}"
                )
                # Continue with next point
        
        logger.info(
            f"Modbus polling job completed: {successful_reads} successful, {failed_reads} failed "
            f"(total: {len(mapped_registers)} mapped registers)"
        )
        
    except Exception as e:
        status_code, error_message = translate_modbus_error(e)
        logger.error(
            f"Error in Modbus polling job: status_code={status_code}, error_message={error_message}",
            exc_info=True
        )
        # Don't re-raise - let scheduler handle retry on next interval
