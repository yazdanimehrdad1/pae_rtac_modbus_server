"""
Device database operations.

Handles CRUD operations for devices table.
Uses SQLAlchemy 2.0+ async ORM.
"""

from typing import Optional
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from db.connection import get_async_session_factory
from schemas.db_models.models import (
    ConfigResponse,
    DeviceCreateRequest,
    DeviceUpdate,
    DeviceResponse,
    DeviceWithConfigs,
)
from schemas.db_models.orm_models import Config, Device, Site
from utils.exceptions import ConflictError, NotFoundError, ValidationError, InternalError
from logger import get_logger

logger = get_logger(__name__)


def _config_to_response(config: Config) -> ConfigResponse:
    return ConfigResponse(
        config_id=config.config_id,
        site_id=config.site_id,
        device_id=config.device_id,
        poll_kind=config.poll_kind,
        poll_start_index=config.poll_start_index,
        poll_count=config.poll_count,
        points=config.points,
        is_active=config.is_active,
        created_at=config.created_at,
        updated_at=config.updated_at,
        created_by=config.created_by,
    )


async def create_device(device: DeviceCreateRequest, site_id: int) -> DeviceWithConfigs:
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
                raise ConflictError(f"Device with name '{device.name}' already exists")
            
            site_result = await session.execute(
                select(Site).where(Site.id == site_id)
            )
            site = site_result.scalar_one_or_none()
            if site is None:
                raise NotFoundError(f"Site with id '{site_id}' not found")
            
            new_device = Device(
                name=device.name,
                type=device.type,
                vendor=device.vendor,
                model=device.model,
                host=device.host,
                port=device.port,
                timeout=device.timeout,
                server_address=device.server_address,
                description=device.description,
                poll_enabled=device.poll_enabled,
                read_from_aggregator=device.read_from_aggregator,
                protocol=device.protocol,
                site_id=site_id
            )
            
            # Add to session and flush to get the ID
            session.add(new_device)
            await session.flush()
            device_primary_key = new_device.device_id
            logger.info(f"Created device: {device.name} (ID: {device_primary_key})")
            
            await session.commit()
            
            result = await session.execute(
                select(Device).where(Device.device_id == device_primary_key)
            )
            created_device = result.scalar_one_or_none()
            
            if created_device is None:
                raise InternalError(f"Device with id {device_primary_key} not found after creation")
            
            return DeviceWithConfigs(
                device_id=created_device.device_id,
                site_id=created_device.site_id,
                name=created_device.name,
                type=created_device.type,
                vendor=created_device.vendor,
                model=created_device.model,
                host=created_device.host,
                port=created_device.port,
                timeout=created_device.timeout,
                server_address=created_device.server_address,
                description=created_device.description,
                poll_enabled=created_device.poll_enabled if created_device.poll_enabled is not None else True,
                read_from_aggregator=created_device.read_from_aggregator if created_device.read_from_aggregator is not None else True,
                protocol=created_device.protocol,
                created_at=created_device.created_at,
                updated_at=created_device.updated_at,
                configs=[],
            )
            
        except IntegrityError as e:
            await session.rollback()
            # Check if it's a unique constraint violation
            error_text = str(e).lower()
            if "unique" in error_text or "duplicate" in error_text or "already exists" in error_text:
                logger.warning(f"Device name '{device.name}' already exists")
                raise ConflictError(f"Device with name '{device.name}' already exists") from e
            else:
                logger.error(f"Database integrity error creating device: {e}")
                raise ValidationError(f"Database integrity error: {e}") from e
        except Exception as e:
            await session.rollback()
            logger.error(f"Database error creating device: {e}")
            raise InternalError(f"Failed to create device: {e}") from e


async def get_all_devices(site_id: int) -> list[DeviceWithConfigs]:
    """
    Get all devices from the database.
    
    Returns:
        List of all devices ordered by ID
    """
    session_factory = get_async_session_factory()
    async with session_factory() as session:
        result = await session.execute(
            select(Device).where(Device.site_id == site_id).order_by(Device.device_id)
        )
        devices = result.scalars().all()
        
        device_ids = [device.device_id for device in devices]
        configs_by_device: dict[int, list[ConfigResponse]] = {}
        if device_ids:
            configs_result = await session.execute(
                select(Config).where(Config.device_id.in_(device_ids))
            )
            for config in configs_result.scalars().all():
                configs_by_device.setdefault(config.device_id, []).append(
                    _config_to_response(config)
                )

        device_list: list[DeviceWithConfigs] = []
        for device in devices:
            device_list.append(
                DeviceWithConfigs(
                    device_id=device.device_id,
                    site_id=device.site_id,
                    name=device.name,
                    type=device.type,
                    vendor=device.vendor,
                    model=device.model,
                    host=device.host,
                    port=device.port,
                    timeout=device.timeout,
                    server_address=device.server_address,
                    description=device.description,
                    poll_enabled=device.poll_enabled if device.poll_enabled is not None else True,
                    read_from_aggregator=device.read_from_aggregator if device.read_from_aggregator is not None else True,
                    protocol=device.protocol,
                    created_at=device.created_at,
                    updated_at=device.updated_at,
                    configs=configs_by_device.get(device.device_id, []),
                )
            )
        return device_list


async def get_device_by_id(device_id: int, site_id: int) -> Optional[DeviceWithConfigs]:
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
            select(Device).where(Device.device_id == device_id, Device.site_id == site_id)
        )
        device = result.scalar_one_or_none()
        
        if device is None:
            return None
        
        configs_result = await session.execute(
            select(Config).where(Config.device_id == device.device_id)
        )
        device_configs = [
            _config_to_response(config)
            for config in configs_result.scalars().all()
        ]

        return DeviceWithConfigs(
            device_id=device.device_id,
            site_id=device.site_id,
            name=device.name,
            type=device.type,
            vendor=device.vendor,
            model=device.model,
            host=device.host,
            port=device.port,
            timeout=device.timeout,
            server_address=device.server_address,
            description=device.description,
            poll_enabled=device.poll_enabled if device.poll_enabled is not None else True,
            read_from_aggregator=device.read_from_aggregator if device.read_from_aggregator is not None else True,
            protocol=device.protocol,
            created_at=device.created_at,
            updated_at=device.updated_at,
            configs=device_configs,
        )


async def get_device_by_id_internal(device_id: int) -> Optional[DeviceWithConfigs]:
    """Backward-compatible helper to get a device by ID."""
    session_factory = get_async_session_factory()
    async with session_factory() as session:
        result = await session.execute(
            select(Device).where(Device.device_id == device_id)
        )
        device = result.scalar_one_or_none()
        if device is None:
            return None
        configs_result = await session.execute(
            select(Config).where(Config.device_id == device.device_id)
        )
        device_configs = [
            _config_to_response(config)
            for config in configs_result.scalars().all()
        ]

        return DeviceWithConfigs(
            device_id=device.device_id,
            site_id=device.site_id,
            name=device.name,
            type=device.type,
            vendor=device.vendor,
            model=device.model,
            host=device.host,
            port=device.port,
            timeout=device.timeout,
            server_address=device.server_address,
            description=device.description,
            poll_enabled=device.poll_enabled if device.poll_enabled is not None else True,
            read_from_aggregator=device.read_from_aggregator if device.read_from_aggregator is not None else True,
            protocol=device.protocol,
            created_at=device.created_at,
            updated_at=device.updated_at,
            configs=device_configs,
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
            select(Device.device_id).where(Device.name == device_name)
        )
        device_id = result.scalar_one_or_none()
        
        return device_id


async def get_device_id_by_name_internal(device_name: str) -> Optional[int]:
    """Backward-compatible helper to get device ID by device name."""
    return await get_device_id_by_name(device_name)


async def update_device(device_id: int, device_update: DeviceUpdate, site_id: int) -> DeviceWithConfigs:
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
                select(Device).where(Device.device_id == device_id, Device.site_id == site_id)
            )
            device = result.scalar_one_or_none()
            
            if device is None:
                raise NotFoundError(f"Device with id {device_id} not found")
            
            # Update only provided fields
            if device_update.name is not None:
                device.name = device_update.name
            if device_update.type is not None:
                device.type = device_update.type
            if device_update.vendor is not None:
                device.vendor = device_update.vendor
            if device_update.model is not None:
                device.model = device_update.model
            if device_update.host is not None:
                device.host = device_update.host
            if device_update.port is not None:
                device.port = device_update.port
            if device_update.timeout is not None:
                device.timeout = device_update.timeout
            if device_update.server_address is not None:
                device.server_address = device_update.server_address
            if device_update.description is not None:
                device.description = device_update.description
            if device_update.poll_enabled is not None:
                device.poll_enabled = device_update.poll_enabled
            if device_update.read_from_aggregator is not None:
                device.read_from_aggregator = device_update.read_from_aggregator
            if device_update.protocol is not None:
                device.protocol = device_update.protocol
            
            # updated_at is automatically updated by the ORM (onupdate=func.now())
            
            # Commit the transaction
            await session.commit()
            
            # Refresh to get the latest data (including updated_at)
            await session.refresh(device)
            
            logger.info(f"Updated device with id {device.device_id}")
            
            configs_result = await session.execute(
                select(Config).where(Config.device_id == device.device_id)
            )
            device_configs = [
                _config_to_response(config)
                for config in configs_result.scalars().all()
            ]

            return DeviceWithConfigs(
                device_id=device.device_id,
                site_id=device.site_id,
                name=device.name,
                type=device.type,
                vendor=device.vendor,
                model=device.model,
                host=device.host,
                port=device.port,
                timeout=device.timeout,
                server_address=device.server_address,
                description=device.description,
                poll_enabled=device.poll_enabled if device.poll_enabled is not None else True,
                read_from_aggregator=device.read_from_aggregator if device.read_from_aggregator is not None else True,
                protocol=device.protocol,
                created_at=device.created_at,
                updated_at=device.updated_at,
                configs=device_configs,
            )
            
        except IntegrityError as e:
            await session.rollback()
            # Check if it's a unique constraint violation
            if "unique" in str(e).lower() or "duplicate" in str(e).lower():
                logger.warning(f"Device name already exists")
                raise ConflictError("Device with this name already exists") from e
            else:
                logger.error(f"Database integrity error updating device: {e}")
                raise ValidationError(f"Database integrity error: {e}") from e
        except Exception as e:
            await session.rollback()
            logger.error(f"Database error updating device: {e}")
            raise InternalError(f"Failed to update device: {e}") from e


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
                select(Device).where(Device.device_id == device_id, Device.site_id == site_id)
            )
            device = result.scalar_one_or_none()
            
            if device is None:
                logger.warning(f"Device with id {device_id} not found for deletion")
                return None

            config_result = await session.execute(
                select(Config.config_id).where(Config.device_id == device_id)
            )
            config_ids = [row[0] for row in config_result.all()]
            if config_ids:
                joined_ids = ", ".join(str(config_id) for config_id in config_ids)
                raise ConflictError(
                    f"Device with id {device_id} has associated configs: {joined_ids}",
                    payload={"config_ids": config_ids}
                )
            
            device_response = DeviceResponse(
                device_id=device.device_id,
                site_id=device.site_id,
                name=device.name,
                type=device.type,
                vendor=device.vendor,
                model=device.model,
                host=device.host,
                port=device.port,
                timeout=device.timeout,
                server_address=device.server_address,
                description=device.description,
                poll_enabled=device.poll_enabled if device.poll_enabled is not None else True,
                read_from_aggregator=device.read_from_aggregator if device.read_from_aggregator is not None else True,
                protocol=device.protocol,
                created_at=device.created_at,
                updated_at=device.updated_at
            )
            
            device_name_to_delete = device.name
            primary_key = device.device_id
            
            await session.delete(device)
            await session.flush()
            await session.commit()
            
            logger.info(f"Successfully deleted device '{device_name_to_delete}' (primary key: {primary_key}).")
            return device_response
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Database error deleting device: {e}")
            raise InternalError(f"Failed to delete device: {e}") from e


async def delete_device_by_id(id: int) -> Optional[DeviceResponse]:
    """Backward-compatible helper to delete by primary key."""
    session_factory = get_async_session_factory()
    async with session_factory() as session:
        result = await session.execute(
            select(Device).where(Device.device_id == id)
        )
        device = result.scalar_one_or_none()
        if device is None:
            return None
        return await delete_device(device.device_id, site_id=device.site_id)



