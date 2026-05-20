"""Device points mapping and validation functions."""

from sqlalchemy import select

from db.connection import get_async_session_factory
from schemas.api_models import ConfigPoint, DevicePointData, DeviceWithConfigs
from schemas.db_models.orm_models import DevicePoint
from utils.exceptions import InternalError


def map_device_configs_to_device_points(
    points: list[ConfigPoint],
    device: DeviceWithConfigs,
    config_id: str
) -> list[DevicePointData]:
    """
    Map ConfigPoint objects into DevicePointData rows ready for DB insertion.
    """
    return [
        DevicePointData(
            category="NATIVE",
            site_id=device.site_id,
            device_id=device.device_id,
            config_id=config_id,
            address=point.address,
            name=point.name.lower(),
            size=point.size,
            data_type=point.data_type,
            scale_factor=point.scale_factor,
            unit=point.unit,
            enum_detail=point.enum_detail or {},
            bitfield_detail=point.bitfield_detail or {},
            byte_order=point.byte_order,
            is_derived=False,
        )
        for point in points
    ]


async def validate_device_points_uniqueness(device_points_list: list[DevicePointData], device: DeviceWithConfigs) -> list[str]:
    """
    Check that the points to be created do not overlap with or duplicate
    existing points for this device. Returns a list of error strings (empty = valid).
    """
    device_id = device.device_id
    if not device_id:
        raise InternalError("Device ID missing from device data")

    session_factory = get_async_session_factory()
    async with session_factory() as session:
        result = await session.execute(
            select(DevicePoint.address, DevicePoint.size, DevicePoint.name)
            .where(DevicePoint.device_id == device_id)
        )
        existing_points_db = result.all()

    errors: list[str] = []
    for new_point in device_points_list:
        new_end = new_point.address + new_point.size - 1

        for ex_addr, ex_size, ex_name in existing_points_db:
            ex_end = ex_addr + ex_size - 1

            if new_point.address <= ex_end and new_end >= ex_addr:
                errors.append(
                    f"Point '{new_point.name}' (address {new_point.address}-{new_end}) overlaps with existing point '{ex_name}' (address {ex_addr}-{ex_end})"
                )
            elif new_point.name == ex_name:
                errors.append(
                    f"Point named '{new_point.name}' already exists for this device"
                )

    return errors
