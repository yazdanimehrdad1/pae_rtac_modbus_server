"""
Device database operations.

Handles CRUD operations for devices table.
Uses SQLAlchemy 2.0+ async ORM.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from db.connection import get_async_session_factory
from schemas.db_models.models import DeviceCreate, DeviceUpdate, DeviceResponse, DeviceListItem
from schemas.db_models.orm_models import Device
from config import settings
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
        ValueError: If device name already exists
        IntegrityError: For other database constraint violations
    """
    session_factory = get_async_session_factory()
    async with session_factory() as session:
        try:
            # Create new Device instance
            new_device = Device(
                name=device.name,
                host=device.host,
                port=device.port,
                device_id=device.device_id,
                description=device.description,
                poll_address=device.poll_address,
                poll_count=device.poll_count,
                poll_kind=device.poll_kind,
                poll_enabled=device.poll_enabled
            )
            
            # Add to session and flush to get the ID
            session.add(new_device)
            await session.flush()  # Flush to get the ID without committing
            
            logger.info(f"Created device: {device.name} (ID: {new_device.id})")
            
            # Commit the transaction
            await session.commit()
            
            # Refresh to ensure we have the latest data (including timestamps)
            await session.refresh(new_device)
            
            return DeviceResponse(
                id=new_device.id,
                name=new_device.name,
                host=new_device.host,
                port=new_device.port,
                device_id=new_device.device_id,
                description=new_device.description,
                register_map=None,  # New devices don't have register map initially
                poll_address=new_device.poll_address,
                poll_count=new_device.poll_count,
                poll_kind=new_device.poll_kind,
                poll_enabled=new_device.poll_enabled if new_device.poll_enabled is not None else True,
                created_at=new_device.created_at,
                updated_at=new_device.updated_at
            )
            
        except IntegrityError as e:
            await session.rollback()
            # Check if it's a unique constraint violation
            if "unique" in str(e).lower() or "duplicate" in str(e).lower():
                logger.warning(f"Device name '{device.name}' already exists")
                raise ValueError(f"Device with name '{device.name}' already exists") from e
            else:
                logger.error(f"Database integrity error creating device: {e}")
                raise
        except Exception as e:
            await session.rollback()
            logger.error(f"Database error creating device: {e}")
            raise


async def get_all_devices() -> list[DeviceListItem]:
    """
    Get all devices from the database.
    
    Returns:
        List of all devices (without register_map for performance), ordered by ID
    """
    session_factory = get_async_session_factory()
    async with session_factory() as session:
        # Query all devices ordered by ID
        result = await session.execute(
            select(Device).order_by(Device.id)
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
                    description=device.description,
                    poll_address=device.poll_address,
                    poll_count=device.poll_count,
                    poll_kind=device.poll_kind,
                    poll_enabled=device.poll_enabled if device.poll_enabled is not None else True,
                    created_at=device.created_at,
                    updated_at=device.updated_at
                )
            )
        return device_list


async def get_device_by_id(device_id: int) -> Optional[DeviceResponse]:
    """
    Get a device by ID.
    
    Args:
        device_id: Device ID
        
    Returns:
        Device if found, None otherwise
    """
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
            description=device.description,
            poll_address=device.poll_address,
            poll_count=device.poll_count,
            poll_kind=device.poll_kind,
            poll_enabled=device.poll_enabled if device.poll_enabled is not None else True,
            created_at=device.created_at,
            updated_at=device.updated_at
        )


async def get_device_by_device_id(device_id: int) -> Optional[DeviceResponse]:
    """
    Get a device by device_id (Modbus unit/slave ID).
    
    Queries directly by device_id since it's unique and indexed for optimal performance.
    
    Args:
        device_id: Modbus unit/slave ID (not the primary key)
        
    Returns:
        Device if found, None otherwise
    """
    session_factory = get_async_session_factory()
    async with session_factory() as session:
        # Query directly by device_id (unique and indexed)
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
            description=device.description,
            poll_address=device.poll_address,
            poll_count=device.poll_count,
            poll_kind=device.poll_kind,
            poll_enabled=device.poll_enabled if device.poll_enabled is not None else True,
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


async def update_device(device_id: int, device_update: DeviceUpdate) -> DeviceResponse:
    """
    Update a device in the database.
    
    Args:
        device_id: Modbus unit/slave ID (not the primary key)
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
            # Get existing device by device_id (Modbus unit/slave ID)
            result = await session.execute(
                select(Device).where(Device.device_id == device_id)
            )
            device = result.scalar_one_or_none()
            
            if device is None:
                raise ValueError(f"Device with device_id {device_id} not found")
            
            # Update only provided fields
            if device_update.name is not None:
                device.name = device_update.name
            if device_update.host is not None:
                device.host = device_update.host
            if device_update.port is not None:
                device.port = device_update.port
            if device_update.device_id is not None:
                device.device_id = device_update.device_id
            if device_update.description is not None:
                device.description = device_update.description
            
            # updated_at is automatically updated by the ORM (onupdate=func.now())
            
            # Commit the transaction
            await session.commit()
            
            # Refresh to get the latest data (including updated_at)
            await session.refresh(device)
            
            logger.info(f"Updated device with device_id {device_id} (primary key: {device.id})")
            
            return DeviceResponse(
                id=device.id,
                name=device.name,
                host=device.host,
                port=device.port,
                device_id=device.device_id,
                description=device.description,
                poll_address=device.poll_address,
                poll_count=device.poll_count,
                poll_kind=device.poll_kind,
                poll_enabled=device.poll_enabled if device.poll_enabled is not None else True,
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


async def delete_device(device_id: int) -> Optional[DeviceResponse]:
    """
    Delete a device from the database.
    
    Args:
        device_id: Modbus unit/slave ID (not the primary key)
        
    Returns:
        DeviceResponse with metadata of the deleted device if found, None if not found
        
    Raises:
        Exception: For database errors
    """
    session_factory = get_async_session_factory()
    async with session_factory() as session:
        try:
            # Get the device to delete by device_id (Modbus unit/slave ID)
            result = await session.execute(
                select(Device).where(Device.device_id == device_id)
            )
            device = result.scalar_one_or_none()
            
            if device is None:
                logger.warning(f"Device with device_id {device_id} not found for deletion")
                return None
            
            # Store device data before deletion
            device_response = DeviceResponse(
                id=device.id,
                name=device.name,
                host=device.host,
                port=device.port,
                device_id=device.device_id,
                description=device.description,
                poll_address=device.poll_address,
                poll_count=device.poll_count,
                poll_kind=device.poll_kind,
                poll_enabled=device.poll_enabled if device.poll_enabled is not None else True,
                created_at=device.created_at,
                updated_at=device.updated_at
            )
            
            # Delete the device using ORM delete to ensure cascade relationships are handled
            # This will automatically delete related register_map and register_readings
            # due to cascade="all, delete-orphan" in the ORM relationships
            device_id_to_delete = device.device_id
            device_name_to_delete = device.name
            primary_key = device.id
            
            # Use ORM delete to respect cascade relationships
            # Database-level CASCADE will also handle foreign key constraints
            session.delete(device)
            await session.flush()  # Flush to check for constraint violations before commit
            
            await session.commit()
            
            logger.info(f"Successfully deleted device '{device_name_to_delete}' with device_id {device_id_to_delete} (primary key: {primary_key}). Related register_map and register_readings were cascade deleted.")
            return device_response
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Database error deleting device: {e}")
            raise



