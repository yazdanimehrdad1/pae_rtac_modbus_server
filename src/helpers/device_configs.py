"""Device config helper functions for DB/cache coordination."""

from fastapi import HTTPException, status

from cache.cache import CacheService
from db.device_configs import create_device_config_for_device
from db.devices import get_device_by_id
from logger import get_logger
from schemas.db_models.models import DeviceConfigData, DeviceConfigResponse

logger = get_logger(__name__)
cache_service = CacheService()

MAX_MODBUS_POLL_REGISTER_COUNT = 125


def validate_register_addresses(poll_address: int, registers: list) -> None:
    """
    Validate register addresses are within allowed poll range.
    """
    max_address = poll_address + MAX_MODBUS_POLL_REGISTER_COUNT
    missing_fields: list[dict[str, str]] = []
    invalid_registers: list[dict[str, int | str]] = []
    for idx, register in enumerate(registers):
        if isinstance(register, dict):
            register_data = register
        elif hasattr(register, "model_dump"):
            register_data = register.model_dump()
        else:
            register_data = vars(register)

        register_address = register_data.get("register_address")
        register_size = register_data.get("size")

        if register_address is None:
            missing_fields.append(
                {
                    "index": idx,
                    "field": "register_address",
                    "message": f"The 'registers[{idx}].register_address' field is required",
                }
            )
            continue
        if register_size is None:
            missing_fields.append(
                {
                    "index": idx,
                    "field": "size",
                    "message": f"The 'registers[{idx}].size' field is required",
                }
            )
            continue
        if not register_data.get("register_name"):
            missing_fields.append(
                {
                    "index": idx,
                    "field": "register_name",
                    "message": f"The 'registers[{idx}].register_name' field is required",
                }
            )
            continue
        if not register_data.get("data_type"):
            missing_fields.append(
                {
                    "index": idx,
                    "field": "data_type",
                    "message": f"The 'registers[{idx}].data_type' field is required",
                }
            )
            continue

        if register_address < poll_address:
            invalid_registers.append(
                {
                    "index": idx,
                    "register_address": register_address,
                    "error": (
                        f"register_address ({register_address}) is less than poll_address "
                        f"({poll_address})"
                    ),
                }
            )
            continue

        max_register_address = register_address + register_size - 1
        if max_register_address > max_address:
            invalid_registers.append(
                {
                    "index": idx,
                    "register_address": register_address,
                    "size": register_size,
                    "max_address": max_register_address,
                    "error": (
                        f"register_address ({register_address}) + size ({register_size}) - 1 = "
                        f"{max_register_address} exceeds poll_address + {MAX_MODBUS_POLL_REGISTER_COUNT} "
                        f"({max_address})"
                    ),
                }
            )

    if missing_fields:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "Missing required field",
                "message": "One or more registers are missing required fields",
                "missing_fields": missing_fields,
            },
        )

    if invalid_registers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Invalid register addresses",
                "message": "One or more registers have addresses outside the poll range",
                "invalid_registers": invalid_registers,
                "poll_address": poll_address,
                "max_address": max_address,
            },
        )


async def create_device_config_cache_db(
    site_id: int,
    device_id: int,
    config: DeviceConfigData
) -> DeviceConfigResponse:
    """
    Create a device config in the DB and update device cache.
    """
    # Basic validation (additional rules TBD)
    if config.site_id != site_id or config.device_id != device_id:
        raise ValueError("Path site_id/device_id must match body")

    validate_register_addresses(config.poll_address, config.registers)


    for register in config.registers:
        if register.scale_factor is None:
            register.scale_factor = 1.0
        if register.unit is None:
            register.unit = None

    created_config = await create_device_config_for_device(site_id, device_id, config)

    updated_device = await get_device_by_id(device_id, site_id)
    if updated_device is None:
        logger.warning(
            "Device %s not found after config creation; cache not updated",
            device_id,
        )
        return created_config

    cache_key = f"device:site:{site_id}:device_id:{device_id}"
    cached = await cache_service.set(
        key=cache_key,
        value=updated_device.model_dump(mode="json"),
    )
    if not cached:
        logger.error(
            "Failed to update cache for device %s in site %s after config create",
            device_id,
            site_id,
        )
        raise RuntimeError("Failed to update device cache after config creation")

    return created_config
