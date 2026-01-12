"""Polling jobs for Modbus data collection."""

import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, TypedDict

from modbus.client import ModbusClient, translate_modbus_error
from modbus.modbus_utills import ModbusUtils
from cache.cache import CacheService
from config import settings
from logger import get_logger
from utils.map_csv_to_json import json_to_register_map, get_register_map_for_device
from utils.modbus_mapper import map_modbus_data_to_registers, MappedRegisterData
from db.devices import get_all_devices
from db.register_readings import insert_register_readings_batch
from schemas.db_models.models import DeviceListItem

logger = get_logger(__name__)

# Initialize services
modbus_client = ModbusClient()
cache_service = CacheService()
modbus_utils = ModbusUtils(modbus_client)


class PollResult(TypedDict, total=False):
    """Result of polling a single device."""
    device_name: str
    success: bool
    cache_successful: int
    cache_failed: int
    db_successful: int
    db_failed: int
    error: Optional[str]

# TODO: maybe consider getting it from the cache instead of the database
async def get_devices_to_poll() -> List[DeviceListItem]:
    """
    Get list of devices to poll from database, filtered by poll_enabled.
    
    Returns:
        List of devices that have polling enabled
    """
    all_devices = await get_all_devices()
    
    logger.info(f"Retrieved {len(all_devices)} device(s) from database")
    
    # Filter devices by poll_enabled from database
    devices_to_poll = []
    for device in all_devices:
        # Check poll_enabled directly from device
        if device.poll_enabled:
            devices_to_poll.append(device)
            logger.debug(f"Device '{device.name}' (ID: {device.id}) has polling enabled")
        else:
            # Polling disabled
            logger.debug(f"Device '{device.name}' (ID: {device.id}) has polling disabled (poll_enabled={device.poll_enabled}), skipping")
    
    logger.info(f"Found {len(devices_to_poll)} device(s) to poll out of {len(all_devices)} total device(s)")
    return devices_to_poll


async def read_device_registers(
    device: DeviceListItem,
    polling_config: Dict[str, Any]
) -> List[Any]:
    """
    Read Modbus registers for a device using polling configuration.
    
    Args:
        device: Device to read from
        polling_config: Polling configuration (address, count, kind, device_id)
        
    Returns:
        List of raw register values from Modbus
        
    Raises:
        Exception: If Modbus read fails
    """
    address = polling_config["poll_address"]
    count = polling_config["poll_count"]
    kind = polling_config["poll_kind"]
    device_id = device.device_id  # Use device's Modbus device_id
    
    logger.debug(
        f"Reading Modbus registers for device '{device.name}': "
        f"kind={kind}, address={address}, count={count}, device_id={device_id}"
    )
    
    # Use appropriate ModbusUtils method based on register kind
    # Pass device-specific host and port for connection
    if kind == "holding":
        modbus_data = modbus_utils.read_holding_registers(address, count, device_id, host=device.host, port=device.port)
    elif kind == "input":
        modbus_data = modbus_utils.read_input_registers(address, count, device_id, host=device.host, port=device.port)
    elif kind == "coils":
        modbus_data = modbus_utils.read_coils(address, count, device_id, host=device.host, port=device.port)
    elif kind == "discretes":
        modbus_data = modbus_utils.read_discrete_inputs(address, count, device_id, host=device.host, port=device.port)
    else:
        raise ValueError(f"Invalid register kind: {kind}. Must be 'holding', 'input', 'coils', or 'discretes'")
    
    logger.info(f"Successfully read {len(modbus_data)} registers from device '{device.name}'")
    return modbus_data


async def store_device_data_in_cache(
    device_name: str,
    mapped_registers: List[MappedRegisterData],
    polling_config: Dict[str, Any],
    timestamp: str
) -> tuple[int, int]:
    """
    Store mapped register data in Redis cache.
    
    Args:
        device_name: Device name for cache key
        mapped_registers: List of mapped register data
        polling_config: Polling configuration
        timestamp: ISO format timestamp string
        
    Returns:
        Tuple of (successful_reads, failed_reads)
    """
    try:
        # Build register data dictionary
        register_data_dict: Dict[int, Dict[str, Any]] = {}
        
        for register_data in mapped_registers:
            register_entry: Dict[str, Any] = {
                "name": register_data.name,
                "value": register_data.value,
                "address": register_data.address,
                "kind": register_data.kind,
                "size": register_data.size,
                "device_id": register_data.device_id,
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
    mapped_registers: List[MappedRegisterData],
    timestamp_dt: datetime
) -> tuple[int, int]:
    """
    Store mapped register data in database.
    
    Args:
        device_id: Database device ID (primary key)
        mapped_registers: List of mapped register data
        timestamp_dt: Datetime object for database storage
        
    Returns:
        Tuple of (successful_inserts, failed_inserts)
    """
    try:
        batch_readings = []
        for register_data in mapped_registers:
            batch_readings.append({
                'device_id': device_id,
                'register_address': register_data.address,
                'value': register_data.value,
                'timestamp': timestamp_dt,
                'quality': 'good',
                'register_name': register_data.name,
                'unit': register_data.unit or None,
                'scale_factor': register_data.scale_factor or None
            })
        
        inserted_count = await insert_register_readings_batch(batch_readings)
        logger.info(f"Successfully stored {inserted_count} register readings in database")
        return inserted_count, 0
        
    except Exception as e:
        logger.error(f"Failed to store register readings in database: {e}", exc_info=True)
        return 0, len(mapped_registers)


async def poll_single_device(device: DeviceListItem) -> PollResult:
    """
    Poll a single device: load register map, read registers, map data, and store in cache/DB.
    
    Args:
        device: Device to poll
        
    Returns:
        PollResult with success status and statistics
    """
    device_name = device.name
    result: PollResult = {
        "device_name": device_name,
        "success": False,
        "cache_successful": 0,
        "cache_failed": 0,
        "db_successful": 0,
        "db_failed": 0,
        "error": None
    }
    
    try:
        # 1. Get polling configuration from device (already loaded in DeviceListItem)
        if not device.poll_enabled:
            result["error"] = f"Polling disabled for device '{device_name}'"
            logger.debug(result["error"])
            return result
        
        # Convert polling config to dict for compatibility
        polling_config = {
            "poll_address": device.poll_address,
            "poll_count": device.poll_count,
            "poll_kind": device.poll_kind,
            "poll_enabled": device.poll_enabled
        }
        
        # TODO: maybe consider getting it from the cache instead of the database
        # 2. Load register map from database by device ID (will auto-get site_id from device)
        json_data = await get_register_map_for_device(device.id, site_id=device.site_id if device.site_id else None)
        if json_data is None:
            result["error"] = f"Register map not found for device '{device_name}' (ID: {device.id}) in database"
            logger.error(result["error"])
            return result
        
        register_map = json_to_register_map(json_data)
        logger.info(f"Loaded {len(register_map.points)} register points for device '{device_name}'")
        
        if not register_map.points:
            result["error"] = f"No register points to poll for device '{device_name}'"
            logger.warning(result["error"])
            return result
        
        # 3. Read Modbus registers
        modbus_data = await read_device_registers(device, polling_config)
        
        # 4. Map register data
        mapped_registers = map_modbus_data_to_registers(
            register_map=register_map,
            modbus_read_data=modbus_data,
            poll_start_address=polling_config["poll_address"]
        )
        
        if not mapped_registers:
            result["error"] = f"No register points mapped from Modbus data for device '{device_name}'"
            logger.warning(result["error"])
            return result
        
        # 5. Get device_id (primary key) from device object
        device_id = device.id
        
        # 6. Store data in cache and database
        timestamp = datetime.now(timezone.utc).isoformat()
        timestamp_dt = datetime.now(timezone.utc)
        
        # TODO: maybe consider getting it from the cache instead of the database
        # Add device_id (Modbus unit/slave ID) to polling_config for cache
        polling_config["device_id"] = device.device_id  # Modbus device_id
        
        cache_successful, cache_failed = await store_device_data_in_cache(
            device_name, mapped_registers, polling_config, timestamp
        )
        
        db_successful = 0
        db_failed = 0
        if device_id is not None:
            db_successful, db_failed = await store_device_data_in_db(
                device_id, mapped_registers, timestamp_dt
            )
        else:
            logger.debug(f"Device '{device_name}' not found in database, skipping DB storage")
        
        result["success"] = True
        result["cache_successful"] = cache_successful
        result["cache_failed"] = cache_failed
        result["db_successful"] = db_successful
        result["db_failed"] = db_failed
        
        logger.info(
            f"Device '{device_name}' polling completed: "
            f"Cache: {cache_successful} successful, {cache_failed} failed | "
            f"Database: {db_successful} successful, {db_failed} failed"
        )
        
    except Exception as e:
        # Pass device host/port for better error messages
        status_code, error_message = translate_modbus_error(e, host=device.host, port=device.port)
        result["error"] = f"status_code={status_code}, error_message={error_message}"
        logger.error(
            f"Error polling device '{device_name}': {result['error']}",
            exc_info=True
        )
    
    return result


async def cron_job_poll_modbus_registers() -> None:
    """
    Scheduled job to poll Modbus registers for all enabled devices.
    
    This job:
    1. Gets list of devices to poll (from database, filtered by poll_enabled)
    2. For each device:
       - Loads register map (DB first, then CSV fallback)
       - Reads Modbus registers using device-specific polling config
       - Maps register data to register points
       - Stores data in Redis cache and database
    3. Handles errors per device (isolated - one device failure doesn't stop others)
    4. Logs summary statistics
    """
    logger.info("Starting Modbus polling job")
    
    try:
        # 1. Get devices to poll
        devices_to_poll = await get_devices_to_poll()
        
        if not devices_to_poll:
            logger.warning("No devices to poll (all devices disabled or not found in config)")
            return
        
        # 2. Poll each device in parallel (errors are isolated per device)
        # Use asyncio.gather to run all device polling operations concurrently
        # Note: ModbusClient is safe for concurrent use because:
        # - It only stores read-only configuration
        # - Each read_registers() call creates a new ModbusTcpClient connection via context manager
        # - No shared mutable state between concurrent calls
        results: List[PollResult] = await asyncio.gather(
            *[poll_single_device(device) for device in devices_to_poll],
            return_exceptions=True
        )
        
        # Convert any exceptions to error results
        processed_results: List[PollResult] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                device_name = devices_to_poll[i].name if i < len(devices_to_poll) else "unknown"
                logger.error(f"Unexpected error polling device '{device_name}': {result}", exc_info=True)
                processed_results.append({
                    "device_name": device_name,
                    "success": False,
                    "cache_successful": 0,
                    "cache_failed": 0,
                    "db_successful": 0,
                    "db_failed": 0,
                    "error": str(result)
                })
            else:
                processed_results.append(result)
        
        results = processed_results
        
        # 3. Log summary
        successful_devices = sum(1 for r in results if r.get("success", False))
        failed_devices = len(results) - successful_devices
        total_cache_successful = sum(r.get("cache_successful", 0) for r in results)
        total_cache_failed = sum(r.get("cache_failed", 0) for r in results)
        total_db_successful = sum(r.get("db_successful", 0) for r in results)
        total_db_failed = sum(r.get("db_failed", 0) for r in results)
        
        logger.info(
            f"Modbus polling job completed: "
            f"{successful_devices} device(s) successful, {failed_devices} device(s) failed | "
            f"Cache: {total_cache_successful} successful, {total_cache_failed} failed | "
            f"Database: {total_db_successful} successful, {total_db_failed} failed"
        )
        
        # Log individual device failures
        for result in results:
            if not result.get("success", False):
                logger.warning(
                    f"Device '{result.get('device_name', 'unknown')}' polling failed: "
                    f"{result.get('error', 'Unknown error')}"
                )
        
    except Exception as e:
        logger.error(
            f"Error in Modbus polling job: {e}",
            exc_info=True
        )
        # Don't re-raise - let scheduler handle retry on next interval
