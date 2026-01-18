"""
Device database operations.

Handles CRUD operations for devices table.
Uses SQLAlchemy 2.0+ async ORM.
"""

from typing import Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from db.connection import get_async_session_factory
from schemas.db_models.models import DeviceCreate, DeviceUpdate, DeviceResponse, DeviceListItem
from schemas.db_models.orm_models import Device, Site
from logger import get_logger

logger = get_logger(__name__)


DEVICE_ID_MIN = 10
DEVICE_ID_MAX = 99
DEVICE_ID_ATTEMPTS = 5


async def _generate_device_id(session: AsyncSession) -> int:
    result = await session.execute(select(Device.device_id))
    used_ids = {row[0] for row in result.all() if row[0] is not None}
    for candidate in range(DEVICE_ID_MIN, DEVICE_ID_MAX + 1):
        if candidate not in used_ids:
            return candidate
    raise ValueError("No available device_id values")


async def create_device(device: DeviceCreate, site_id: int) -> DeviceResponse:
    """
    Create a new device in the database.
    
    Args:
        device: Device creation data
    Returns:
        Created device with ID and timestamps
        
    Raises:
        ValueError: If device name or device_id already exists
        IntegrityError: For other database constraint violations
    """
    session_factory = get_async_session_factory()
    async with session_factory() as session:
        try:
            # Check if device name already exists
            existing_device_result = await session.execute(
                select(Device).where(Device.name == device.name)
            )
            existing_device = existing_device_result.scalar_one_or_none()
            if existing_device is not None:
                raise ValueError(f"Device with name '{device.name}' already exists")
            
            site_result = await session.execute(
                select(Site).where(Site.id == site_id)
            )
            site = site_result.scalar_one_or_none()
            if site is None:
                raise ValueError(f"Site with id '{site_id}' not found")
            
            device_id = await _generate_device_id(session)
            new_device = Device(
                device_id=device_id,
                name=device.name,
                host=device.host,
                port=device.port,
                server_id=device.server_id,
                description=device.description,
                main_type=device.main_type,
                sub_type=device.sub_type,
                poll_enabled=device.poll_enabled,
                configs=device.configs,
                site_id=site_id
            )
            
            # Add to session and flush to get the ID
            session.add(new_device)
            await session.flush()
            device_primary_key = new_device.id
            logger.info(f"Created device: {device.name} (ID: {device_primary_key})")
            
            await session.commit()
            
            result = await session.execute(
                select(Device).where(Device.id == device_primary_key)
            )
            created_device = result.scalar_one_or_none()
            
            if created_device is None:
                raise RuntimeError(f"Device with id {device_primary_key} not found after creation")
            
            return DeviceResponse(
                id=created_device.id,
                name=created_device.name,
                host=created_device.host,
                port=created_device.port,
                device_id=created_device.device_id,
                server_id=created_device.server_id,
                site_id=created_device.site_id,
                description=created_device.description,
                main_type=created_device.main_type,
                sub_type=created_device.sub_type,
                poll_enabled=created_device.poll_enabled if created_device.poll_enabled is not None else True,
                configs=created_device.configs or [],
                created_at=created_device.created_at,
                updated_at=created_device.updated_at
            )
            
        except IntegrityError as e:
            await session.rollback()
            # Check if it's a unique constraint violation
            error_text = str(e).lower()
            if "unique" in error_text or "duplicate" in error_text or "already exists" in error_text:
                if "device_id" in error_text:
                    logger.warning("Device device_id already exists")
                    raise ValueError("Failed to allocate unique device_id") from e
                logger.warning(f"Device name '{device.name}' already exists")
                raise ValueError(f"Device with name '{device.name}' already exists") from e
            else:
                logger.error(f"Database integrity error creating device: {e}")
                raise
        except Exception as e:
            await session.rollback()
            logger.error(f"Database error creating device: {e}")
            raise


async def get_all_devices(site_id: int) -> list[DeviceListItem]:
    """
    Get all devices from the database.
    
    Returns:
        List of all devices ordered by ID
    """
    session_factory = get_async_session_factory()
    async with session_factory() as session:
        result = await session.execute(
            select(Device).where(Device.site_id == site_id).order_by(Device.id)
        )
        devices = result.scalars().all()
        
        # Convert ORM models to Pydantic models
        device_list = []
        for device in devices:
            device_list.append(
                DeviceListItem(
                    id=device.id,
                    name=device.name,
                    host=device.host,
                    port=device.port,
                    device_id=device.device_id,
                    server_id=device.server_id,
                    site_id=device.site_id,
                    description=device.description,
                    main_type=device.main_type,
                    sub_type=device.sub_type,
                    poll_enabled=device.poll_enabled if device.poll_enabled is not None else True,
                    configs=device.configs or [],
                    created_at=device.created_at,
                    updated_at=device.updated_at
                )
            )
        return device_list


async def get_devices_by_site_id(site_id: int) -> list[DeviceListItem]:
    """Backward-compatible helper for scheduler jobs."""
    return await get_all_devices(site_id)


async def get_device_by_id(device_id: int, site_id: int) -> Optional[DeviceResponse]:
    """
    Get a device by primary key ID.
    
    Args:
        device_id: Device ID (database primary key)
        
    Returns:
        Device if found, None otherwise
    """
    session_factory = get_async_session_factory()
    async with session_factory() as session:
        result = await session.execute(
            select(Device).where(Device.id == device_id, Device.site_id == site_id)
        )
        device = result.scalar_one_or_none()
        
        if device is None:
            return None
        
        return DeviceResponse(
            id=device.id,
            name=device.name,
            host=device.host,
            port=device.port,
            device_id=device.device_id,
            server_id=device.server_id,
            site_id=device.site_id,
            description=device.description,
            main_type=device.main_type,
            sub_type=device.sub_type,
            poll_enabled=device.poll_enabled if device.poll_enabled is not None else True,
            configs=device.configs or [],
            created_at=device.created_at,
            updated_at=device.updated_at
        )


async def get_device_by_id_internal(device_id: int) -> Optional[DeviceResponse]:
    """Backward-compatible helper to get a device by ID."""
    session_factory = get_async_session_factory()
    async with session_factory() as session:
        result = await session.execute(
            select(Device).where(Device.id == device_id)
        )
        device = result.scalar_one_or_none()
        if device is None:
            return None
        return DeviceResponse(
            id=device.id,
            name=device.name,
            host=device.host,
            port=device.port,
            device_id=device.device_id,
            server_id=device.server_id,
            site_id=device.site_id,
            description=device.description,
            main_type=device.main_type,
            sub_type=device.sub_type,
            poll_enabled=device.poll_enabled if device.poll_enabled is not None else True,
            configs=device.configs or [],
            created_at=device.created_at,
            updated_at=device.updated_at
        )


async def get_device_by_device_id(device_id: int) -> Optional[DeviceResponse]:
    """
    Get a device by device_id (Modbus unit/slave ID).
    
    Args:
        device_id: Device ID (database primary key)
        
    Returns:
        Device if found, None otherwise
    """
    session_factory = get_async_session_factory()
    async with session_factory() as session:
        result = await session.execute(
            select(Device).where(Device.device_id == device_id)
        )
        device = result.scalar_one_or_none()
        
        if device is None:
            return None
        
        return DeviceResponse(
            id=device.id,
            name=device.name,
            host=device.host,
            port=device.port,
            device_id=device.device_id,
            server_id=device.server_id,
            description=device.description,
            main_type=device.main_type,
            sub_type=device.sub_type,
            poll_enabled=device.poll_enabled if device.poll_enabled is not None else True,
            configs=device.configs or [],
            created_at=device.created_at,
            updated_at=device.updated_at
        )


async def get_device_id_by_name(device_name: str) -> Optional[int]:
    """
    Get device ID by device name.
    
    Args:
        device_name: Device name/identifier
        
    Returns:
        Device ID if found, None otherwise
    """
    session_factory = get_async_session_factory()
    async with session_factory() as session:
        result = await session.execute(
            select(Device.id).where(Device.name == device_name)
        )
        device_id = result.scalar_one_or_none()
        
        return device_id


async def get_device_id_by_name_internal(device_name: str) -> Optional[int]:
    """Backward-compatible helper to get device ID by device name."""
    return await get_device_id_by_name(device_name)


async def update_device(device_id: int, device_update: DeviceUpdate, site_id: int) -> DeviceResponse:
    """
    Update a device in the database.
    
    Args:
        device_id: Device ID (database primary key)
        device_update: Device update data (only provided fields will be updated)
    Returns:
        Updated device with new timestamps
        
    Raises:
        ValueError: If device not found or name already exists
        IntegrityError: For other database constraint violations
    """
    session_factory = get_async_session_factory()
    async with session_factory() as session:
        try:
            # Get existing device by primary key
            result = await session.execute(
                select(Device).where(Device.id == device_id, Device.site_id == site_id)
            )
            device = result.scalar_one_or_none()
            
            if device is None:
                raise ValueError(f"Device with id {device_id} not found")
            
            # Update only provided fields
            if device_update.name is not None:
                device.name = device_update.name
            if device_update.host is not None:
                device.host = device_update.host
            if device_update.port is not None:
                device.port = device_update.port
            if device_update.server_id is not None:
                device.server_id = device_update.server_id
            if device_update.description is not None:
                device.description = device_update.description
            if device_update.main_type is not None:
                device.main_type = device_update.main_type
            if device_update.sub_type is not None:
                device.sub_type = device_update.sub_type
            if device_update.poll_enabled is not None:
                device.poll_enabled = device_update.poll_enabled
            if device_update.configs is not None:
                device.configs = device_update.configs
            
            # updated_at is automatically updated by the ORM (onupdate=func.now())
            
            # Commit the transaction
            await session.commit()
            
            # Refresh to get the latest data (including updated_at)
            await session.refresh(device)
            
            logger.info(f"Updated device with id {device.id}")
            
            return DeviceResponse(
                id=device.id,
                name=device.name,
                host=device.host,
                port=device.port,
                device_id=device.device_id,
                server_id=device.server_id,
                site_id=device.site_id,
                description=device.description,
                main_type=device.main_type,
                sub_type=device.sub_type,
                poll_enabled=device.poll_enabled if device.poll_enabled is not None else True,
                configs=device.configs or [],
                created_at=device.created_at,
                updated_at=device.updated_at
            )
            
        except IntegrityError as e:
            await session.rollback()
            # Check if it's a unique constraint violation
            if "unique" in str(e).lower() or "duplicate" in str(e).lower():
                logger.warning(f"Device name already exists")
                raise ValueError("Device with this name already exists") from e
            else:
                logger.error(f"Database integrity error updating device: {e}")
                raise
        except Exception as e:
            await session.rollback()
            logger.error(f"Database error updating device: {e}")
            raise


async def delete_device(device_id: int, site_id: int) -> Optional[DeviceResponse]:
    """
    Delete a device from the database by primary key.
    
    Args:
        device_id: Device ID (database primary key)
        
    Returns:
        DeviceResponse with metadata of the deleted device if found, None if not found
        
    Raises:
        Exception: For database errors
    """
    session_factory = get_async_session_factory()
    async with session_factory() as session:
        try:
            result = await session.execute(
                select(Device).where(Device.id == device_id, Device.site_id == site_id)
            )
            device = result.scalar_one_or_none()
            
            if device is None:
                logger.warning(f"Device with id {device_id} not found for deletion")
                return None
            
            device_response = DeviceResponse(
                id=device.id,
                name=device.name,
                host=device.host,
                port=device.port,
                device_id=device.device_id,
                server_id=device.server_id,
                site_id=device.site_id,
                description=device.description,
                main_type=device.main_type,
                sub_type=device.sub_type,
                poll_enabled=device.poll_enabled if device.poll_enabled is not None else True,
                configs=device.configs or [],
                created_at=device.created_at,
                updated_at=device.updated_at
            )
            
            device_name_to_delete = device.name
            primary_key = device.id
            
            session.delete(device)
            await session.flush()
            await session.commit()
            
            logger.info(f"Successfully deleted device '{device_name_to_delete}' (primary key: {primary_key}).")
            return device_response
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Database error deleting device: {e}")
            raise


async def delete_device_by_id(id: int) -> Optional[DeviceResponse]:
    """Backward-compatible helper to delete by primary key."""
    session_factory = get_async_session_factory()
    async with session_factory() as session:
        result = await session.execute(
            select(Device).where(Device.id == id)
        )
        device = result.scalar_one_or_none()
        if device is None:
            return None
        return await delete_device(device.id, site_id=device.site_id)



