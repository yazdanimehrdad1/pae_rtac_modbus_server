"""DB queries for device_points_readings table, keyed by device_point_id."""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import select, and_, func as sql_func

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

    Always returns ALL device points for the device (LEFT JOIN), so points that
    have never been polled appear with timestamp=None and derived_value=None.
    If point_ids is provided, only those points are returned.
    """
    async with get_session() as session:
        point_conditions = []
        if point_ids:
            point_conditions.append(DevicePoint.id.in_(point_ids))
        if device_id is not None:
            point_conditions.append(DevicePoint.device_id == device_id)
        if site_id is not None:
            point_conditions.append(DevicePoint.site_id == site_id)

        statement = (
            select(
                DevicePoint.id.label("device_point_id"),
                DevicePoint.address,
                DevicePoint.name,
                DevicePoint.data_type,
                DevicePoint.size,
                DevicePoint.unit,
                DevicePoint.scale_factor,
                DevicePoint.bitfield_detail,
                DevicePoint.enum_detail,
                DevicePointsReading.timestamp,
                DevicePointsReading.derived_value,
            )
            .outerjoin(DevicePointsReading, DevicePoint.id == DevicePointsReading.device_point_id)
            .where(and_(*point_conditions) if point_conditions else True)
            .distinct(DevicePoint.id)
            .order_by(DevicePoint.id, DevicePointsReading.timestamp.desc())
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

        rank_subq = (
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
                DevicePoint.bitfield_detail,
                DevicePoint.enum_detail,
                sql_func.row_number().over(
                    partition_by=DevicePointsReading.device_point_id,
                    order_by=DevicePointsReading.timestamp.asc(),
                ).label("rn"),
            )
            .join(DevicePoint, DevicePointsReading.device_point_id == DevicePoint.id)
            .where(and_(*conditions) if conditions else True)
        ).subquery()

        statement = (
            select(rank_subq)
            .where(rank_subq.c.rn <= limit)
            .order_by(rank_subq.c.device_point_id, rank_subq.c.timestamp.asc())
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
                "bitfield_detail": row.bitfield_detail,
                "enum_detail": row.enum_detail,
            }
            for row in result.all()
        ]
