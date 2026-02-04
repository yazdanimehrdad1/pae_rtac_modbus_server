"""Polling jobs for Modbus data collection."""

import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, TypedDict

from helpers.modbus import translate_modbus_error
from modbus.client import ModbusClient
from modbus.modbus_utills import ModbusUtils
from config import settings
from logger import get_logger
from utils.modbus_mapper import map_modbus_data_to_device_points, MappedRegisterData
from helpers.sites import get_complete_site_data
from db.sites import get_site_by_id, get_all_sites
from schemas.db_models.models import DeviceListItem, DeviceWithConfigs
from utils.store_data_readings import (
    store_device_data_in_cache,
    store_device_data_in_db,
    store_device_data_in_db_translated,
)
from helpers.device_points import get_device_points

logger = get_logger(__name__)

# Initialize services
edge_aggregator_modbus_client = ModbusClient()
edge_aggregator_modbus_utils = ModbusUtils(edge_aggregator_modbus_client)
direct_modbus_utils_by_endpoint: dict[tuple[str, int], ModbusUtils] = {}



class PollResult(TypedDict, total=False):
    """Result of polling a single device."""
    device_name: str
    success: bool
    cache_successful: int
    cache_failed: int
    db_successful: int
    db_failed: int
    error: Optional[str]

def get_direct_modbus_utils(host: str, port: int) -> ModbusUtils:
    endpoint = (host, port)
    modbus_utils = direct_modbus_utils_by_endpoint.get(endpoint)
    if modbus_utils is None:
        modbus_utils = ModbusUtils(ModbusClient())
        direct_modbus_utils_by_endpoint[endpoint] = modbus_utils
    return modbus_utils

async def get_enabled_devices_to_poll(site_devices: List[DeviceListItem]) -> List[DeviceListItem]:
    """
    Get list of devices to poll from database, filtered by poll_enabled.
    
    Returns:
        List of devices that have polling enabled
    """
    # Filter devices by poll_enabled from database
    devices_to_poll = []
    for device in site_devices:
        # Check poll_enabled directly from device
        if device.poll_enabled:
            devices_to_poll.append(device)
            logger.debug(f"Device '{device.name}' (ID: {device.device_id}) has polling enabled")
        else:
            # Polling disabled
            logger.debug(
                f"Device '{device.name}' (ID: {device.device_id}) has polling disabled "
                f"(poll_enabled={device.poll_enabled}), skipping"
            )
    
    logger.info(
        f"Found {len(devices_to_poll)} device(s) to poll out of {len(site_devices)} total device(s) "
    )
    return devices_to_poll


async def read_device_registers(
    device: DeviceListItem,
    polling_config: Dict[str, Any]
) -> list[int | bool]:
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
    #TODO: it is very important, when the device_config is created, there is a validation to autmatically calculate the count or default to 125
    # Why/how count is dominated by 
    # 1: last register - first rgister address + 1
    # 2: If last register has a size of 2,4 then the count is the last register address + size - first register address
    address = polling_config["poll_address"]
    count = polling_config["poll_count"]
    kind = polling_config["poll_kind"]
    server_id = device.server_address
    host = device.host
    port = device.port
    
    logger.debug(
        f"Reading Modbus registers for device '{device.name}': "
        f"kind={kind}, address={address}, count={count}, server_address={server_id}"
    )
    
    # Use appropriate ModbusUtils method based on register kind
    # Pass device-specific host and port for connection

    if device.read_from_aggregator:
        modbus_utils = edge_aggregator_modbus_utils
        host = None
        port = None
    else:
        modbus_utils = get_direct_modbus_utils(host, port)

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


async def poll_single_device(site_name: str, device: DeviceWithConfigs) -> PollResult:
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

    device_without_configs = DeviceListItem(
        device_id=device.device_id,
        site_id=device.site_id,
        name=device.name,
        type=device.type,
        vendor=device.vendor,
        model=device.model,
        host=device.host,
        port=device.port,
        timeout=device.timeout,
        server_address=device.server_address,
        description=device.description,
        poll_enabled=device.poll_enabled,
        read_from_aggregator=device.read_from_aggregator,
        protocol=device.protocol,
        created_at=device.created_at,
        updated_at=device.updated_at
    )
   

    total_cache_successful = 0
    total_cache_failed = 0
    total_db_successful = 0
    total_db_failed = 0
    combined_mapped_registers_list_all_configs_per_device = []
    last_polling_config = None

    try:

        device_points_all = await get_device_points(device.site_id, device.device_id)


        for config in device.configs:
            polling_config = {
                "poll_address": config.poll_start_index,
                "poll_count": config.poll_count,
                "poll_kind": config.poll_kind, 
            }

            points = [
                point for point in device_points_all
                if point.config_id == config.config_id
            ]


            #registers = config_points.points or []  
            logger.info(
                f"Loaded {len(points)} points for device '{device_name}' "
                f"(config_id='{config.config_id}')"
            )

            if not points:
                logger.warning(
                    f"No points to poll for device '{device_name}' (config_id='{config.config_id}')"
                )
                continue

      
            try:
                if device.protocol == "Modbus":
                    modbus_data = await read_device_registers(device_without_configs, polling_config)
                    mapped_registers = map_modbus_data_to_device_points(
                        device_points_list=points,
                        modbus_read_data=modbus_data,
                        poll_start_address=polling_config["poll_address"]
                    )

                    if not mapped_registers:
                        logger.warning(
                            f"No register points mapped for device '{device_name}' (config_id='{config.config_id}')"
                        )
                        continue

                    combined_mapped_registers_list_all_configs_per_device.extend(mapped_registers)
                    last_polling_config = polling_config

                else:
                    print("Device protocol is not DNP")
            except Exception as e:
                if device.read_from_aggregator:
                    error_host = settings.modbus_host
                    error_port = settings.modbus_port
                else:
                    error_host = device.host
                    error_port = device.port
                status_code, error_message = translate_modbus_error(
                    e,
                    host=error_host,
                    port=error_port
                )
                result["error"] = f"status_code={status_code}, error_message={error_message}"
                logger.warning(
                    f"Error polling device '{device_name}': {result['error']}"
                )
                continue




        timestamp = datetime.now(timezone.utc).isoformat()
        timestamp_dt = datetime.now(timezone.utc)

        #TO_REMOVE
        print("this is combined_mapped_registers_list_all_configs_per_device", json.dumps(combined_mapped_registers_list_all_configs_per_device, indent=4))

        if not combined_mapped_registers_list_all_configs_per_device or last_polling_config is None:
            result["error"] = f"No configs were successfully polled for '{device_name}'"
            logger.warning(result["error"])
            return result

        cache_successful, cache_failed = await store_device_data_in_cache(
            device_name,
            combined_mapped_registers_list_all_configs_per_device,
            last_polling_config,
            timestamp,
            site_name
        )
        total_cache_successful += cache_successful
        total_cache_failed += cache_failed

        
        db_successful, db_failed = await store_device_data_in_db(
                device.device_id,
                device.site_id,
                combined_mapped_registers_list_all_configs_per_device,
                timestamp_dt
        )

        ###################################################################################
        # This is under development. The purpose is to store scaled and translated bitfields 
        # and enums in the database.
        ###################################################################################

        # await store_device_data_in_db_translated(
        #     device.device_id,
        #     device.site_id,
        #     combined_mapped_registers_list_all_configs_per_device,
        #     timestamp_dt
        # )

        total_db_successful += db_successful
        total_db_failed += db_failed

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
        if device.read_from_aggregator:
            error_host = settings.modbus_host
            error_port = settings.modbus_port
        else:
            error_host = device.host
            error_port = device.port
        status_code, error_message = translate_modbus_error(
            e,
            host=error_host,
            port=error_port
        )
        result["error"] = f"status_code={status_code}, error_message={error_message}"
        logger.error(
            f"Error polling device '{device_name}': {result['error']}",
            exc_info=True
        )
    
    return result

# TODO: eventually this function also needs to be called by another function to grab all the devices for multiple sites
async def poll_modbus_registers_per_site(site_id: int) -> None:
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

        complete_site_data = await get_complete_site_data(site_id)
        if complete_site_data is None:
            logger.warning(f"Site with id {site_id} not found")
            return
        
        site_name = complete_site_data.name
        devices_list = complete_site_data.devices
    
        
        if not devices_list:
            logger.warning("No devices for site with id {site_id}")
            return

        enabled_devices_to_poll = await get_enabled_devices_to_poll(devices_list)
  
        # 2. Poll each device in parallel (errors are isolated per device)
        # Use asyncio.gather to run all device polling operations concurrently
        # Note: ModbusClient is safe for concurrent use because:
        # - It only stores read-only configuration
        # - Each read_registers() call creates a new ModbusTcpClient connection via context manager
        # - No shared mutable state between concurrent calls
        results: List[PollResult] = await asyncio.gather(
            *[poll_single_device(site_name,device) for device in enabled_devices_to_poll],
            return_exceptions=True
        )
        
        # Convert any exceptions to error results
        processed_results: List[PollResult] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                device_name = enabled_devices_to_poll[i].name if i < len(enabled_devices_to_poll) else "unknown"
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


async def cron_job_poll_modbus_registers_all_sites() -> None:
    """
    Scheduled job to poll Modbus registers for all sites.
    """
    logger.info("Starting Modbus polling job for all sites")
    try:
        all_sites = await get_all_sites()
        logger.info(f"Retrieved {len(all_sites)} site(s) from database")
        for site in all_sites:
            await poll_modbus_registers_per_site(site.site_id)
    except Exception as e:
        logger.error(f"Error in Modbus polling job for all sites: {e}", exc_info=True)
        # Don't re-raise - let scheduler handle retry on next interval