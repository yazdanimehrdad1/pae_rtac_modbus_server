"""Device points mapping and validation functions."""

from sqlalchemy import select

from db.connection import get_async_session_factory
from schemas.api_models import ConfigPoint, DevicePointData, DeviceWithConfigs
from schemas.db_models.orm_models import DevicePoint
from utils.exceptions import ConflictError, InternalError


def map_device_configs_to_device_points(
    points: list[ConfigPoint],
    device: DeviceWithConfigs,
    config_id: str
) -> list[DevicePointData]:
    """
    Map points into Device_Points rows.
    """
    device_points_list: list[DevicePointData] = []
    for point in points:
        base_name = point.name.lower()
        config_id = config_id
        data_type = point.data_type
        enum_detail = point.enum_detail or {}
        bitfield_detail = point.bitfield_detail or {}



        # The base point record (non-derived)
        device_points_list.append(
            {
                "site_id": device.site_id,
                "device_id": device.device_id,
                "config_id": config_id,
                "address": point.address,
                "name": base_name.lower(),
                "size": point.size,
                "data_type": data_type,
                "scale_factor": point.scale_factor,
                "unit": point.unit,
                "enum_detail": enum_detail,
                "bitfield_detail": bitfield_detail,
                "byte_order": point.byte_order,
                "is_derived": False,
            }
        )
    return device_points_list


async def validate_device_points_uniqueness(device_points_list: list[dict[str, object]], device: DeviceWithConfigs) -> None:
    """
    Validate that the points attempting to be created do not already exist
    or overlap with existing points for the device (based on address range).
    """

    device_id = device.device_id
    if not device_id:
        raise InternalError("Device ID missing from device data")

    session_factory = get_async_session_factory()
    async with session_factory() as session:
        # Get all existing points for this device from DB
        result = await session.execute(
            select(DevicePoint.address, DevicePoint.size, DevicePoint.name)
            .where(DevicePoint.device_id == device_id)
        )
        existing_points_db = result.all()

        for new_point in device_points_list:
            new_start = new_point.get("address")
            new_size = new_point.get("size", 1)
            new_name = new_point.get("name")

            if new_start is None:
                continue

            new_end = new_start + new_size - 1

            for ex_addr, ex_size, ex_name in existing_points_db:
                ex_start = ex_addr
                ex_end = ex_addr + ex_size - 1

                if new_start <= ex_end and new_end >= ex_start:
                    raise ConflictError(
                        f"Point '{new_name}' (address {new_start}-{new_end}) overlaps with existing point '{ex_name}' (address {ex_start}-{ex_end})",
                        payload={
                            "error_type": "Point address overlap",
                            "conflict": {
                                "new_point": {"name": new_name, "address": new_start, "size": new_size},
                                "existing_point": {"name": ex_name, "address": ex_start, "size": ex_size}
                            }
                        }
                    )

                if new_name == ex_name:
                    raise ConflictError(
                        f"Point named '{new_name}' already exists for this device",
                        payload={
                            "error_type": "Point name collision",
                            "conflict": {
                                "name": new_name,
                                "existing_address": ex_start
                            }
                        }
                    )
