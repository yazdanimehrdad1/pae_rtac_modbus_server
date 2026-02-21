"""
Device point readings database operations.

Handles CRUD operations for device_points_readings time-series table.
"""

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, TypedDict
from sqlalchemy import select, and_, func as sql_func
from sqlalchemy.dialects.postgresql import insert

from db.session import get_session
from schemas.db_models.orm_models import DevicePointsReading, DevicePoint, Device
from helpers.devices import get_device_cache_db
from logger import get_logger

logger = get_logger(__name__)


class DevicePointReadingDict(TypedDict):
    timestamp: datetime
    device_point_id: int
    derived_value: Optional[float]


async def insert_register_reading(
    device_id: int,
    site_id: Optional[str],
    register_address: int,
    value: float,
    timestamp: Optional[datetime] = None,
    quality: str = 'good',
    register_name: Optional[str] = None,
    unit: Optional[str] = None,
    scale_factor: Optional[float] = None
) -> bool:
    """
    Insert a single register reading into the database.
    
    Args:
        device_id: Device ID
        site_id: Optional Site ID (unused)
        register_address: Modbus register address
        value: Register value (already converted to float/double)
        timestamp: Timestamp when reading was taken (defaults to now if None)
        quality: Data quality flag ('good', 'bad', 'uncertain', 'substituted')
        register_name: Register name (denormalized from register_map)
        unit: Unit of measurement (denormalized from register_map)
        scale_factor: Scale factor to apply to raw value (denormalized from register_map)
        
    Returns:
        True if inserted successfully, False otherwise
        
    Raises:
        ValueError: If site doesn't exist or device doesn't belong to site
        Exception: For database errors
    """
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)
    
    try:
        async with get_session() as session:
            # Validate that device exists
            device_result = await session.execute(
                select(Device).where(Device.device_id == device_id)
            )
            device = device_result.scalar_one_or_none()
            if device is None:
                raise ValueError(f"Device with id '{device_id}' not found")
            # Use PostgreSQL-specific INSERT ... ON CONFLICT via insert().on_conflict_do_update()
            #TODO critical: I think the way we are inserting here is not correct, because we are putting all the readings in a single table,
            # so lets say for site1-device-1 and for site-2-device-1, the device_id is the same, but the site_id is different,
            # so we need to insert the readings into the correct table, based on the site_id
            # we need to create a new table for each site, and then insert the readings into the correct table
            # the table name should be register_readings_raw_site_id_device_id
            # the table should have the following columns: timestamp, register_address, value, quality, register_name, unit, scale_factor
            # the table should have the following primary key: timestamp, register_address
            # the table should have the following foreign key: device_id
            # the table should have the following index: timestamp, register_address
            # the table should have the following constraint: device_id must be unique for each site
            statement = insert(DevicePointsReading).values(
                timestamp=timestamp,
                device_id=device_id,
                register_address=register_address,
                value=value,
                quality=quality,
                register_name=register_name,
                unit=unit,
                scale_factor=scale_factor
            )
            
            statement = statement.on_conflict_do_update(
                index_elements=['device_point_id', 'timestamp'],
                set_=dict(
                    derived_value=statement.excluded.derived_value
                )
            )
            
            await session.execute(statement)
            await session.commit()
            
            logger.debug(f"Inserted reading: device_id={device_id}, register_address={register_address}, value={value}")
            return True
            
    except Exception as e:
        logger.error(f"Error inserting register reading: {e}", exc_info=True)
        return False


async def insert_register_readings_batch(
    site_id: Optional[str],
    device_id: int,
    points_readings_list: List[DevicePointsReading],
    timestamp_dt: datetime
) -> int:
    """
    Insert multiple register readings in a single batch operation.
    
    Args:
        site_id: Optional Site ID (unused)
        readings: List of reading dictionaries, each containing:
            - device_id (int)
            - register_address (int)
            - value (float)
            - timestamp (datetime)
            - quality (str, optional, default 'good')
            - register_name (str, optional)
            - unit (str, optional)
            - scale_factor (float, optional)
        
    Returns:
        Number of successfully inserted readings
        
    Raises:
        ValueError: If site doesn't exist or any device doesn't belong to site
        Exception: For database errors
    """
    if not points_readings_list:
        logger.debug("No readings to insert in batch")
        return 0
    
    try:
        async with get_session() as session:
            
            values = []
            for device_point_reading in points_readings_list:
                reading_site_id = device_point_reading.site_id if device_point_reading.site_id is not None else site_id
                reading_device_id = device_point_reading.device_id if device_point_reading.device_id is not None else device_id

                values.append({
                    'site_id': reading_site_id,
                    'device_id': reading_device_id,
                    'device_point_id': device_point_reading.device_point_id,
                    'timestamp': device_point_reading.timestamp,
                    'derived_value': device_point_reading.derived_value
                })
            
            # Build batch INSERT query with ON CONFLICT
            # TODO: critical: we need to insert the readings into the correct table, based on the site_id
            # we need to create a new table for each site, and then insert the readings into the correct table
            # the table name should be register_readings_raw_site_id_device_id
            # the table should have the following columns: timestamp, device_point_id, derived_value
            # the table should have the following primary key: timestamp, device_point_id
            # the table should have the following foreign key: device_point_id
            # the table should have the following index: device_point_id, timestamp
            # the table should have the following constraint: device_id must be unique for each site
            statement = insert(DevicePointsReading).values(values)
            
            statement = statement.on_conflict_do_update(
                index_elements=['device_point_id', 'timestamp'],
                set_=dict(
                    derived_value=statement.excluded.derived_value
                )
            )
            
            await session.execute(statement)
            await session.commit()
            
            inserted_count = len(values)
            logger.debug(f"Batch inserted {inserted_count} register readings")
            
            return inserted_count
            
    except Exception as e:
        logger.error(f"Error in batch insert: {e}", exc_info=True)
        # Return 0 on unexpected errors
        return 0

async def get_all_readings(
    site_id: Optional[str] = None,
    device_id: Optional[int] = None,
    register_address: Optional[int] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None
) -> List[DevicePointReadingDict]:
    """
    Get all register readings with optional filters.
    
    Args:
        site_id: Optional Site ID (unused)
        device_id: Optional filter by device ID
        register_address: Optional filter by register address
        start_time: Optional start of time range (inclusive)
        end_time: Optional end of time range (inclusive)
        limit: Optional maximum number of readings to return
        offset: Optional number of readings to skip (for pagination)
        
    Returns:
        List of reading dictionaries, ordered by timestamp descending (newest first)
        
    Raises:
        ValueError: If device doesn't exist
    """
    try:
        async with get_session() as session:
            if device_id is not None:
                device_result = await session.execute(
                    select(Device).where(Device.device_id == device_id)
                )
                device = device_result.scalar_one_or_none()
                if device is None:
                    raise ValueError(f"Device with id '{device_id}' not found")

            # Build query with filters
            statement = (
                select(
                    DevicePointsReading.timestamp,
                    DevicePointsReading.derived_value,
                    DevicePointsReading.device_point_id
                )
                .join(DevicePoint, DevicePointsReading.device_point_id == DevicePoint.id)
            )

            conditions = []
            if device_id is not None:
                conditions.append(DevicePointsReading.device_id == device_id)
            if site_id is not None:
                conditions.append(DevicePointsReading.site_id == site_id)
            if register_address is not None:
                conditions.append(DevicePoint.address == register_address)
            if start_time is not None:
                conditions.append(DevicePointsReading.timestamp >= start_time)
            if end_time is not None:
                conditions.append(DevicePointsReading.timestamp <= end_time)

            if conditions:
                statement = statement.where(and_(*conditions))

            # Order by timestamp descending (newest first)
            statement = statement.order_by(DevicePointsReading.timestamp.desc())

            # Add LIMIT and OFFSET if provided
            if limit is not None:
                statement = statement.limit(limit)
            if offset is not None:
                statement = statement.offset(offset)

            result = await session.execute(statement)
            readings = result.all()

            return [
                {
                    'timestamp': reading.timestamp,
                    'device_point_id': reading.device_point_id,
                    'derived_value': reading.derived_value
                }
                for reading in readings
            ]
    except Exception as e:
        logger.error("Error fetching register readings: %s", e, exc_info=True)
        raise


async def get_latest_reading(
    device_id: int,
    site_id: Optional[str],
    register_address: int
) -> Optional[Dict[str, Any]]:
    """
    Get the latest reading for a specific register.
    
    Args:
        device_id: Device ID
        site_id: Optional Site ID (unused)
        register_address: Register address
        
    Returns:
        Dictionary with reading data if found, None otherwise
        
    Raises:
        ValueError: If device doesn't exist
    """
    async with get_session() as session:
        device_result = await session.execute(
            select(Device).where(Device.device_id == device_id)
        )
        device = device_result.scalar_one_or_none()
        if device is None:
            raise ValueError(f"Device with id '{device_id}' not found")
        
        rank_subquery = (
            select(
                DevicePointsReading.device_point_id,
                DevicePointsReading.timestamp,
                DevicePointsReading.derived_value,
                sql_func.row_number().over(
                    partition_by=DevicePointsReading.device_point_id,
                    order_by=DevicePointsReading.timestamp.desc()
                ).label('rn')
            )
            .where(
                and_(
                    DevicePointsReading.device_id == device_id,
                    DevicePointsReading.site_id == site_id
                )
            )
        )

        ranked = rank_subquery.subquery()

        statement = (
            select(
                ranked.c.timestamp,
                ranked.c.derived_value,
                DevicePoint.id.label('device_point_id'),
                DevicePoint.address,
                DevicePoint.name,
                DevicePoint.data_type,
                DevicePoint.unit,
                DevicePoint.scale_factor,
                DevicePoint.is_derived,
            )
            .join(ranked, ranked.c.device_point_id == DevicePoint.id)
            .where(
                and_(
                    ranked.c.rn == 1,
                    DevicePoint.device_id == device_id,
                    DevicePoint.site_id == site_id,
                    DevicePoint.address == register_address
                )
            )
            .limit(1)
        )

        result = await session.execute(statement)
        row = result.one_or_none()

        if row is None:
            return None

        return {
            'timestamp': row.timestamp,
            'device_id': device_id,
            'site_id': site_id,
            'device_point_id': row.device_point_id,
            'register_address': row.address,
            'name': row.name,
            'data_type': row.data_type,
            'unit': row.unit,
            'scale_factor': row.scale_factor,
            'is_derived': row.is_derived,
            'derived_value': row.derived_value
        }


async def get_latest_readings_for_device(
    device_id: int,
    site_id: Optional[str],
    register_addresses: Optional[List[int]] = None
) -> List[Dict[str, Any]]:
    """
    Get latest readings for all registers (or specific registers) of a device.
    
    Args:
        device_id: Device ID
        site_id: Optional Site ID (unused)
        register_addresses: Optional list of specific register addresses.
                          If None, returns latest for all registers of the device.
        
    Returns:
        List of latest reading dictionaries, one per register
        
    Raises:
        ValueError: If device doesn't exist
    """
    async with get_session() as session:
        device_result = await session.execute(
            select(Device).where(Device.device_id == device_id)
        )
        device = device_result.scalar_one_or_none()
        if device is None:
            raise ValueError(f"Device with id '{device_id}' not found")
        
        # Use window function to rank readings by timestamp per device_point_id
        rank_subquery = (
            select(
                DevicePointsReading.device_point_id,
                DevicePointsReading.timestamp,
                DevicePointsReading.derived_value,
                sql_func.row_number().over(
                    partition_by=DevicePointsReading.device_point_id,
                    order_by=DevicePointsReading.timestamp.desc()
                ).label('rn')
            )
            .where(
                and_(
                    DevicePointsReading.device_id == device_id,
                    DevicePointsReading.site_id == site_id
                )
            )
        )

        ranked = rank_subquery.subquery()

        statement = (
            select(
                ranked.c.timestamp,
                ranked.c.derived_value,
                DevicePoint.id.label('device_point_id'),
                DevicePoint.address,
                DevicePoint.name,
                DevicePoint.data_type,
                DevicePoint.unit,
                DevicePoint.scale_factor,
                DevicePoint.is_derived,
            )
            .join(ranked, ranked.c.device_point_id == DevicePoint.id)
            .where(
                and_(
                    ranked.c.rn == 1,
                    DevicePoint.device_id == device_id,
                    DevicePoint.site_id == site_id
                )
            )
        )

        if register_addresses:
            statement = statement.where(DevicePoint.address.in_(register_addresses))

        result = await session.execute(statement)
        rows = result.all()

        return [
            {
                'device_point_id': row.device_point_id,
                'register_address': row.address,
                'name': row.name,
                'data_type': row.data_type,
                'unit': row.unit,
                'scale_factor': row.scale_factor,
                'is_derived': row.is_derived,
                'timestamp': row.timestamp,
                'derived_value': row.derived_value
            }
            for row in rows
        ]


async def get_latest_readings_for_device_n(
    device_id: int,
    site_id: Optional[str],
    latest_n: int,
    register_addresses: Optional[List[int]] = None
) -> List[Dict[str, Any]]:
    """
    Get latest N readings per register (or specific registers) of a device.

    Args:
        device_id: Device ID
        site_id: Optional Site ID (unused)
        latest_n: Number of latest readings per point to return
        register_addresses: Optional list of specific register addresses.
                          If None, returns latest for all registers of the device.

    Returns:
        List of latest reading dictionaries, one per register reading

    Raises:
        ValueError: If device doesn't exist
    """
    async with get_session() as session:
        device = await get_device_cache_db(site_id, device_id)
        if device is None:
            raise ValueError(f"Device with id '{device_id}' not found")

        rank_subquery = (
            select(
                DevicePointsReading.device_point_id,
                DevicePointsReading.timestamp,
                DevicePointsReading.derived_value,
                sql_func.row_number().over(
                    partition_by=DevicePointsReading.device_point_id,
                    order_by=DevicePointsReading.timestamp.desc()
                ).label('rn')
            )
            .where(
                and_(
                    DevicePointsReading.device_id == device_id,
                    DevicePointsReading.site_id == site_id
                )
            )
        )

        ranked = rank_subquery.subquery()

        statement = (
            select(
                ranked.c.timestamp,
                ranked.c.derived_value,
                DevicePoint.id.label('device_point_id'),
                DevicePoint.address,
                DevicePoint.name,
                DevicePoint.data_type,
                DevicePoint.unit,
                DevicePoint.scale_factor,
                DevicePoint.is_derived,
            )
            .join(ranked, ranked.c.device_point_id == DevicePoint.id)
            .where(
                and_(
                    ranked.c.rn <= latest_n,
                    DevicePoint.device_id == device_id,
                    DevicePoint.site_id == site_id
                )
            )
        )

        if register_addresses:
            statement = statement.where(DevicePoint.address.in_(register_addresses))
        statement = statement.order_by(
            DevicePoint.id,
            ranked.c.timestamp.desc()
        )

        result = await session.execute(statement)
        rows = result.all()

        return [
            {
                'device_point_id': row.device_point_id,
                'register_address': row.address,
                'name': row.name,
                'data_type': row.data_type,
                'unit': row.unit,
                'scale_factor': row.scale_factor,
                'is_derived': row.is_derived,
                'timestamp': row.timestamp,
                'derived_value': row.derived_value
            }
            for row in rows
        ]
