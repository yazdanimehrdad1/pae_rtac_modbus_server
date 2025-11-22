"""
Register readings database operations.

Handles CRUD operations for register_readings time-series table.
"""

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
import asyncpg

from db.connection import get_db_pool
from logger import get_logger

logger = get_logger(__name__)


async def insert_register_reading(
    device_id: int,
    register_address: int,
    value: float,
    timestamp: Optional[datetime] = None,
    quality: str = 'good',
    register_name: Optional[str] = None,
    unit: Optional[str] = None
) -> bool:
    """
    Insert a single register reading into the database.
    
    Args:
        device_id: Device ID
        register_address: Modbus register address
        value: Register value (already converted to float/double)
        timestamp: Timestamp when reading was taken (defaults to now if None)
        quality: Data quality flag ('good', 'bad', 'uncertain', 'substituted')
        register_name: Register name (denormalized from register_map)
        unit: Unit of measurement (denormalized from register_map)
        
    Returns:
        True if inserted successfully, False otherwise
        
    Raises:
        asyncpg.PostgresError: For database errors
    """
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)
    
    pool = await get_db_pool()
    
    try:
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO register_readings (
                    timestamp, device_id, register_address, value,
                    quality, register_name, unit
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (timestamp, device_id, register_address) 
                DO UPDATE SET
                    value = EXCLUDED.value,
                    quality = EXCLUDED.quality,
                    register_name = EXCLUDED.register_name,
                    unit = EXCLUDED.unit
            """, timestamp, device_id, register_address, value, quality, register_name, unit)
            
            logger.debug(f"Inserted reading: device_id={device_id}, register_address={register_address}, value={value}")
            return True
            
    except asyncpg.PostgresError as e:
        logger.error(f"Database error inserting register reading: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error inserting register reading: {e}", exc_info=True)
        return False


async def insert_register_readings_batch(
    readings: List[Dict[str, Any]]
) -> int:
    """
    Insert multiple register readings in a single batch operation.
    
    Args:
        readings: List of reading dictionaries, each containing:
            - device_id (int)
            - register_address (int)
            - value (float)
            - timestamp (datetime)
            - quality (str, optional, default 'good')
            - register_name (str, optional)
            - unit (str, optional)
        
    Returns:
        Number of successfully inserted readings
        
    Raises:
        asyncpg.PostgresError: For database errors
    """
    if not readings:
        logger.debug("No readings to insert in batch")
        return 0
    
    pool = await get_db_pool()
    
    try:
        async with pool.acquire() as conn:
            # Prepare values for batch insert
            values = []
            for reading in readings:
                timestamp = reading.get('timestamp')
                if timestamp is None:
                    timestamp = datetime.now(timezone.utc)
                
                values.append((
                    timestamp,
                    reading['device_id'],
                    reading['register_address'],
                    float(reading['value']),  # Ensure it's a float
                    reading.get('quality', 'good'),
                    reading.get('register_name'),
                    reading.get('unit')
                ))
            
            # Build batch INSERT query
            # Using INSERT ... VALUES with ON CONFLICT for idempotency
            query = """
                INSERT INTO register_readings (
                    timestamp, device_id, register_address, value,
                    quality, register_name, unit
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (timestamp, device_id, register_address) 
                DO UPDATE SET
                    value = EXCLUDED.value,
                    quality = EXCLUDED.quality,
                    register_name = EXCLUDED.register_name,
                    unit = EXCLUDED.unit
            """
            
            # Execute batch insert
            result = await conn.executemany(query, values)
            
            # result is a string like "INSERT 0 5" - extract the number
            inserted_count = len(values)
            logger.debug(f"Batch inserted {inserted_count} register readings")
            
            return inserted_count
            
    except asyncpg.PostgresError as e:
        logger.error(f"Database error in batch insert: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in batch insert: {e}", exc_info=True)
        # Return 0 on unexpected errors
        return 0

async def get_all_readings(
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
        device_id: Optional filter by device ID
        register_address: Optional filter by register address
        start_time: Optional start of time range (inclusive)
        end_time: Optional end of time range (inclusive)
        limit: Optional maximum number of readings to return
        offset: Optional number of readings to skip (for pagination)
        
    Returns:
        List of reading dictionaries, ordered by timestamp descending (newest first)
    """
    pool = await get_db_pool()
    
    async with pool.acquire() as conn:
        # Build query dynamically based on filters
        conditions = []
        params = []
        param_index = 1
        
        if device_id is not None:
            conditions.append(f"device_id = ${param_index}")
            params.append(device_id)
            param_index += 1
        
        if register_address is not None:
            conditions.append(f"register_address = ${param_index}")
            params.append(register_address)
            param_index += 1
        
        if start_time is not None:
            conditions.append(f"timestamp >= ${param_index}")
            params.append(start_time)
            param_index += 1
        
        if end_time is not None:
            conditions.append(f"timestamp <= ${param_index}")
            params.append(end_time)
            param_index += 1
        
        # Build WHERE clause
        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)
        
        # Build query
        query = f"""
            SELECT 
                timestamp, device_id, register_address, value,
                quality, register_name, unit
            FROM register_readings
            {where_clause}
            ORDER BY timestamp DESC
        """
        
        # Add LIMIT and OFFSET if provided
        if limit is not None:
            query += f" LIMIT ${param_index}"
            params.append(limit)
            param_index += 1
        
        if offset is not None:
            query += f" OFFSET ${param_index}"
            params.append(offset)
        
        rows = await conn.fetch(query, *params)
        
        return [
            {
                'timestamp': row['timestamp'],
                'device_id': row['device_id'],
                'register_address': row['register_address'],
                'value': row['value'],
                'quality': row['quality'],
                'register_name': row['register_name'],
                'unit': row['unit']
            }
            for row in rows
        ]


async def get_latest_reading(
    device_id: int,
    register_address: int
) -> Optional[Dict[str, Any]]:
    """
    Get the latest reading for a specific register.
    
    Args:
        device_id: Device ID
        register_address: Register address
        
    Returns:
        Dictionary with reading data if found, None otherwise
    """
    pool = await get_db_pool()
    
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT 
                timestamp, device_id, register_address, value,
                quality, register_name, unit
            FROM register_readings
            WHERE device_id = $1 AND register_address = $2
            ORDER BY timestamp DESC
            LIMIT 1
        """, device_id, register_address)
        
        if row is None:
            return None
        
        return {
            'timestamp': row['timestamp'],
            'device_id': row['device_id'],
            'register_address': row['register_address'],
            'value': row['value'],
            'quality': row['quality'],
            'register_name': row['register_name'],
            'unit': row['unit']
        }


async def get_latest_readings_for_device(
    device_id: int,
    register_addresses: Optional[List[int]] = None
) -> List[Dict[str, Any]]:
    """
    Get latest readings for all registers (or specific registers) of a device.
    
    Args:
        device_id: Device ID
        register_addresses: Optional list of specific register addresses.
                          If None, returns latest for all registers of the device.
        
    Returns:
        List of latest reading dictionaries, one per register
    """
    pool = await get_db_pool()
    
    async with pool.acquire() as conn:
        if register_addresses:
            # Get latest for specific registers
            query = """
                SELECT DISTINCT ON (register_address)
                    timestamp, device_id, register_address, value,
                    quality, register_name, unit
                FROM register_readings
                WHERE device_id = $1
                AND register_address = ANY($2::int[])
                ORDER BY register_address, timestamp DESC
            """
            rows = await conn.fetch(query, device_id, register_addresses)
        else:
            # Get latest for all registers of the device
            query = """
                SELECT DISTINCT ON (register_address)
                    timestamp, device_id, register_address, value,
                    quality, register_name, unit
                FROM register_readings
                WHERE device_id = $1
                ORDER BY register_address, timestamp DESC
            """
            rows = await conn.fetch(query, device_id)
        
        return [
            {
                'timestamp': row['timestamp'],
                'device_id': row['device_id'],
                'register_address': row['register_address'],
                'value': row['value'],
                'quality': row['quality'],
                'register_name': row['register_name'],
                'unit': row['unit']
            }
            for row in rows
        ]

