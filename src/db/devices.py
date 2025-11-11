"""
Device database operations.

Handles CRUD operations for devices table.
"""

from datetime import datetime
from typing import Optional
import asyncpg

from db.connection import get_db_pool
from schemas.db_models.models import DeviceCreate, DeviceUpdate, DeviceResponse
from logger import get_logger

logger = get_logger(__name__)


async def create_device(device: DeviceCreate) -> DeviceResponse:
    """
    Create a new device in the database.
    
    Args:
        device: Device creation data
        
    Returns:
        Created device with ID and timestamps
        
    Raises:
        asyncpg.UniqueViolationError: If device name already exists
        asyncpg.PostgresError: For other database errors
    """
    pool = await get_db_pool()
    
    async with pool.acquire() as conn:
        try:
            row = await conn.fetchrow("""
                INSERT INTO devices (name, host, port, unit_id, description)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id, name, host, port, unit_id, description, created_at, updated_at
            """, device.name, device.host, device.port, device.unit_id, device.description)
            
            logger.info(f"Created device: {device.name} (ID: {row['id']})")
            
            return DeviceResponse(
                id=row['id'],
                name=row['name'],
                host=row['host'],
                port=row['port'],
                unit_id=row['unit_id'],
                description=row['description'],
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )
            
        except asyncpg.UniqueViolationError as e:
            logger.warning(f"Device name '{device.name}' already exists")
            raise ValueError(f"Device with name '{device.name}' already exists") from e
        except asyncpg.PostgresError as e:
            logger.error(f"Database error creating device: {e}")
            raise


async def get_all_devices() -> list[DeviceResponse]:
    """
    Get all devices from the database.
    
    Returns:
        List of all devices, ordered by ID
    """
    pool = await get_db_pool()
    
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, name, host, port, unit_id, description, created_at, updated_at
            FROM devices
            ORDER BY id
        """)
        
        return [
            DeviceResponse(
                id=row['id'],
                name=row['name'],
                host=row['host'],
                port=row['port'],
                unit_id=row['unit_id'],
                description=row['description'],
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )
            for row in rows
        ]


async def get_device_by_id(device_id: int) -> Optional[DeviceResponse]:
    """
    Get a device by ID.
    
    Args:
        device_id: Device ID
        
    Returns:
        Device if found, None otherwise
    """
    pool = await get_db_pool()
    
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT id, name, host, port, unit_id, description, created_at, updated_at
            FROM devices
            WHERE id = $1
        """, device_id)
        
        if row is None:
            return None
        
        return DeviceResponse(
            id=row['id'],
            name=row['name'],
            host=row['host'],
            port=row['port'],
            unit_id=row['unit_id'],
            description=row['description'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )


async def update_device(device_id: int, device_update: DeviceUpdate) -> DeviceResponse:
    """
    Update a device in the database.
    
    Args:
        device_id: Device ID to update
        device_update: Device update data (only provided fields will be updated)
        
    Returns:
        Updated device with new timestamps
        
    Raises:
        ValueError: If device not found or name already exists
        asyncpg.PostgresError: For other database errors
    """
    pool = await get_db_pool()
    
    async with pool.acquire() as conn:
        # Check if device exists
        existing = await get_device_by_id(device_id)
        if existing is None:
            raise ValueError(f"Device with ID {device_id} not found")
        
        # Build dynamic UPDATE query based on provided fields
        update_fields = []
        values = []
        param_index = 1
        
        if device_update.name is not None:
            update_fields.append(f"name = ${param_index}")
            values.append(device_update.name)
            param_index += 1
        
        if device_update.host is not None:
            update_fields.append(f"host = ${param_index}")
            values.append(device_update.host)
            param_index += 1
        
        if device_update.port is not None:
            update_fields.append(f"port = ${param_index}")
            values.append(device_update.port)
            param_index += 1
        
        if device_update.unit_id is not None:
            update_fields.append(f"unit_id = ${param_index}")
            values.append(device_update.unit_id)
            param_index += 1
        
        if device_update.description is not None:
            update_fields.append(f"description = ${param_index}")
            values.append(device_update.description)
            param_index += 1
        
        # If no fields to update, return existing device
        if not update_fields:
            return existing
        
        # Always update updated_at timestamp
        update_fields.append("updated_at = NOW()")
        
        # Add device_id as last parameter for WHERE clause
        values.append(device_id)
        where_param = param_index
        
        query = f"""
            UPDATE devices
            SET {', '.join(update_fields)}
            WHERE id = ${where_param}
            RETURNING id, name, host, port, unit_id, description, created_at, updated_at
        """
        
        try:
            row = await conn.fetchrow(query, *values)
            
            logger.info(f"Updated device ID {device_id}")
            
            return DeviceResponse(
                id=row['id'],
                name=row['name'],
                host=row['host'],
                port=row['port'],
                unit_id=row['unit_id'],
                description=row['description'],
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )
            
        except asyncpg.UniqueViolationError as e:
            logger.warning(f"Device name already exists")
            raise ValueError("Device with this name already exists") from e
        except asyncpg.PostgresError as e:
            logger.error(f"Database error updating device: {e}")
            raise


async def delete_device(device_id: int) -> bool:
    """
    Delete a device from the database.
    
    Args:
        device_id: Device ID to delete
        
    Returns:
        True if device was deleted, False if not found
        
    Raises:
        asyncpg.PostgresError: For database errors
    """
    pool = await get_db_pool()
    
    async with pool.acquire() as conn:
        result = await conn.execute("""
            DELETE FROM devices
            WHERE id = $1
        """, device_id)
        
        deleted = result == "DELETE 1"
        
        if deleted:
            logger.info(f"Deleted device ID {device_id}")
        else:
            logger.warning(f"Device ID {device_id} not found for deletion")
        
        return deleted

