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
from sqlalchemy.orm import selectinload

from db.connection import get_async_session_factory
from schemas.db_models.models import DeviceCreate, DeviceUpdate, DeviceResponse, DeviceListItem
from schemas.db_models.orm_models import Device, Site
from config import settings
from logger import get_logger

logger = get_logger(__name__)


async def create_device(device: DeviceCreate, site_id: Optional[str] = None) -> DeviceResponse:
    """
    Create a new device in the database and optionally associate it with a site.
    
    Args:
        device: Device creation data
        site_id: Optional site ID (UUID) to associate this device with. If provided, site must exist.
        
    Returns:
        Created device with ID and timestamps
        
    Raises:
        ValueError: If site not found (when site_id is provided) or device name already exists
        IntegrityError: For other database constraint violations
    """
    session_factory = get_async_session_factory()
    async with session_factory() as session:
        try:
            # Validate site_id if provided - site must exist
            site = None
            if site_id:
                site_result = await session.execute(
                    select(Site).where(Site.id == site_id)
                )
                site = site_result.scalar_one_or_none()
                if site is None:
                    raise ValueError(f"Site with id '{site_id}' not found")
            
            # Check if device name already exists in this specific site
            if site_id:
                existing_device_result = await session.execute(
                    select(Device).where(
                        Device.name == device.name,
                        Device.site_id == site_id
                    )
                )
                existing_device = existing_device_result.scalar_one_or_none()
                if existing_device is not None:
                    # Device with same name already exists in this site
                    raise ValueError(f"Device with name '{device.name}' already exists in site '{site.name}'")
            
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
                poll_enabled=device.poll_enabled,
                site_id=site_id  # Use site_id from path parameter
            )
            
            # Add to session and flush to get the ID
            session.add(new_device)
            await session.flush()  # Flush to get the ID without committing
            
            # Update device_count in site if site_id is provided
            if site_id:
                await session.execute(
                    update(Site)
                    .where(Site.id == site_id)
                    .values(device_count=Site.device_count + 1)
                )
            
            # Store the primary key before commit
            device_primary_key = new_device.id
            
            logger.info(f"Created device: {device.name} (ID: {device_primary_key})")
            
            # Commit the transaction
            await session.commit()
            
            # Query the device back after commit to get the database-generated timestamps
            # This avoids greenlet issues from accessing ORM object attributes after commit
            result = await session.execute(
                select(Device).where(Device.id == device_primary_key)
            )
            created_device = result.scalar_one_or_none()
            
            if created_device is None:
                # This shouldn't happen, but handle it gracefully
                raise RuntimeError(f"Device with id {device_primary_key} not found after creation")
            
            # Build response from the freshly queried device
            return DeviceResponse(
                id=created_device.id,
                name=created_device.name,
                host=created_device.host,
                port=created_device.port,
                device_id=created_device.device_id,
                description=created_device.description,
                register_map=None,  # New devices don't have register map initially
                poll_address=created_device.poll_address,
                poll_count=created_device.poll_count,
                poll_kind=created_device.poll_kind,
                poll_enabled=created_device.poll_enabled if created_device.poll_enabled is not None else True,
                site_id=created_device.site_id,
                created_at=created_device.created_at,
                updated_at=created_device.updated_at
            )
            
        except IntegrityError as e:
            await session.rollback()
            # Check if it's a unique constraint violation
            if "unique" in str(e).lower() or "duplicate" in str(e).lower() or "already exists" in str(e).lower():
                # For site-scoped uniqueness, we should have site_id and site available
                if site_id and site:
                    logger.warning(f"Device name '{device.name}' already exists in site '{site.name}'")
                    raise ValueError(f"Device with name '{device.name}' already exists in site '{site.name}'") from e
                else:
                    # Fallback: try to query for the existing device to get site info
                    try:
                        existing_device_result = await session.execute(
                            select(Device).where(
                                Device.name == device.name,
                                Device.site_id == site_id
                            )
                        )
                        existing_device = existing_device_result.scalar_one_or_none()
                        if existing_device and existing_device.site_id:
                            site_result = await session.execute(
                                select(Site).where(Site.id == existing_device.site_id)
                            )
                            existing_site = site_result.scalar_one_or_none()
                            if existing_site:
                                logger.warning(f"Device name '{device.name}' already exists in site '{existing_site.name}'")
                                raise ValueError(f"Device with name '{device.name}' already exists in site '{existing_site.name}'") from e
                    except ValueError:
                        # Re-raise ValueError (our custom error with site info)
                        raise
                    except Exception as query_error:
                        # Log but fall through to generic error message
                        logger.debug(f"Could not query existing device for site info: {query_error}")
                    
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
                    site_id=device.site_id,
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
            site_id=device.site_id,
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
            site_id=device.site_id,
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
            
            # Handle site_id changes and update device_count
            old_site_id = device.site_id
            if device_update.site_id is not None:
                # Validate new site_id if provided
                if device_update.site_id:
                    site_result = await session.execute(
                        select(Site).where(Site.id == device_update.site_id)
                    )
                    site = site_result.scalar_one_or_none()
                    if site is None:
                        raise ValueError(f"Site with id {device_update.site_id} not found")
                
                # Update site_id
                device.site_id = device_update.site_id
                
                # Update device_count: decrement old site, increment new site
                if old_site_id and old_site_id != device_update.site_id:
                    # Decrement old site
                    await session.execute(
                        update(Site)
                        .where(Site.id == old_site_id)
                        .values(device_count=Site.device_count - 1)
                    )
                if device_update.site_id and old_site_id != device_update.site_id:
                    # Increment new site
                    await session.execute(
                        update(Site)
                        .where(Site.id == device_update.site_id)
                        .values(device_count=Site.device_count + 1)
                    )
                elif device_update.site_id is None and old_site_id:
                    # Removing device from site
                    await session.execute(
                        update(Site)
                        .where(Site.id == old_site_id)
                        .values(device_count=Site.device_count - 1)
                    )
            
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


async def delete_device(device_id: int, site_id: Optional[str] = None) -> Optional[DeviceResponse]:
    """
    Delete a device from the database.
    
    Args:
        device_id: Modbus unit/slave ID (not the primary key)
        site_id: Optional site ID to validate that the device belongs to this site
        
    Returns:
        DeviceResponse with metadata of the deleted device if found, None if not found
        
    Raises:
        ValueError: If site_id is provided and device doesn't belong to that site, or site doesn't exist
        Exception: For database errors
    """
    session_factory = get_async_session_factory()
    async with session_factory() as session:
        try:
            # Validate site_id if provided - site must exist
            if site_id:
                site_result = await session.execute(
                    select(Site).where(Site.id == site_id)
                )
                site = site_result.scalar_one_or_none()
                if site is None:
                    raise ValueError(f"Site with id '{site_id}' not found")
            
            # Get the device to delete by device_id (Modbus unit/slave ID)
            # Load register_map relationship to ensure cascade delete works properly
            result = await session.execute(
                select(Device)
                .where(Device.device_id == device_id)
                .options(selectinload(Device.register_map))
            )
            device = result.scalar_one_or_none()
            
            if device is None:
                logger.warning(f"Device with device_id {device_id} not found for deletion")
                return None
            
            # Validate that device belongs to the specified site if site_id is provided
            if site_id:
                if device.site_id != site_id:
                    raise ValueError(f"Device with device_id {device_id} does not belong to site '{site_id}'")
            
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
                site_id=device.site_id,
                created_at=device.created_at,
                updated_at=device.updated_at
            )
            
            # Delete the device using ORM delete to ensure cascade relationships are handled
            # This will automatically delete related register_map and register_readings
            # due to cascade="all, delete-orphan" in the ORM relationships
            device_id_to_delete = device.device_id
            device_name_to_delete = device.name
            primary_key = device.id
            
            # Decrement device_count in site if device is associated with a site
            if device.site_id:
                await session.execute(
                    update(Site)
                    .where(Site.id == device.site_id)
                    .values(device_count=Site.device_count - 1)
                )
            
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


async def delete_device_by_id(id: int) -> Optional[DeviceResponse]:
    """
    Delete a device from the database by its primary key (id).
    
    Args:
        id: Database primary key (id)
        
    Returns:
        DeviceResponse with metadata of the deleted device if found, None if not found
        
    Raises:
        Exception: For database errors
    """
    session_factory = get_async_session_factory()
    async with session_factory() as session:
        try:
            # Get the device to delete by primary key (id)
            # Load register_map relationship to ensure cascade delete works properly
            result = await session.execute(
                select(Device)
                .where(Device.id == id)
                .options(selectinload(Device.register_map))
            )
            device = result.scalar_one_or_none()
            
            if device is None:
                logger.warning(f"Device with id {id} not found for deletion")
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
                site_id=device.site_id,
                created_at=device.created_at,
                updated_at=device.updated_at
            )
            
            # Store info for logging
            device_id_to_delete = device.device_id
            device_name_to_delete = device.name
            primary_key = device.id
            
            # Decrement device_count in site if device is associated with a site
            if device.site_id:
                await session.execute(
                    update(Site)
                    .where(Site.id == device.site_id)
                    .values(device_count=Site.device_count - 1)
                )
            
            # Use ORM delete to respect cascade relationships
            # Database-level CASCADE will also handle foreign key constraints
            session.delete(device)
            await session.flush()  # Flush to check for constraint violations before commit
            
            await session.commit()
            
            logger.info(f"Successfully deleted device '{device_name_to_delete}' with id {primary_key} (device_id: {device_id_to_delete}). Related register_map and register_readings were cascade deleted.")
            return device_response
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Database error deleting device by id: {e}")
            raise



