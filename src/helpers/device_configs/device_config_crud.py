"""Device config CRUD helper functions."""

from db.device_configs import create_config_for_device, delete_config, get_config, update_config, get_configs_for_device
from api.controllers.devices import get_device_by_id
from utils.exceptions import NotFoundError, ValidationError, InternalError
from logger import get_logger
from typing import Optional

from schemas.api_models import ConfigCreateRequest, ConfigResponse, ConfigUpdate
from helpers.device_configs.configs_validation import validate_point_addresses
from helpers.device_points import (
    map_device_configs_to_device_points,
    create_device_points,
    validate_device_points_uniqueness,
)

logger = get_logger(__name__)


async def create_config_helper(
    site_id: int,
    device_id: int,
    config: ConfigCreateRequest
) -> ConfigResponse:
    """Create a config in the DB."""
    if config.site_id != site_id or config.device_id != device_id:
        raise ValidationError("Path site_id/device_id must match body")

    device = await get_device_by_id(site_id, device_id)
    if not device:
        raise NotFoundError(f"Device with id {device_id} not found")

    validation = validate_point_addresses(config.poll_start_index, config.points)
    if not validation.is_valid:
        raise ValidationError(
            "Validation errors in config points",
            payload={"errors": validation.errors}
        )
    config.poll_start_index = validation.min_register_number
    config.poll_count = validation.poll_count

    # TODO: You have to make sure both device_points and device_configs are created.
    # Maybe try to create device_points first, and if it fails, roll back the config creation

    


    create_config_result = await create_config_for_device(site_id, device_id, config)
    device_points_list = map_device_configs_to_device_points(config.points, device, create_config_result.config_id)
    uniqueness_errors = await validate_device_points_uniqueness(device_points_list, device)
    if uniqueness_errors:
        await delete_config(create_config_result.config_id)
        raise ValidationError(
            "Device point conflicts",
            payload={"errors": uniqueness_errors}
        )

    # device points are validated, now create them
    create_device_points_result = await create_device_points(device_points_list)

    if not create_device_points_result:
        if create_config_result:
            await delete_config(create_config_result.config_id)
        raise InternalError("Failed to create device points")

    logger.info(
        "Config and associated device points created successfully",
        extra={
            "site_id": site_id,
            "device_id": device_id,
            "config": create_config_result,
            "device_points_created_count": len(device_points_list),
        },
    )

    return create_config_result


async def get_config_db(config_id: str) -> Optional[ConfigResponse]:
    return await get_config(config_id)


async def update_config_db(config_id: str, update: ConfigUpdate) -> Optional[ConfigResponse]:
    return await update_config(config_id, update)


async def delete_config_db(config_id: str) -> bool:
    return await delete_config(config_id)


async def get_configs_for_device_db(device_id: int, site_id: Optional[int] = None) -> list[ConfigResponse]:
    return await get_configs_for_device(device_id, site_id)
