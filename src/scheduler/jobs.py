"""Polling jobs for Modbus data collection."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any

from modbus.client import ModbusClient, translate_modbus_error
from modbus.modbus_utills import ModbusUtils
from cache.cache import CacheService
from config import settings
from logger import get_logger
from utils.map_csv_to_json import map_csv_to_json, json_to_register_map
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
        
        json_data = map_csv_to_json(register_map_path)
        register_map = json_to_register_map(json_data)
        logger.info(f"Loaded {len(register_map.points)} register points from {register_map_path}")
        
        if not register_map.points:
            logger.warning("No register points to poll")
            return
        
        # 2. Make a single modbus client call to poll points from a fixed index, and fixed range
        logger.debug(
            f"Reading Modbus registers: kind={settings.main_sel_751_poll_kind}, "
            f"address={settings.main_sel_751_poll_address}, count={settings.main_sel_751_poll_count}, "
            f"unit_id={settings.main_sel_751_poll_unit_id}"
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
        
        logger.info("Storing data in Redis cache")
        logger.info(f"Register map: {len(register_map.points)} points")
        
        try:
            # Build a single large object containing all mapped registers, similar to ReadResponse
            # Store all data from mapped_registers in a structure similar to /read/main-sel-751
            register_data_dict: Dict[int, Dict[str, Any]] = {}
            
            for register_data in mapped_registers:
                # Create RegisterData-like structure with all fields from MappedRegisterData
                register_entry: Dict[str, Any] = {
                    "name": register_data.name,
                    "value": register_data.value,
                    "address": register_data.address,
                    "kind": register_data.kind,
                    "size": register_data.size,
                    "unit_id": register_data.unit_id,
                }
                
                # Add optional metadata
                if register_data.data_type:
                    register_entry["Type"] = register_data.data_type
                if register_data.scale_factor:
                    register_entry["scale_factor"] = register_data.scale_factor
                if register_data.unit:
                    register_entry["unit"] = register_data.unit
                if register_data.tags:
                    register_entry["tags"] = register_data.tags
                
                # Use address as key (similar to ReadResponse.data structure)
                register_data_dict[register_data.address] = register_entry
            
            # Create cache object similar to ReadResponse structure
            cache_data: Dict[str, Any] = {
                "ok": True,
                "timestamp": timestamp,
                "kind": settings.main_sel_751_poll_kind,
                "address": settings.main_sel_751_poll_address,
                "count": settings.main_sel_751_poll_count,
                "unit_id": settings.main_sel_751_poll_unit_id,
                "data": register_data_dict
            }
            
            # Store in cache with keys: poll:main-sel-751:latest and poll:main-sel-751:{timestamp}
            cache_key_latest = "poll:main-sel-751:latest"
            cache_key_timestamped = f"poll:main-sel-751:{timestamp}"
        
            # TODO: Optimize caching strategy using Redis Sorted Sets (Option B)
            # Current approach stores full objects in timestamped keys, which is inefficient for:
            # - Memory usage (redundant metadata in each entry)
            # - Querying past hour (requires fetching 60+ keys per device)
            # 
            # Proposed optimization:
            # 1. Keep current structure for latest: poll:{device}:latest (full object)
            # 2. Use Redis Sorted Set for history: poll:{device}:history (ZSET)
            #    - Score: timestamp (Unix epoch)
            #    - Value: JSON string with only {address: value} pairs (no metadata)
            # 3. Store metadata separately: register_map:{device} (static, no TTL)
            # 4. Query past hour: ZRANGEBYSCORE poll:{device}:history <1-hour-ago> +inf WITHSCORES
            # 5. Cleanup old data: ZREMRANGEBYSCORE poll:{device}:history -inf <1-hour-ago>
            # 
            # Benefits:
            # - 90% memory reduction (only values, not metadata)
            # - Single Redis call per device for past hour queries
            # - Efficient time-range queries
            # - Better scalability for 10+ devices
            
            logger.info(f"Cache key latest: {cache_key_latest}")
            logger.info(f"Cache key timestamped: {cache_key_timestamped}")
            logger.info(f"Storing {len(register_data_dict)} registers in cache")
            logger.info(f"Cache TTL: {settings.poll_cache_ttl}")  
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
            
            successful_reads = len(register_data_dict)
            failed_reads = 0
            
            logger.info(f"Successfully stored {successful_reads} registers in cache")
            
        except Exception as e:
            logger.error(f"Failed to store data in cache: {e}", exc_info=True)
            successful_reads = 0
            failed_reads = len(mapped_registers)
        
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
