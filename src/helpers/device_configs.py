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


def set_register_defaults(registers: list) -> None:
    """
    Set default values for register fields in-place.
    """
    for register in registers:
        if isinstance(register, dict):
            if register.get("scale_factor") is None:
                register["scale_factor"] = 1.0
            if register.get("unit") is None:
                register["unit"] = "unit"
        else:
            if getattr(register, "scale_factor", None) is None:
                register.scale_factor = 1.0
            if getattr(register, "unit", None) is None:
                register.unit = "unit"


def compute_poll_range(registers: list) -> tuple[int, int, int]:
    """
    Compute min register number, max register end, and poll count.
    """
    min_register_number = min(register.register_address for register in registers)
    max_register_end = max(
        register.register_address + register.size - 1
        for register in registers
    )
    poll_count = max_register_end - min_register_number + 1
    return min_register_number, max_register_end, poll_count


def validate_duplicate_registers(registers: list) -> None:
    """
    Validate no duplicate register addresses exist.
    """
    seen_addresses: dict[int, list[int]] = {}
    duplicates: list[dict[str, int | list[int]]] = []
    duplicate_register_addresses: list[int] = []
    for idx, register in enumerate(registers):
        if isinstance(register, dict):
            register_data = register
        elif hasattr(register, "model_dump"):
            register_data = register.model_dump()
        else:
            register_data = vars(register)
        register_address = register_data.get("register_address")
        if register_address is None:
            continue
        seen_addresses.setdefault(register_address, []).append(idx)

    for address, indices in seen_addresses.items():
        if len(indices) > 1:
            duplicate_register_addresses.append(address)
            duplicates.append(
                {
                    "register_address": address,
                    "indices": indices,
                }
            )

    if duplicates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Duplicate register addresses",
                "message": "One or more registers share the same register_address",
                "duplicate_register_addresses": duplicate_register_addresses,
                "duplicates": duplicates,
            },
        )


def validate_register_addresses(poll_address: int, registers: list) -> None:
    """
    Validate register addresses are within allowed poll range.
    """
    validate_duplicate_registers(registers)
    max_address = poll_address + MAX_MODBUS_POLL_REGISTER_COUNT
    missing_fields: list[dict[str, str]] = []
    invalid_registers: list[dict[str, int | str]] = []
    for idx, register in enumerate(registers):
        if isinstance(register, dict):#this is a dictionary, we are using the dictionary directly
            register_data = register
        elif hasattr(register, "model_dump"):#this is a pydantic model, we are using the model_dump method to convert the pydantic model to a dictionary
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

    set_register_defaults(config.registers)

   
    min_register_number, max_register_end, poll_count = compute_poll_range(
        config.registers
    )

    if poll_count > MAX_MODBUS_POLL_REGISTER_COUNT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Poll count exceeds maximum allowed",
                "message": "The number of registers to poll exceeds the maximum allowed, consider adding multiple device configs",
                "max_poll_count": MAX_MODBUS_POLL_REGISTER_COUNT,
                "poll_count": poll_count,
                "min_register_number": min_register_number,
                "max_register_end": max_register_end,
                "registers": config.registers,
            },
        )


    warning_detail = None
    if min_register_number != config.poll_address or poll_count != config.poll_count:
        warning_detail = {
            "warning": "Poll range computed from registers differs from payload",
            "min_register_number": min_register_number,
            "max_register_end": max_register_end,
            "computed_poll_count": poll_count,
            "payload_poll_address": config.poll_address,
            "payload_poll_count": config.poll_count,
        }
        logger.warning(
            "Min register number or poll count does not match the config; continuing with payload values",
            extra=warning_detail,
        )

    created_config = await create_device_config_for_device(site_id, device_id, config)
    if warning_detail:
        created_config = created_config.model_copy(update={"warnings": warning_detail})

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
