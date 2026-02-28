"""Polling helpers for Modbus data collection."""

import asyncio
from datetime import datetime, timezone
from typing import List, Optional

from helpers.modbus import translate_modbus_error
from pymodbus.exceptions import ConnectionException
from config import settings
from logger import get_logger
from helpers.modbus.modbus_data_mapping import map_modbus_data_to_device_points
from helpers.sites import get_complete_site_data
from schemas.api_models import DeviceListItem, DeviceWithConfigs, PollResult, PollingConfig
from utils.store_data_readings import store_device_data_in_db
from helpers.device_points import get_device_points
from helpers.workers.device_poll import get_enabled_devices_to_poll, read_device_registers

logger = get_logger(__name__)

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
    combined_mapped_registers_list_all_configs_per_device = []
    last_polling_config = None
    last_read_error: Optional[str] = None

    try:
        device_points_all = await get_device_points(device.device_id)
        timestamp = datetime.now(timezone.utc).isoformat()
        timestamp_dt = datetime.now(timezone.utc)

        for config in device.configs:
            polling_config = PollingConfig(
                poll_address=config.poll_start_index,
                poll_count=config.poll_count,
                poll_kind=config.poll_kind,
            )
            try:
                modbus_data_readings_per_config = await read_device_registers(
                    device_without_configs,
                    polling_config
                )

                if not modbus_data_readings_per_config:
                    logger.info(
                        "No Modbus data readings for device '%s' (config_id='%s')",
                        device_name,
                        config.config_id
                    )
                    continue

                device_points = [
                    point for point in device_points_all
                    if point.config_id == config.config_id
                ]

                mapped_registers_readings_list = map_modbus_data_to_device_points(
                    timestamp_dt=timestamp_dt,
                    device_points_list=device_points,
                    modbus_read_data=modbus_data_readings_per_config,
                    poll_start_address=int(polling_config.poll_address)
                )
                combined_mapped_registers_list_all_configs_per_device.extend(mapped_registers_readings_list)
                last_polling_config = polling_config

            except Exception as e:
                if isinstance(e, ConnectionException):
                    logger.warning(f"Error reading device registers: {e}, polling_config: {polling_config}")
                else:
                    logger.error(f"Error reading device registers: {e}, polling_config: {polling_config}", exc_info=True)
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
                last_read_error = result["error"]
                logger.warning(
                    f"Error polling device '{device_name}': {result['error']}"
                )
                continue


        if not combined_mapped_registers_list_all_configs_per_device or last_polling_config is None:
            if last_read_error:
                result["error"] = last_read_error
            else:
                result["error"] = f"No configs were successfully polled for '{device_name}'"
            logger.warning(result["error"])
            return result

        db_successful, db_failed = await store_device_data_in_db(
                device.device_id,
                device.site_id,
                combined_mapped_registers_list_all_configs_per_device,
                timestamp_dt
        )

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
