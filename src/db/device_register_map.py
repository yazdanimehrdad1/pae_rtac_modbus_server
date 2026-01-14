"""
Device register map database operations.

Handles CRUD operations for device_register_map table.
"""

from typing import Optional, Dict, Any
from sqlalchemy import select, update, delete
from sqlalchemy.exc import IntegrityError

from db.session import get_session
from schemas.db_models.orm_models import DeviceRegisterMap, Device, Site
from logger import get_logger

logger = get_logger(__name__)

# TODO: add cache to this function
async def get_register_map(device_id: int, site_id: str) -> Optional[Dict[str, Any]]:
    """
    Get register map for a device by device ID.
    
    Args:
        device_id: Device ID (database primary key)
        site_id: Site ID to validate that the device belongs to this site
        
    Returns:
        Register map dictionary if found, None otherwise
        
    Raises:
        ValueError: If site doesn't exist, device doesn't exist, or device doesn't belong to that site
    """
    async with get_session() as session:
        # Validate site_id - site must exist
        site_result = await session.execute(
            select(Site).where(Site.id == site_id)
        )
        site = site_result.scalar_one_or_none()
        if site is None:
            raise ValueError(f"Site with id '{site_id}' not found")
        
        # Query register map with join to Device, filtering by both device_id and site_id
        # This ensures the device exists and belongs to the specified site in a single query
        statement = (
            select(DeviceRegisterMap)
            .join(Device, DeviceRegisterMap.device_id == Device.id)
            .where(
                DeviceRegisterMap.device_id == device_id,
                Device.site_id == site_id
            )
        )
        
        result = await session.execute(statement)
        device_register_map = result.scalar_one_or_none()
        
        # Return None if register map not found or is empty
        if not device_register_map or not device_register_map.register_map:
            return None
        
        # SQLAlchemy JSON type automatically handles dict conversion
        return device_register_map.register_map




# TODO: adjust this function to add json b based on the excel file
async def create_register_map( site_id: str, device_id: int, register_map: Dict[str, Any]) -> bool:
    """
    Create a new register map for a device.
    
    Args:
        device_id: Device ID (database primary key)
        register_map: Register map dictionary to store
        site_id: Site ID (required) to validate that the device belongs to this site
        
    Returns:
        True if created successfully, False otherwise
        
    Raises:
        ValueError: If register map already exists for this device, device_id doesn't exist, 
                    or device doesn't belong to the specified site
    """
    async with get_session() as session:
        try:
            # Validate site_id - site must exist
            logger.debug(f"Validating site_id '{site_id}' for register map creation on device {device_id}")
            site_result = await session.execute(
                select(Site).where(Site.id == site_id)
            )
            site = site_result.scalar_one_or_none()
            if site is None:
                error_msg = f"Site with id '{site_id}' not found"
                logger.warning(f"{error_msg} when creating register map for device {device_id} on site {site_id}")
                raise ValueError(error_msg)
            logger.debug(f"Site '{site_id}' found: {site.name}")
            
            # Validate that device exists and belongs to the specified site (query by both device_id and site_id)
            logger.debug(f"Validating device_id {device_id} for register map creation in site '{site_id}'")
            device_result = await session.execute(
                select(Device).where(
                    Device.id == device_id,
                    Device.site_id == site_id
                )
            )
            device = device_result.scalar_one_or_none()
            
            if device is None:
                error_msg = f"Device with id '{device_id}' not found in site '{site_id}'"
                logger.warning(f"{error_msg} when creating register map")
                raise ValueError(error_msg)
            
            logger.debug(f"Device {device_id} found: name='{device.name}', site_id='{device.site_id}' - validation passed")
            
            # Check if register map already exists for this device
            existing_map_result = await session.execute(
                select(DeviceRegisterMap).where(DeviceRegisterMap.device_id == device_id)
            )
            existing_map = existing_map_result.scalar_one_or_none()
            
            if existing_map is not None:
                error_msg = f"Register map already exists for device ID {device_id}"
                logger.warning(error_msg)
                raise ValueError(error_msg)
            
            # Create new DeviceRegisterMap instance
            device_register_map = DeviceRegisterMap(
                device_id=device_id,
                register_map=register_map
            )
            
            session.add(device_register_map)
            await session.commit()
            
            logger.info(f"Created register map for device ID {device_id} on site {site_id}")
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
async def update_register_map(site_id: str, device_id: int, register_map: Dict[str, Any]) -> bool:
    """
    Update register map for a device.
    
    Args:
        site_id: Site ID to validate that the device belongs to this site
        device_id: Device ID (database primary key)
        register_map: Register map dictionary to store
        
    Returns:
        True if updated successfully, False if register map not found
        
    Raises:
        ValueError: If site doesn't exist, device doesn't exist in that site, or register map doesn't exist
    """
    async with get_session() as session:
        # Validate site_id - site must exist
        logger.debug(f"Validating site_id '{site_id}' for register map update on device {device_id}")
        site_result = await session.execute(
            select(Site).where(Site.id == site_id)
        )
        site = site_result.scalar_one_or_none()
        if site is None:
            error_msg = f"Site with id '{site_id}' not found"
            logger.warning(f"{error_msg} when updating register map for device {device_id}")
            raise ValueError(error_msg)
        logger.debug(f"Site '{site_id}' found: {site.name}")
        
        # Validate that device exists and belongs to the specified site (query by both device_id and site_id)
        logger.debug(f"Validating device_id {device_id} for register map update in site '{site_id}'")
        device_result = await session.execute(
            select(Device).where(
                Device.id == device_id,
                Device.site_id == site_id
            )
        )
        device = device_result.scalar_one_or_none()
        
        if device is None:
            error_msg = f"Device with id '{device_id}' not found in site '{site_id}'"
            logger.warning(f"{error_msg} when updating register map")
            raise ValueError(error_msg)
        
        logger.debug(f"Device {device_id} found: name='{device.name}', site_id='{device.site_id}' - validation passed")
        
        # Update register map (only if it exists)
        statement = update(DeviceRegisterMap).where(
            DeviceRegisterMap.device_id == device_id
        ).values(register_map=register_map)
        
        result = await session.execute(statement)
        await session.commit()
        
        updated = result.rowcount > 0
        
        if updated:
            logger.info(f"Updated register map for device ID {device_id} on site {site_id}")
        else:
            logger.warning(f"Register map not found for device ID {device_id} in site '{site_id}'")
        
        return updated


async def delete_register_map(site_id: str, device_id: int) -> bool:
    """
    Delete register map for a device.
    
    Args:
        site_id: Site ID to validate that the device belongs to this site
        device_id: Device ID (database primary key)
        
    Returns:
        True if register map was deleted, False if not found
        
    Raises:
        ValueError: If site doesn't exist, device doesn't exist in that site, or register map doesn't exist
    """
    async with get_session() as session:
        # Validate site_id - site must exist
        logger.debug(f"Validating site_id '{site_id}' for register map deletion on device {device_id}")
        site_result = await session.execute(
            select(Site).where(Site.id == site_id)
        )
        site = site_result.scalar_one_or_none()
        if site is None:
            error_msg = f"Site with id '{site_id}' not found"
            logger.warning(f"{error_msg} when deleting register map for device {device_id}")
            raise ValueError(error_msg)
        logger.debug(f"Site '{site_id}' found: {site.name}")
        
        # Validate that device exists and belongs to the specified site (query by both device_id and site_id)
        logger.debug(f"Validating device_id {device_id} for register map deletion in site '{site_id}'")
        device_result = await session.execute(
            select(Device).where(
                Device.id == device_id,
                Device.site_id == site_id
            )
        )
        device = device_result.scalar_one_or_none()
        
        if device is None:
            error_msg = f"Device with id '{device_id}' not found in site '{site_id}'"
            logger.warning(f"{error_msg} when deleting register map")
            raise ValueError(error_msg)
        
        logger.debug(f"Device {device_id} found: name='{device.name}', site_id='{device.site_id}' - validation passed")
        
        statement = delete(DeviceRegisterMap).where(
            DeviceRegisterMap.device_id == device_id
        )
        
        result = await session.execute(statement)
        await session.commit()
        
        deleted = result.rowcount > 0
        
        if deleted:
            logger.info(f"Deleted register map for device ID {device_id} on site {site_id}")
        else:
            logger.warning(f"Register map not found for device ID {device_id} in site '{site_id}'")
        
        return deleted



