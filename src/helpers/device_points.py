from typing import Any
from fastapi import HTTPException, status
from sqlalchemy import select
from db.connection import get_async_session_factory
from schemas.db_models.orm_models import DevicePoint
from utils.exceptions import ConflictError, NotFoundError, InternalError
from schemas.db_models.models import DeviceWithConfigs

def map_device_configs_to_device_points(points: list, device: DeviceWithConfigs) -> list[dict[str, object]]:
    """
    Map points into Device_Points rows.
    """
    device_points_list: list[dict[str, object]] = []
    for point in points:
        # TODO: make sure points are passed as a model and not dict when calling this function
        if isinstance(point, dict): # point is a dict
            point_data = point
        elif hasattr(point, "model_dump"): # point is a model
            point_data = point.model_dump()
        else:
            point_data = vars(point)

        base_name = point_data.get("name", "").lower()

        if point_data.get("data_type") == "enum":
            for enum_value, enum_name in point_data.get("enum_detail", {}).items():
                device_points_list.append(
                    {
                        "site_id": device.site_id,
                        "device_id": device.device_id,
                        "config_id": point_data.get("config_id"),
                        "address": point_data.get("address"),
                        "name": f"{base_name}_{enum_name}".lower(),
                        "size": point_data.get("size"),
                        "data_type": "single_enum",
                        "scale_factor": point_data.get("scale_factor"),
                        "unit": point_data.get("unit"),
                        "enum_value": enum_value,
                        "is_derived": True,
                    }
                )
        elif point_data.get("data_type") == "bitfield":
            for bitfield_value, bitfield_name in point_data.get("bitfield_detail", {}).items():
                device_points_list.append(
                    {
                        "site_id": device.site_id,
                        "device_id": device.device_id,
                        "config_id": point_data.get("config_id"),
                        "address": point_data.get("address"),
                        "name": f"{base_name}_{bitfield_name}".lower(),
                        "size": point_data.get("size"),
                        "data_type": "single_bit",
                        "scale_factor": point_data.get("scale_factor"),
                        "unit": point_data.get("unit"),
                        "bitfield_value": bitfield_value,
                        "is_derived": True,
                    }
                )


        # The base point record (non-derived)
        device_points_list.append(
            {
                "site_id": device.site_id,
                "device_id": device.device_id,
                "config_id": point_data.get("config_id"),
                "name": base_name.lower(),
                "address": point_data.get("address"),
                "size": point_data.get("size"),
                "data_type": point_data.get("data_type"),
                "scale_factor": point_data.get("scale_factor"),
                "unit": point_data.get("unit"),
                "enum_detail": point_data.get("enum_detail"),
                "bitfield_detail": point_data.get("bitfield_detail"),
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


async def create_device_points(device_points_list: list[dict[str, object]]) -> None:
    """
    Create device points in the database.
    """
    if not device_points_list:
        return
    try:
        session_factory = get_async_session_factory()
        async with session_factory() as session:
            # 1. Identify all unique device_ids involved (should be checking per device)
            # Assuming all points belong to the same device based on previous logic, but let's be safe
            # Group by device_id to batch checks
            points_by_device: dict[int, list[dict[str, object]]] = {}
            for point in device_points_list:
                device_id = point.get("device_id")
                if device_id:
                    points_by_device.setdefault(device_id, []).append(point)

            all_duplicates = []

            for device_id, points in points_by_device.items():
                names_to_check = {point["name"] for point in points if point.get("name")}
            
            # optimizations: fetch all existing names for this device
            result = await session.execute(
                select(DevicePoint.name)
                .where(DevicePoint.device_id == device_id)
                .where(DevicePoint.name.in_(names_to_check))
            )
            existing_names = set(result.scalars().all())
            
            if existing_names:
                all_duplicates.extend(
                    [name for name in names_to_check if name in existing_names]
                )

        if all_duplicates:
            raise ConflictError(
                "One or more points already exist for this device.",
                payload={
                    "error_type": "Duplicate points found",
                    "existing_points": list(all_duplicates)
                }
            )

        # 2. If no duplicates, create all points
        new_points = [DevicePoint(**point) for point in device_points_list]
        session.add_all(new_points)
        await session.commit()
        return True
    except Exception as e:
        raise InternalError(f"Failed to create device points: {str(e)}")


async def get_device_points(site_id: int, device_id: int) -> list[DevicePoint]:
    """
    Get all points for a specific site and device.
    """
    session_factory = get_async_session_factory()
    async with session_factory() as session:
        result = await session.execute(
            select(DevicePoint)
            .where(DevicePoint.site_id == site_id)
            .where(DevicePoint.device_id == device_id)
            .order_by(DevicePoint.address.asc())
        )
        return list(result.scalars().all())
