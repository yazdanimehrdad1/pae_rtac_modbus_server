"""Device points CRUD operations."""

from sqlalchemy import select

from db.connection import get_async_session_factory
from schemas.db_models.orm_models import DevicePoint
from utils.exceptions import ConflictError, InternalError


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


async def get_device_points(device_id: int) -> list[DevicePoint]:
    """
    Get all points for a specific device.
    """
    session_factory = get_async_session_factory()
    async with session_factory() as session:
        result = await session.execute(
            select(DevicePoint)
            .where(DevicePoint.device_id == device_id)
            .order_by(DevicePoint.address.asc())
        )
        return list(result.scalars().all())
