"""
Device register map database operations.

Handles CRUD operations for device_register_map table.
"""

from typing import Optional, Dict, Any
import asyncpg
import json

from db.connection import get_db_pool
from logger import get_logger

logger = get_logger(__name__)


async def get_register_map_by_device_id(device_id: int) -> Optional[Dict[str, Any]]:
    """
    Get register map for a device by device ID.
    
    Args:
        device_id: Device ID
        
    Returns:
        Register map dictionary if found, None otherwise
    """
    pool = await get_db_pool()
    
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT register_map
            FROM device_register_map
            WHERE device_id = $1
        """, device_id)
        
        if row is None or row['register_map'] is None:
            return None
        
        # asyncpg returns JSONB as dict automatically
        return row['register_map']


async def get_register_map_by_device_name(device_name: str) -> Optional[Dict[str, Any]]:
    """
    Get register map for a device by device name.
    
    Args:
        device_name: Device name/identifier
        
    Returns:
        Register map dictionary if found, None otherwise
    """
    pool = await get_db_pool()
    
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT drm.register_map
            FROM device_register_map drm
            JOIN devices d ON drm.device_id = d.id
            WHERE d.name = $1
        """, device_name)
        
        if row is None or row['register_map'] is None:
            return None
        
        # asyncpg returns JSONB as dict automatically
        return row['register_map']

# TODO: adjust this function to add json b based on the excel file
async def create_register_map(device_id: int, register_map: Dict[str, Any]) -> bool:
    """
    Create a new register map for a device.
    
    Args:
        device_id: Device ID
        register_map: Register map dictionary to store
        
    Returns:
        True if created successfully, False otherwise
        
    Raises:
        asyncpg.UniqueViolationError: If register map already exists for this device
        asyncpg.ForeignKeyViolationError: If device_id doesn't exist
    """
    pool = await get_db_pool()
    
    async with pool.acquire() as conn:
        try:
            # Convert register_map dict to JSON string for PostgreSQL JSONB
            register_map_json = json.dumps(register_map)
            
            await conn.execute("""
                INSERT INTO device_register_map (device_id, register_map)
                VALUES ($1, $2::jsonb)
            """, device_id, register_map_json)
            
            logger.info(f"Created register map for device ID {device_id}")
            return True
            
        except asyncpg.UniqueViolationError as e:
            logger.warning(f"Register map already exists for device ID {device_id}")
            raise ValueError(f"Register map already exists for device ID {device_id}") from e
        except asyncpg.ForeignKeyViolationError as e:
            logger.warning(f"Device ID {device_id} does not exist")
            raise ValueError(f"Device ID {device_id} does not exist") from e
        except asyncpg.PostgresError as e:
            logger.error(f"Database error creating register map: {e}")
            raise

# TODO: adjust this function to update json b based on the excel file
async def update_register_map(device_id: int, register_map: Dict[str, Any]) -> bool:
    """
    Update register map for a device.
    
    Args:
        device_id: Device ID
        register_map: Register map dictionary to store
        
    Returns:
        True if updated successfully, False if device_id not found
    """
    pool = await get_db_pool()
    
    async with pool.acquire() as conn:
        # Convert register_map dict to JSON string for PostgreSQL JSONB
        register_map_json = json.dumps(register_map)
        
        result = await conn.execute("""
            UPDATE device_register_map
            SET register_map = $1::jsonb, updated_at = NOW()
            WHERE device_id = $2
        """, register_map_json, device_id)
        
        updated = result == "UPDATE 1"
        
        if updated:
            logger.info(f"Updated register map for device ID {device_id}")
        else:
            logger.warning(f"Register map not found for device ID {device_id}")
        
        return updated


async def delete_register_map(device_id: int) -> bool:
    """
    Delete register map for a device.
    
    Args:
        device_id: Device ID
        
    Returns:
        True if register map was deleted, False if not found
    """
    pool = await get_db_pool()
    
    async with pool.acquire() as conn:
        result = await conn.execute("""
            DELETE FROM device_register_map
            WHERE device_id = $1
        """, device_id)
        
        deleted = result == "DELETE 1"
        
        if deleted:
            logger.info(f"Deleted register map for device ID {device_id}")
        else:
            logger.warning(f"Register map not found for device ID {device_id}")
        
        return deleted

