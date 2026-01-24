"""Device config helper functions for DB/cache coordination."""

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
    for register in registers:
        register_address = getattr(register, "register_address", None)
        if register_address is None:
            register_address = register.get("register_address")
        if register_address is None or register_address < poll_address or register_address > max_address:
            raise ValueError(
                f"Register address {register_address} is out of range for poll_address {poll_address}"
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
