"""Device config CRUD helper functions for DB/cache coordination."""

import json

from cache.cache import CacheService
from db.device_configs import create_config_for_device, delete_config
from db.devices import get_device_by_id
from utils.exceptions import NotFoundError, ValidationError, InternalError
from logger import get_logger
from schemas.db_models.models import ConfigCreateRequest, ConfigResponse
from helpers.device_configs.configs_validation import (
    MAX_MODBUS_POLL_REGISTER_COUNT,
    set_point_defaults,
    compute_poll_range,
    validate_point_addresses,
    validate_config_points_fields,
    validate_poll_range_consistency,
)
from helpers.device_points import (
    map_device_configs_to_device_points,
    create_device_points,
    validate_device_points_uniqueness,
)

logger = get_logger(__name__)
cache_service = CacheService()


async def create_config_cache_db(
    site_id: int,
    device_id: int,
    config: ConfigCreateRequest
) -> ConfigResponse:
    """
    Create a config in the DB and update device cache.
    """
    # Basic validation (additional rules TBD)
    if config.site_id != site_id or config.device_id != device_id:
        raise ValidationError("Path site_id/device_id must match body")


    validation_result = validate_point_addresses(config.poll_start_index, config.points)
    if validation_result.missing_fields:
        raise ValidationError(
            "One or more points are missing required fields",
            payload={
                "error_type": "Missing required field",
                "missing_fields": [err.model_dump(exclude_none=True) for err in validation_result.missing_fields],
            },
        )
    if validation_result.invalid_registers:
        max_address = config.poll_start_index + MAX_MODBUS_POLL_REGISTER_COUNT
        raise ValidationError(
            "One or more points have addresses outside the poll range",
            payload={
                "error_type": "Invalid point addresses",
                "invalid_registers": [err.model_dump(exclude_none=True) for err in validation_result.invalid_registers],
                "poll_start_index": config.poll_start_index,
                "max_address": max_address,
            },
        )

    set_point_defaults(config.points)

    field_errors = validate_config_points_fields(config.points)
    if field_errors:
        raise ValidationError(
            "Validation errors in point fields",
            payload={"error_type": "Invalid point fields", "errors": field_errors}
        )

    min_register_number, max_register_end, poll_count = compute_poll_range(
        config.points
    )

    poll_range_error = validate_poll_range_consistency(
        poll_count=poll_count,
        min_register_number=min_register_number,
        max_register_end=max_register_end,
        points=config.points,
        payload_poll_start_index=config.poll_start_index,
        payload_poll_count=config.poll_count
    )
    if poll_range_error:
        raise ValidationError(
            poll_range_error,
            payload={
                "error_type": "Poll count exceeds maximum allowed",
                "max_poll_count": MAX_MODBUS_POLL_REGISTER_COUNT,
                "poll_count": poll_count,
                "min_register_number": min_register_number,
                "max_register_end": max_register_end,
            },
        )

    # TODO: You have to make sure both device_points and device_configs are created.
    # Maybe try to create device_points first, and if it fails, roll back the config creation

    # Validate point uniqueness against DB before creating config
    # device is type of DeviceWithConfigs
    device = await get_device_by_id(device_id, site_id)

    if not device:
         raise NotFoundError(f"Device with id {device_id} not found")

    device_points_list = map_device_configs_to_device_points(config.points, device)
    device_points_uniquness_result = await validate_device_points_uniqueness(device_points_list, device)
    create_config_result = await create_config_for_device(site_id, device_id, config)

    # Assign the newly created config_id to the points list
    for pt in device_points_list:
        pt["config_id"] = create_config_result.config_id

    # device points are validated, now create them
    create_device_points_result = await create_device_points(device_points_list)

    if not create_device_points_result:
        if create_config_result:
            await delete_config(create_config_result.config_id)
        raise InternalError("Failed to create device points")

    cache_key = f"device:site:{site_id}:device_id:{device_id}"
    await cache_service.delete(cache_key)
    logger.info(
        "Config created successfully",
        extra={
            "site_id": site_id,
            "device_id": device_id,
            "config": create_config_result,
        },
    )

    return create_config_result
