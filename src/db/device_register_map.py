"""
Device register map database operations.

Handles CRUD operations for device_register_map table.
"""

from typing import Optional, Dict, Any
from sqlalchemy import select, update, delete
from sqlalchemy.exc import IntegrityError

from db.session import get_session
from schemas.db_models.orm_models import DeviceRegisterMap, Device
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
    async with get_session() as session:
        statement = select(DeviceRegisterMap).where(
            DeviceRegisterMap.device_id == device_id
        )
        
        result = await session.execute(statement)
        device_register_map = result.scalar_one_or_none()
        
        if device_register_map is None or device_register_map.register_map is None:
            return None
        
        # SQLAlchemy JSON type automatically handles dict conversion
        return device_register_map.register_map


async def get_register_map_by_device_name(device_name: str) -> Optional[Dict[str, Any]]:
    """
    Get register map for a device by device name.
    
    Args:
        device_name: Device name/identifier
        
    Returns:
        Register map dictionary if found, None otherwise
    """
    async with get_session() as session:
        statement = select(DeviceRegisterMap).join(
            Device, DeviceRegisterMap.device_id == Device.id
        ).where(Device.name == device_name)
        
        result = await session.execute(statement)
        device_register_map = result.scalar_one_or_none()
        
        if device_register_map is None or device_register_map.register_map is None:
            return None
        
        # SQLAlchemy JSON type automatically handles dict conversion
        return device_register_map.register_map

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
        ValueError: If register map already exists for this device or device_id doesn't exist
    """
    async with get_session() as session:
        try:
            # Create new DeviceRegisterMap instance
            device_register_map = DeviceRegisterMap(
                device_id=device_id,
                register_map=register_map
            )
            
            session.add(device_register_map)
            await session.commit()
            
            logger.info(f"Created register map for device ID {device_id}")
            return True
            
        except IntegrityError as e:
            await session.rollback()
            error_msg = str(e.orig)
            
            if "unique" in error_msg.lower() or "duplicate" in error_msg.lower():
                logger.warning(f"Register map already exists for device ID {device_id}")
                raise ValueError(f"Register map already exists for device ID {device_id}") from e
            elif "foreign key" in error_msg.lower() or "violates foreign key" in error_msg.lower():
                logger.warning(f"Device ID {device_id} does not exist")
                raise ValueError(f"Device ID {device_id} does not exist") from e
            else:
                logger.error(f"Database error creating register map: {e}")
                raise
        except Exception as e:
            await session.rollback()
            logger.error(f"Unexpected error creating register map: {e}", exc_info=True)
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
    async with get_session() as session:
        statement = update(DeviceRegisterMap).where(
            DeviceRegisterMap.device_id == device_id
        ).values(register_map=register_map)
        
        result = await session.execute(statement)
        await session.commit()
        
        updated = result.rowcount > 0
        
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
    async with get_session() as session:
        statement = delete(DeviceRegisterMap).where(
            DeviceRegisterMap.device_id == device_id
        )
        
        result = await session.execute(statement)
        await session.commit()
        
        deleted = result.rowcount > 0
        
        if deleted:
            logger.info(f"Deleted register map for device ID {device_id}")
        else:
            logger.warning(f"Register map not found for device ID {device_id}")
        
        return deleted

