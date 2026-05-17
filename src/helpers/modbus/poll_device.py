"""Polling helpers for Modbus data collection."""

import asyncio
from datetime import datetime, timezone
from typing import List

from helpers.modbus import translate_modbus_error
from pymodbus.exceptions import ConnectionException
from config import settings
from logger import get_logger
from helpers.modbus.modbus_data_mapping import map_modbus_data_to_device_points
from helpers.sites import get_complete_site_data
from schemas.api_models import DeviceListItem, DeviceWithConfigs, PollResult, PollingConfig
from utils.store_data_readings import store_device_data_in_db, DbStoreResult
from helpers.device_points import get_device_points
from helpers.workers.device_poll import get_enabled_devices_to_poll, read_device_registers

logger = get_logger(__name__)

_MODBUS_MAX_REGISTERS_PER_READ = 125

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
        # TODO: I think this can also be obtained from cache instead of DB
        complete_site_data = await get_complete_site_data(site_id)
        if complete_site_data is None:
            logger.warning(f"Site with id {site_id} not found")
            return
        #TODO: this can be optimized to only query devices with poll_enabled=true in the first place, 
        # instead of getting all devices and filtering in python
        site_name = complete_site_data.name
        devices_list = complete_site_data.devices 

        if not devices_list:
            logger.warning("No devices for site with id {site_id}")
            return

        enabled_devices_to_poll = await get_enabled_devices_to_poll(devices_list)

        results: List[PollResult] = await asyncio.gather(
            *[poll_single_device_modbus(site_name, device) for device in enabled_devices_to_poll],
            return_exceptions=True
        )

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


# TODO: eventually the device points should be queried as part of this function, and determines the polls range itself
#  Inorder to do this we need to add register_type:holding, input, coils, discretes to the polling config and update the read_device_registers function to use it
# Infact you can redefine the polling config in a helper function and and do the for loop as you are doing in the first TRY
async def poll_single_device_modbus(site_name: str, device: DeviceWithConfigs) -> PollResult:
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
    try:
        # TODO: consider getting from cache or optimize the DB call somehow.
        device_points_all = await get_device_points(device.device_id)
        timestamp_dt = datetime.now(timezone.utc)

        register_address_value_map_all = await _poll_all_device_configs_register_values( device.configs, device_without_configs, device_name)

        mapped_raw_registers_to_device_points_all = map_modbus_data_to_device_points(
            timestamp_dt=timestamp_dt,
            device_points_list=device_points_all,
            register_map=register_address_value_map_all,
        )

        if not mapped_raw_registers_to_device_points_all:
            result["error"] = f"No device points configured for '{device_name}' — skipping DB store"
            logger.warning(result["error"])
            return result

        # TODO: I think here there should be two types of DB storing
        # 1: Storing raw registers for short term (maybe upto 1 week) for debugging and site development process.
        # 2: Storing the mapped/calculated points for long term and historian purposes. This will be the data that is used by the frontend and other consumers.
        db_result: DbStoreResult = await store_device_data_in_db(
                device.device_id,
                device.site_id,
                mapped_raw_registers_to_device_points_all,
                timestamp_dt
        )

        total_db_successful += db_result.successful
        total_db_failed += db_result.failed

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

async def _poll_all_device_configs_register_values(
    configs,
    device_without_configs: DeviceListItem,
    device_name: str,
) -> dict[int, int | bool]:
    """
    Poll every config block for a device and return one merged register map.
    """

    register_address_value_map: dict[int, int | bool] = {}

    for config in configs:
        polling_config = None  # safe default so except block can always reference it

        try:
            polling_config = PollingConfig(
                poll_address=config.poll_start_index,
                poll_count=config.poll_count,
                poll_kind=config.poll_kind,
            )

            config_register_address_value_map = await _read_config_registers(
                device_without_configs,
                polling_config,
            )

            if not config_register_address_value_map:
                logger.info(
                    "No Modbus data readings for device '%s' (config_id='%s')",
                    device_name,
                    config.config_id,
                )
                continue

            # Merge all register blocks together
            register_address_value_map.update(config_register_address_value_map)

        except Exception as error:
            if device_without_configs.read_from_aggregator:
                error_host = settings.modbus_host or "unknown"
                error_port = settings.modbus_port or "unknown"
            else:
                error_host = device_without_configs.host or "unknown"
                error_port = device_without_configs.port or "unknown"

            try:
                status_code, error_message = translate_modbus_error(
                    error,
                    host=error_host,
                    port=error_port,
                )
            except Exception as translate_error:
                status_code = 500
                error_message = (
                    f"{type(error).__name__}: {error} "
                    f"(error translation also failed: {translate_error})"
                )

            if isinstance(error, ConnectionException):
                logger.warning(
                    "Connection error polling device '%s' (config_id='%s', "
                    "host=%s, port=%s, config=%s): [%s] %s",
                    device_name, config.config_id, error_host, error_port,
                    polling_config, status_code, error_message,
                )
            else:
                logger.error(
                    "Unexpected error polling device '%s' (config_id='%s', "
                    "host=%s, port=%s, config=%s): [%s] %s",
                    device_name, config.config_id, error_host, error_port,
                    polling_config, status_code, error_message,
                    exc_info=True,
                )
            # continue to the next config — one failed config does not abort the device poll

    return register_address_value_map


async def _read_config_registers(
    device: DeviceListItem,
    polling_config: PollingConfig,
) -> dict[int, int | bool]:
    """
    Read Modbus registers in chunks and return a register map.

    Example output:
    {
        1400: 0,
        1401: 111,
        1402: 50,
    }
    """

    start_address = int(polling_config.poll_address)
    total_count = polling_config.poll_count

    register_address_value_map: dict[int, int | bool] = {}

    # Simple single-read case
    if total_count <= _MODBUS_MAX_REGISTERS_PER_READ:

        raw_values = await read_device_registers(device, polling_config)

        if not raw_values:
            return {}

        register_address_value_map.update({
            start_address + i: value
            for i, value in enumerate(raw_values)
        })

        return register_address_value_map

    # Chunked-read case
    offset = 0

    while offset < total_count:

        chunk_count = min(
            _MODBUS_MAX_REGISTERS_PER_READ,
            total_count - offset,
        )

        chunk_start_address = start_address + offset

        chunk_config = PollingConfig(
            poll_address=chunk_start_address,
            poll_count=chunk_count,
            poll_kind=polling_config.poll_kind,
        )

        chunk_data = await read_device_registers(device, chunk_config)

        if not chunk_data:
            logger.warning(
                "Chunked read returned no data at address=%s, count=%s — aborting poll",
                chunk_start_address,
                chunk_count,
            )
            return {}

        # Store each register using absolute register address as key
        register_address_value_map.update({
            chunk_start_address + i: value
            for i, value in enumerate(chunk_data)
        })

        offset += chunk_count

    return register_address_value_map

