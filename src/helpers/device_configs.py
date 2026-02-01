"""Device config helper functions for DB/cache coordination."""

from fastapi import HTTPException, status

from cache.cache import CacheService
from db.device_configs import create_config_for_device, get_configs_for_device
from db.devices import get_device_by_id
from logger import get_logger
from schemas.db_models.models import ConfigCreate, ConfigResponse

logger = get_logger(__name__)
cache_service = CacheService()

MAX_MODBUS_POLL_REGISTER_COUNT = 125

from helpers.device_points import (
    map_device_configs_to_device_points,
    create_device_points,
    validate_device_points_uniqueness
)


def set_point_defaults(points: list) -> None:
    """
    Set default values for point fields in-place.
    """
    for point in points:
        if isinstance(point, dict):
            if point.get("point_scale_factor") in ("", None):
                point["point_scale_factor"] = 1.0
            if point.get("point_unit") in ("", None):
                point["point_unit"] = "unit"
        else:
            if getattr(point, "point_scale_factor", None) in ("", None):
                point.point_scale_factor = 1.0
            if getattr(point, "point_unit", None) in ("", None):
                point.point_unit = "unit"


def _get_point_attr(point: object, key: str, default=None):
    if isinstance(point, dict):
        return point.get(key, default)
    if hasattr(point, key):
        return getattr(point, key, default)
    return default


def compute_poll_range(points: list) -> tuple[int, int, int]:
    """
    Compute min point address, max point end, and poll count.
    """
    addresses = [_get_point_attr(point, "point_address") for point in points]
    sizes = [_get_point_attr(point, "point_size", 1) for point in points]
    min_register_number = min(addresses)
    max_register_end = max(
        address + size - 1
        for address, size in zip(addresses, sizes)
    )
    poll_count = max_register_end - min_register_number + 1
    return min_register_number, max_register_end, poll_count


def validate_duplicate_points(points: list) -> None:
    """
    Validate no duplicate point addresses exist.
    """
    seen_addresses: dict[int, list[int]] = {}
    duplicates: list[dict[str, int | list[int]]] = []
    duplicate_register_addresses: list[int] = []
    for idx, point in enumerate(points):
        if isinstance(point, dict):
            point_data = point
        elif hasattr(point, "model_dump"):
            point_data = point.model_dump()
        else:
            point_data = vars(point)
        point_address = point_data.get("point_address")
        if point_address is None:
            continue
        seen_addresses.setdefault(point_address, []).append(idx)

    for address, indices in seen_addresses.items():
        if len(indices) > 1:
            duplicate_register_addresses.append(address)
            duplicates.append(
                {
                    "point_address": address,
                    "indices": indices,
                }
            )

    if duplicates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Duplicate point addresses",
                "message": "One or more points share the same point_address",
                "duplicate_register_addresses": duplicate_register_addresses,
                "duplicates": duplicates,
            },
        )


def validate_point_addresses(poll_start_index: int, points: list) -> None:
    """
    Validate point addresses are within allowed poll range.
    """
    validate_duplicate_points(points)
    max_address = poll_start_index + MAX_MODBUS_POLL_REGISTER_COUNT
    missing_fields: list[dict[str, str]] = []
    invalid_registers: list[dict[str, int | str]] = []
    for idx, point in enumerate(points):
        if isinstance(point, dict):
            point_data = point
        elif hasattr(point, "model_dump"):
            point_data = point.model_dump()
        else:
            point_data = vars(point)

        point_address = point_data.get("point_address")
        point_size = point_data.get("point_size")

        if point_address is None:
            missing_fields.append(
                {
                    "index": idx,
                    "field": "point_address",
                    "message": f"The 'points[{idx}].point_address' field is required",
                }
            )
            continue
        if point_size is None:
            missing_fields.append(
                {
                    "index": idx,
                    "field": "point_size",
                    "message": f"The 'points[{idx}].point_size' field is required",
                }
            )
            continue
        if not point_data.get("point_name"):
            missing_fields.append(
                {
                    "index": idx,
                    "field": "point_name",
                    "message": f"The 'points[{idx}].point_name' field is required",
                }
            )
            continue
        if not point_data.get("point_data_type"):
            missing_fields.append(
                {
                    "index": idx,
                    "field": "point_data_type",
                    "message": f"The 'points[{idx}].point_data_type' field is required",
                }
            )
            continue

        if point_address < poll_start_index:
            invalid_registers.append(
                {
                    "index": idx,
                    "point_address": point_address,
                    "error": (
                        f"point_address ({point_address}) is less than poll_start_index "
                        f"({poll_start_index})"
                    ),
                }
            )
            continue

        max_register_address = point_address + point_size - 1
        if max_register_address > max_address:
            invalid_registers.append(
                {
                    "index": idx,
                    "point_address": point_address,
                    "point_size": point_size,
                    "max_address": max_register_address,
                    "error": (
                        f"point_address ({point_address}) + size ({point_size}) - 1 = "
                        f"{max_register_address} exceeds poll_start_index + {MAX_MODBUS_POLL_REGISTER_COUNT} "
                        f"({max_address})"
                    ),
                }
            )

    if missing_fields:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "Missing required field",
                "message": "One or more points are missing required fields",
                "missing_fields": missing_fields,
            },
        )

    if invalid_registers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Invalid point addresses",
                "message": "One or more points have addresses outside the poll range",
                "invalid_registers": invalid_registers,
                "poll_start_index": poll_start_index,
                "max_address": max_address,
            },
        )


def validate_config_points_fields(points: list) -> None:
    """
    Validate the fields of the points in the config.
    """
    for point in points:
        if hasattr(point, "model_dump"):
            point = point.model_dump()
        elif hasattr(point, "dict"):
            point = point.dict()
        elif not isinstance(point, dict):
            point = vars(point)

        if not point.get("point_name"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Point name is required for point {point.get('point_address')}")
        if not point.get("point_address"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Point address is required for point {point.get('point_address')}")
        if not point.get("point_size"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Point size is required for point {point.get('point_address')}")
        if not point.get("point_data_type"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Point data type is required for point {point.get('point_address')}")
        if point.get("point_data_type") not in ["enum", "bitfield"] and not point.get("point_scale_factor"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Point scale factor is required")
        if point.get("point_data_type") not in ["enum", "bitfield"] and not point.get("point_unit"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Point unit is required")
        if point.get("point_data_type") == "bitfield" and not point.get("point_bitfield_detail"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Point bitfield detail is required for bitfield type")
        if point.get("point_data_type") == "enum" and not point.get("point_enum_detail"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Point enum detail is required for enum type")

def validate_poll_range_consistency(
    poll_count: int,
    min_register_number: int,
    max_register_end: int,
    points: list,
    payload_poll_start_index: int,
    payload_poll_count: int,
) -> None:
    """
    Validate poll count limits and consistency with payload values.
    """
    if poll_count > MAX_MODBUS_POLL_REGISTER_COUNT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Poll count exceeds maximum allowed",
                "message": "The number of points to poll exceeds the maximum allowed, consider adding multiple configs",
                "max_poll_count": MAX_MODBUS_POLL_REGISTER_COUNT,
                "poll_count": poll_count,
                "min_register_number": min_register_number,
                "max_register_end": max_register_end,
                "points": points,
            },
        )

    if min_register_number != payload_poll_start_index or poll_count != payload_poll_count:
        logger.warning(
            "Min point address or poll count does not match the config; continuing with payload values",
            extra={
                "min_register_number": min_register_number,
                "max_register_end": max_register_end,
                "computed_poll_count": poll_count,
                "payload_poll_start_index": payload_poll_start_index,
                "payload_poll_count": payload_poll_count,
            },
        )


async def create_config_cache_db(
    site_id: int,
    device_id: int,
    config: ConfigCreate
) -> ConfigResponse:
    """
    Create a config in the DB and update device cache.
    """
    # Basic validation (additional rules TBD)
    if config.site_id != site_id or config.device_id != device_id:
        raise ValueError("Path site_id/device_id must match body")

    validate_point_addresses_result =validate_point_addresses(config.poll_start_index, config.points)

    set_point_defaults(config.points)

    validate_config_points_fields_result = validate_config_points_fields(config.points)

    min_register_number, max_register_end, poll_count = compute_poll_range(
        config.points
    )

    validate_poll_range_consistency_result = validate_poll_range_consistency(
        poll_count=poll_count,
        min_register_number=min_register_number,
        max_register_end=max_register_end,
        points=config.points,
        payload_poll_start_index=config.poll_start_index,
        payload_poll_count=config.poll_count
    )

    # TODO: You have to make sure both device_points and device_configs are created. 
    # Maybe try to create device_points first, and if it fails, roll back the config creation

    # Validate point uniqueness against DB before creating config
    device = await get_device_by_id(device_id, site_id)
    
    if not device:
         raise ValueError(f"Device with id {device_id} not found")
         
    device_data = device.model_dump()
    
    device_points_list = map_device_configs_to_device_points(config.points, device_data)
    
    device_points_uniquness_result = await validate_device_points_uniqueness(device_points_list, device_data)

    create_config_result = await create_config_for_device(site_id, device_id, config)

    # device points are validated, now create them
    # TODO: if the points are faild to be created, then we need to make sure
    # the config is deleted and rolledback
    create_device_points_result = await create_device_points(device_points_list)

    cache_key = f"device:site:{site_id}:device_id:{device_id}"
    await cache_service.invalidate(cache_key)
    await cache_service.set(cache_key, create_config_result)
    logger.info(
        "Config created successfully",
        extra={
            "site_id": site_id,
            "device_id": device_id,
            "config": create_config_result,
        },
    )
    

    return create_config_result





