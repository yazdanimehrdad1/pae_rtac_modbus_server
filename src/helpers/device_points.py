from typing import Any
from fastapi import HTTPException, status
from sqlalchemy import select
from db.connection import get_async_session_factory
from schemas.db_models.orm_models import DevicePoint

def map_device_configs_to_device_points(points: list, device: Any) -> list[dict[str, object]]:
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


        if point_data.get("point_data_type") == "enum":
            for enum_name, enum_value in point_data.get("point_enum_detail", {}).items():
                device_points_list.append(
                    {
                        #id or point_id as a PK
                        "site_id": device.get("site_id"),
                        "device_id": device.get("device_id"),
                        "config_id": point_data.get("config_id"),
                        "address": point_data.get("point_address"),
                        "name": point_data.get("point_name") + "_" + enum_name,
                        "size": point_data.get("point_size"),
                        "data_type": point_data.get("point_data_type"),
                        "scale_factor": point_data.get("point_scale_factor"),
                        "unit": point_data.get("point_unit"),
                        "enum_value": enum_value,
                    }
                )
        elif point_data.get("point_data_type") == "bitfield":
            for bitfield_name, bitfield_value in point_data.get("point_bitfield_detail", {}).items():
                device_points_list.append(
                    {
                        #id or point_id as a PK
                        "site_id": device.get("site_id"),
                        "device_id": device.get("device_id"),
                        "config_id": point_data.get("config_id"),
                        "address": point_data.get("point_address"),
                        "name": point_data.get("point_name") + "_" + bitfield_name,
                        "size": point_data.get("point_size"),
                        "data_type": point_data.get("point_data_type"),
                        "scale_factor": point_data.get("point_scale_factor"),
                        "unit": point_data.get("point_unit"),
                        "bitfield_value": bitfield_value,
                    }
                )


        # TODO: consider using else, what I'm trying to do is to also get the rawvalues for bitfield/enums
        device_points_list.append(
            {
                # id or point_id as a PK
                "site_id": device.get("site_id"),
                "device_id": device.get("device_id"),
                "config_id": point_data.get("config_id"),
                "name": point_data.get("point_name"),
                "address": point_data.get("point_address"),
                "size": point_data.get("point_size"),
                "data_type": point_data.get("point_data_type"),
                "scale_factor": point_data.get("point_scale_factor"),
                "unit": point_data.get("point_unit"),
            }
        )
    return device_points_list


async def validate_device_points_uniqueness(device_points_list: list[dict[str, object]], device: dict[str, Any]) -> None:
    """
    Validate that the points attempting to be created do not already exist
    for the device (based on point address).
    """

    device_id = device.get("device_id")
    if not device_id:
        raise ValueError("Device ID missing from device data")

    session_factory = get_async_session_factory()
    async with session_factory() as session:
        addresses_to_check = {point.get("address") for point in device_points_list if point.get("address") is not None}
        
        # Query DB for ALL existing addresses for this device
        result = await session.execute(
            select(DevicePoint.address)
            .where(DevicePoint.device_id == device_id)
        )
        existing_addresses_db = set(result.scalars().all())
        
        # Check for intersection
        duplicates = addresses_to_check.intersection(existing_addresses_db)
        
        if duplicates:
            # Reconstruct detailed error list
            all_duplicates = []
            for addr in duplicates:
                all_duplicates.append(
                    {
                        "device_id": device_id,
                        "address": addr,
                        "error": f"Point with address {addr} already exists for device {device_id}"
                    }
                )
            
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "Duplicate point addresses found",
                    "message": "One or more points already exist for this device based on address.",
                    "duplicates": all_duplicates
                }
            )


async def create_device_points(device_points_list: list[dict[str, object]]) -> None:
    """
    Create device points in the database.
    """
    if not device_points_list:
        return

    session_factory = get_async_session_factory()
    async with session_factory() as session:
        # 1. Identify all unique device_ids involved (should be checking per device)
        # Assuming all points belong to the same device based on previous logic, but let's be safe
        # Group by device_id to batch checks
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
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "Duplicate points found",
                    "message": "One or more points already exist for this device.",
                    "existing_points": list(all_duplicates)
                }
            )

        # 2. If no duplicates, create all points
        new_points = [DevicePoint(**point) for point in device_points_list]
        session.add_all(new_points)
        await session.commit()
