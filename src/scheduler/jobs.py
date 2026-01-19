"""Polling jobs for Modbus data collection."""

import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, TypedDict

from modbus.client import ModbusClient, translate_modbus_error
from modbus.modbus_utills import ModbusUtils
from cache.cache import CacheService
from config import settings
from logger import get_logger
from db.device_configs import get_device_config
from utils.modbus_mapper import map_modbus_data_to_registers, MappedRegisterData
from db.devices import get_devices_by_site_id
from db.register_readings import insert_register_readings_batch
from db.sites import get_site_by_id, get_all_sites
from schemas.db_models.models import DeviceListItem

logger = get_logger(__name__)

# Initialize services
edge_aggregator_modbus_client = ModbusClient()
edge_aggregator_cache_service = CacheService()
edge_aggregator_modbus_utils = ModbusUtils(edge_aggregator_modbus_client)


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
async def get_devices_to_poll(site_id: int) -> List[DeviceListItem]:
    """
    Get list of devices to poll from database, filtered by poll_enabled.
    
    This function only returns devices for a single site.
    
    Returns:
        List of devices that have polling enabled for a site
    """
    site_devices = await get_devices_by_site_id(site_id)
    logger.info(f"Retrieved {len(site_devices)} device(s) for site ID {site_id}")
    
    # Filter devices by poll_enabled from database
    devices_to_poll = []
    for device in site_devices:
        # Check poll_enabled directly from device
        if device.poll_enabled:
            devices_to_poll.append(device)
            logger.debug(f"Device '{device.name}' (ID: {device.id}) has polling enabled")
        else:
            # Polling disabled
            logger.debug(f"Device '{device.name}' (ID: {device.id}) has polling disabled (poll_enabled={device.poll_enabled}), skipping")
    
    logger.info(
        f"Found {len(devices_to_poll)} device(s) to poll out of {len(site_devices)} total device(s) "
        f"for site ID {site_id}"
    )
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
    server_id = device.modbus_server_id
    host = device.modbus_host
    port = device.modbus_port
    
    logger.debug(
        f"Reading Modbus registers for device '{device.name}': "
        f"kind={kind}, address={address}, count={count}, server_id={server_id}"
    )
    
    # Use appropriate ModbusUtils method based on register kind
    # Pass device-specific host and port for connection

    # TODO: lets find a way so we don't have to keep creating a 
    # modbus client and modbus utils object for devices that are not 
    # reading from the edge aggregator, and somehow storing it in a global variable
    if device.read_from_aggregator:
        modbus_client = edge_aggregator_modbus_client
        modbus_utils = edge_aggregator_modbus_utils
    else:
        modbus_client = ModbusClient(
            host=device.modbus_host,
            port=device.modbus_port,
            server_id=device.modbus_server_id,
            timeout=device.modbus_timeout
        )
        modbus_utils = ModbusUtils(modbus_client)

    if kind not in {"holding", "input", "coils", "discretes"}:
        raise ValueError(f"Invalid register kind: {kind}. Must be 'holding', 'input', 'coils', or 'discretes'")

    if kind == "holding":
        modbus_data = modbus_utils.read_holding_registers(
            address,
            count,
            server_id,
            host,
            port
        )
    elif kind == "input":
        modbus_data = modbus_utils.read_input_registers(
            address,
            count,
            server_id,
            host,
            port
        )
    elif kind == "coils":
        modbus_data = modbus_utils.read_coils(
            address,
            count,
            server_id,
            host,
            port
        )
    else:
        modbus_data = modbus_utils.read_discrete_inputs(
            address,
            count,
            server_id,
            host,
            port
        )
    
    logger.info(f"Successfully read {len(modbus_data)} registers from device '{device.name}'")
    return modbus_data


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
        
        await edge_aggregator_cache_service.set(
            key=cache_key_latest,
            value=cache_data,
            ttl=settings.poll_cache_ttl
        )
        
        await edge_aggregator_cache_service.set(
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
    mapped_registers: List[MappedRegisterData],
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
        
        inserted_count = await insert_register_readings_batch(site_id, batch_readings)
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
        # 1. Get polling configuration from device configs
        config_ids = list(device.configs or [])
        if not config_ids:
            result["error"] = f"No device configs associated with device '{device_name}'"
            logger.warning(result["error"])
            return result

        # 2. Get site_name if site_id is available
        site_name = None
        if device.site_id:
            try:
                site = await get_site_by_id(device.site_id)
                if site:
                    site_name = site.name
            except Exception as e:
                logger.warning(f"Could not fetch site name for site_id '{device.site_id}': {e}")

        # 3. Poll each device config associated with this device
        total_cache_successful = 0
        total_cache_failed = 0
        total_db_successful = 0
        total_db_failed = 0
        any_success = False

        #TODO: lets write a function that get all site,device, and config information by one call. Also priorotize cache over db. 

        for config_id in config_ids:
            device_config = await get_device_config(config_id)
            if device_config is None:
                logger.warning(
                    f"Device config '{config_id}' not found for device '{device_name}'"
                )
                continue

            polling_config = {
                "poll_address": device_config.poll_address,
                "poll_count": device_config.poll_count,
                "poll_kind": device_config.poll_kind,  # "holding", "input", "coils", "discretes"
                "poll_enabled": device.poll_enabled
            }

            registers = device_config.registers or []
            logger.info(
                f"Loaded {len(registers)} register points for device '{device_name}' "
                f"(config_id='{config_id}')"
            )

            if not registers:
                logger.warning(
                    f"No register points to poll for device '{device_name}' (config_id='{config_id}')"
                )
                continue

            # 4. Read Modbus registers
            modbus_data = await read_device_registers(device, polling_config)

            # 5. Map register data
            register_map = {"registers": registers}
            mapped_registers = map_modbus_data_to_registers(
                register_map=register_map,
                modbus_read_data=modbus_data,
                poll_start_address=polling_config["poll_address"]
            )

            if not mapped_registers:
                logger.warning(
                    f"No register points mapped for device '{device_name}' (config_id='{config_id}')"
                )
                continue

            # 6. Store data in cache and database
            timestamp = datetime.now(timezone.utc).isoformat()
            timestamp_dt = datetime.now(timezone.utc)

            # Add device_id (Modbus unit/slave ID) to polling_config for cache
            polling_config["device_id"] = device.modbus_server_id  # Modbus device_id

            cache_successful, cache_failed = await store_device_data_in_cache(
                device_name, mapped_registers, polling_config, timestamp, site_name
            )
            total_cache_successful += cache_successful
            total_cache_failed += cache_failed

            if device.id is not None and device.site_id:
                db_successful, db_failed = await store_device_data_in_db(
                    device.id, device.site_id, mapped_registers, timestamp_dt
                )
            else:
                logger.debug(
                    f"Device '{device_name}' not found in database, skipping DB storage"
                )
                db_successful, db_failed = 0, len(mapped_registers)

            total_db_successful += db_successful
            total_db_failed += db_failed
            any_success = True

        if not any_success:
            result["error"] = f"No device configs were successfully polled for '{device_name}'"
            logger.warning(result["error"])
            return result

        result["success"] = True
        result["cache_successful"] = total_cache_successful
        result["cache_failed"] = total_cache_failed
        result["db_successful"] = total_db_successful
        result["db_failed"] = total_db_failed

        logger.info(
            f"Device '{device_name}' polling completed: "
            f"Cache: {total_cache_successful} successful, {total_cache_failed} failed | "
            f"Database: {total_db_successful} successful, {total_db_failed} failed"
        )
        
    except Exception as e:
        # Pass device host/port for better error messages
        status_code, error_message = translate_modbus_error(
            e,
            host=device.modbus_host,
            port=device.modbus_port
        )
        result["error"] = f"status_code={status_code}, error_message={error_message}"
        logger.error(
            f"Error polling device '{device_name}': {result['error']}",
            exc_info=True
        )
    
    return result

# TODO: eventually this function also needs to be called by another function to grab all the devices for multiple sites
async def cron_job_poll_modbus_registers() -> None:
    """
    Scheduled job to poll Modbus registers for all enabled devices.
    
    This job:
    1. Gets list of devices to poll (from database, filtered by poll_enabled)
    2. For each device:
       - Loads register map (cache first and DB second)
       - Reads Modbus registers using device-specific polling config
       - Maps register data to register points
       - Stores data in Redis cache and database
    3. Handles errors per device (isolated - one device failure doesn't stop others)
    4. Logs summary statistics
    """
    logger.info("Starting Modbus polling job")
    
    try:
        # 1. Get devices to poll across all sites (site-scoped function)
        devices_to_poll: List[DeviceListItem] = []
        all_sites = await get_all_sites()
        logger.info(f"Retrieved {len(all_sites)} site(s) from database")
        for site in all_sites:
            try:
                site_devices = await get_devices_to_poll(site.id)
                devices_to_poll.extend(site_devices)
                logger.debug(
                    f"Retrieved {len(site_devices)} device(s) to poll from site '{site.name}' (ID: {site.id})"
                )
            except Exception as e:
                logger.warning(
                    f"Error retrieving devices to poll for site '{site.name}' (ID: {site.id}): {e}"
                )
        
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
