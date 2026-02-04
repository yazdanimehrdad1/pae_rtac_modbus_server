"""
Device point readings database operations.

Handles CRUD operations for device_points_readings time-series table.
"""

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from db.session import get_session
from schemas.db_models.orm_models import DevicePointsReading, DevicePoint, Device
from logger import get_logger

logger = get_logger(__name__)


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
            statement = insert(PointReading).values(
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
                index_elements=['timestamp', 'device_id', 'register_address'],
                set_=dict(
                    value=statement.excluded.value,
                    quality=statement.excluded.quality,
                    register_name=statement.excluded.register_name,
                    unit=statement.excluded.unit,
                    scale_factor=statement.excluded.scale_factor
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
    readings: List[Dict[str, Any]]
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
    if not readings:
        logger.debug("No readings to insert in batch")
        return 0
    
    try:
        async with get_session() as session:
            # Validate all devices exist and get unique device_ids
            device_ids = {reading['device_id'] for reading in readings}
            devices_result = await session.execute(
                select(Device).where(Device.device_id.in_(device_ids))
            )
            valid_devices = {device.device_id for device in devices_result.scalars().all()}
            
            # Check if all device_ids are valid
            invalid_devices = device_ids - valid_devices
            if invalid_devices:
                raise ValueError(
                    f"Device(s) {sorted(invalid_devices)} not found"
                )
            # Prepare values for batch insert
            values = []
            for reading in readings:
                timestamp = reading.get('timestamp')
                if timestamp is None:
                    timestamp = datetime.now(timezone.utc)
                
                values.append({
                    'timestamp': timestamp,
                    'device_id': reading['device_id'],
                    'register_address': reading['register_address'],
                    'value': float(reading['value']),  # Ensure it's a float
                    'quality': reading.get('quality', 'good'),
                    'register_name': reading.get('register_name'),
                    'unit': reading.get('unit'),
                    'scale_factor': reading.get('scale_factor')
                })
            
            # Build batch INSERT query with ON CONFLICT
            # TODO: critical: we need to insert the readings into the correct table, based on the site_id
            # we need to create a new table for each site, and then insert the readings into the correct table
            # the table name should be register_readings_raw_site_id_device_id
            # the table should have the following columns: timestamp, register_address, value, quality, register_name, unit, scale_factor
            # the table should have the following primary key: timestamp, register_address
            # the table should have the following foreign key: device_id
            # the table should have the following index: timestamp, register_address
            # the table should have the following constraint: device_id must be unique for each site
            statement = insert(PointReading).values(values)
            
            statement = statement.on_conflict_do_update(
                index_elements=['timestamp', 'device_id', 'register_address'],
                set_=dict(
                    value=statement.excluded.value,
                    quality=statement.excluded.quality,
                    register_name=statement.excluded.register_name,
                    unit=statement.excluded.unit,
                    scale_factor=statement.excluded.scale_factor
                )
            )
            
            result = await session.execute(statement)
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
) -> List[Dict[str, Any]]:
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
    async with get_session() as session:
        if device_id is not None:
            device_result = await session.execute(
                select(Device).where(Device.device_id == device_id)
            )
            device = device_result.scalar_one_or_none()
            if device is None:
                raise ValueError(f"Device with id '{device_id}' not found")
        
        # Build query with filters
        statement = select(PointReading)
        
        conditions = []
        if device_id is not None:
            conditions.append(PointReading.device_id == device_id)
        if register_address is not None:
            conditions.append(PointReading.register_address == register_address)
        if start_time is not None:
            conditions.append(PointReading.timestamp >= start_time)
        if end_time is not None:
            conditions.append(PointReading.timestamp <= end_time)
        
        if conditions:
            statement = statement.where(and_(*conditions))
        
        # Order by timestamp descending (newest first)
        statement = statement.order_by(PointReading.timestamp.desc())
        
        # Add LIMIT and OFFSET if provided
        if limit is not None:
            statement = statement.limit(limit)
        if offset is not None:
            statement = statement.offset(offset)
        
        result = await session.execute(statement)
        readings = result.scalars().all()
        
        return [
            {
                'timestamp': reading.timestamp,
                'device_id': reading.device_id,
                'register_address': reading.register_address,
                'value': reading.value,
                'quality': reading.quality,
                'register_name': reading.register_name,
                'unit': reading.unit
            }
            for reading in readings
        ]


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
        
        statement = select(PointReading).where(
            and_(
                PointReading.device_id == device_id,
                PointReading.register_address == register_address
            )
        ).order_by(PointReading.timestamp.desc()).limit(1)
        
        result = await session.execute(statement)
        reading = result.scalar_one_or_none()
        
        if reading is None:
            return None
        
        return {
            'timestamp': reading.timestamp,
            'device_id': reading.device_id,
            'register_address': reading.register_address,
            'value': reading.value,
            'quality': reading.quality,
            'register_name': reading.register_name,
            'unit': reading.unit
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
        
        # Use window function to get latest reading per register_address
        # This is equivalent to DISTINCT ON (register_address) ... ORDER BY register_address, timestamp DESC
        from sqlalchemy import func as sql_func
        
        # Use window function to rank readings by timestamp per register_address
        rank_subquery = (
            select(
                PointReading.timestamp,
                PointReading.register_address,
                PointReading.value,
                PointReading.quality,
                PointReading.register_name,
                PointReading.unit,
                PointReading.scale_factor,
                sql_func.row_number().over(
                    partition_by=PointReading.register_address,
                    order_by=PointReading.timestamp.desc()
                ).label('rn')
            )
            .where(PointReading.device_id == device_id)
        )
        
        # If register_addresses is provided, filter the subquery to only include the specified register addresses
        if register_addresses:
            rank_subquery = rank_subquery.where(
                PointReading.register_address.in_(register_addresses)
            )
        
        # Create subquery alias
        ranked = rank_subquery.subquery()
        
        # Select only rows where rn = 1 (latest per register_address)
        statement = (
            select(
                ranked.c.timestamp,
                ranked.c.register_address,
                ranked.c.value,
                ranked.c.quality,
                ranked.c.register_name,
                ranked.c.unit,
                ranked.c.scale_factor
            )
            .where(ranked.c.rn == 1)
        )
        
        result = await session.execute(statement)
        rows = result.all()
        
        return [
            {
                'timestamp': row.timestamp,
                'register_address': row.register_address,
                'value': row.value,
                'quality': row.quality,
                'register_name': row.register_name,
                'unit': row.unit,
                'scale': row.scale_factor  # Scale factor from database
            }
            for row in rows
        ]

