"""Device points CRUD operations."""

from sqlalchemy import select

from db.connection import get_async_session_factory
from schemas.api_models import DevicePointData
from schemas.db_models.orm_models import DevicePoint
from utils.exceptions import InternalError


async def create_device_points(device_points_list: list[DevicePointData]) -> bool:
    """
    Persist a list of DevicePointData to the database.
    Uniqueness is guaranteed by the caller (validate_device_points_uniqueness).
    """
    if not device_points_list:
        return True
    try:
        session_factory = get_async_session_factory()
        async with session_factory() as session:
            new_points = [DevicePoint(**point.model_dump()) for point in device_points_list]
            session.add_all(new_points)
            await session.commit()
        return True
    except Exception as e:
        raise InternalError(f"Failed to create device points: {str(e)}")


async def get_device_points(device_id: int, category: str | None = None) -> list[DevicePoint]:
    """
    Get all points for a specific device, optionally filtered by category.
    """
    session_factory = get_async_session_factory()
    async with session_factory() as session:
        query = (
            select(DevicePoint)
            .where(DevicePoint.device_id == device_id)
            .order_by(DevicePoint.address.asc())
        )
        if category is not None:
            query = query.where(DevicePoint.category == category.upper())
        result = await session.execute(query)
        return list(result.scalars().all())
