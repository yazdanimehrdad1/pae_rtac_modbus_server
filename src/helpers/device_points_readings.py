"""DB queries for device_points_readings table, keyed by device_point_id."""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import select, and_

from db.session import get_session
from schemas.db_models.orm_models import DevicePointsReading, DevicePoint
from db.register_readings import LatestDevicePointReadingDict, TimeSeriesDevicePointReadingDict
from logger import get_logger

logger = get_logger(__name__)


async def get_latest_readings_by_point_ids(
    point_ids: List[int],
    site_id: Optional[int] = None,
    device_id: Optional[int] = None,
) -> List[LatestDevicePointReadingDict]:
    """
    Get the single latest reading per point.

    If point_ids is empty, returns latest for all points belonging to device_id/site_id.
    """
    async with get_session() as session:
        conditions = []
        if point_ids:
            conditions.append(DevicePointsReading.device_point_id.in_(point_ids))
        if device_id is not None:
            conditions.append(DevicePointsReading.device_id == device_id)
        if site_id is not None:
            conditions.append(DevicePointsReading.site_id == site_id)

        statement = (
            select(
                DevicePointsReading.timestamp,
                DevicePointsReading.derived_value,
                DevicePoint.id.label("device_point_id"),
                DevicePoint.address,
                DevicePoint.name,
                DevicePoint.data_type,
                DevicePoint.size,
                DevicePoint.unit,
                DevicePoint.scale_factor,
                DevicePoint.is_derived,
                DevicePoint.bitfield_detail,
                DevicePoint.enum_detail,
            )
            .join(DevicePoint, DevicePointsReading.device_point_id == DevicePoint.id)
            .where(and_(*conditions) if conditions else True)
            .distinct(DevicePointsReading.device_point_id)
            .order_by(
                DevicePointsReading.device_point_id,
                DevicePointsReading.timestamp.desc(),
            )
        )
        result = await session.execute(statement)
        return [
            {
                "device_point_id": row.device_point_id,
                "register_address": row.address,
                "name": row.name,
                "data_type": row.data_type,
                "size": row.size,
                "unit": row.unit,
                "scale_factor": row.scale_factor,
                "is_derived": row.is_derived,
                "timestamp": row.timestamp,
                "derived_value": row.derived_value,
                "bitfield_detail": row.bitfield_detail,
                "enum_detail": row.enum_detail,
            }
            for row in result.all()
        ]


async def get_timeseries_by_point_ids(
    point_ids: List[int],
    site_id: Optional[int] = None,
    device_id: Optional[int] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = 1000,
) -> List[TimeSeriesDevicePointReadingDict]:
    """
    Get time-series readings per point, ordered by (device_point_id, timestamp ASC).

    If point_ids is empty, returns readings for all points belonging to device_id/site_id.
    """
    async with get_session() as session:
        conditions = []
        if point_ids:
            conditions.append(DevicePointsReading.device_point_id.in_(point_ids))
        if device_id is not None:
            conditions.append(DevicePointsReading.device_id == device_id)
        if site_id is not None:
            conditions.append(DevicePointsReading.site_id == site_id)
        if start_time is not None:
            conditions.append(DevicePointsReading.timestamp >= start_time)
        if end_time is not None:
            conditions.append(DevicePointsReading.timestamp <= end_time)

        statement = (
            select(
                DevicePointsReading.timestamp,
                DevicePointsReading.derived_value,
                DevicePoint.id.label("device_point_id"),
                DevicePoint.address,
                DevicePoint.name,
                DevicePoint.data_type,
                DevicePoint.size,
                DevicePoint.unit,
                DevicePoint.scale_factor,
                DevicePoint.is_derived,
                DevicePoint.bitfield_detail,
                DevicePoint.enum_detail,
            )
            .join(DevicePoint, DevicePointsReading.device_point_id == DevicePoint.id)
            .where(and_(*conditions) if conditions else True)
            .order_by(
                DevicePointsReading.device_point_id,
                DevicePointsReading.timestamp.asc(),
            )
            .limit(limit)
        )
        result = await session.execute(statement)
        return [
            {
                "timestamp": row.timestamp,
                "derived_value": row.derived_value,
                "device_point_id": row.device_point_id,
                "register_address": row.address,
                "name": row.name,
                "data_type": row.data_type,
                "size": row.size,
                "unit": row.unit,
                "scale_factor": row.scale_factor,
                "is_derived": row.is_derived,
                "bitfield_detail": row.bitfield_detail,
                "enum_detail": row.enum_detail,
            }
            for row in result.all()
        ]
