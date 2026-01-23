"""
Device config database operations.

Handles CRUD operations for device_configs table.
"""

from typing import Optional
from sqlalchemy import select, update, delete
from sqlalchemy.exc import IntegrityError

from db.session import get_session
from schemas.db_models.models import DeviceConfigData, DeviceConfigResponse
from schemas.db_models.orm_models import DeviceConfig, Device
from logger import get_logger

logger = get_logger(__name__)


CONFIG_INDEX_MIN = 1
CONFIG_INDEX_MAX = 10

# 
async def _generate_config_id(session, site_id: int, device_id: int) -> str:
    prefix = f"{site_id}-{device_id}-"
    result = await session.execute(
        select(Device.configs).where(Device.id == device_id)
    )
    device_configs = result.scalar_one_or_none()
    if device_configs is None:
        raise ValueError(f"Device with id '{device_id}' not found")
    next_index = len(device_configs) + 1
    if next_index > CONFIG_INDEX_MAX:
        raise ValueError("No available device config slots")
    if next_index < CONFIG_INDEX_MIN:
        next_index = CONFIG_INDEX_MIN
    return f"{prefix}{next_index}"


async def create_device_config_for_device(
    site_id: int,
    device_id: int,
    config: DeviceConfigData
) -> DeviceConfigResponse:
    """
    Create a new device config.
    
    Args:
        config: Device config creation data
        
    Returns:
        Created device config with timestamps
        
    Raises:
        ValueError: If config ID already exists
        IntegrityError: For other database constraint violations
    """
    async with get_session() as session:
        try:
            if config.site_id != site_id or config.device_id != device_id:
                raise ValueError("Path site_id/device_id must match body")
            
            config_id = await _generate_config_id(session, site_id, device_id)
            # convert DeviceConfigData to dict
            payload = config.model_dump(by_alias=True)
            device_result = await session.execute(
                select(Device).where(Device.id == device_id, Device.site_id == site_id)
            )
            device = device_result.scalar_one_or_none()
            if device is None:
                raise ValueError(f"Device with id '{device_id}' not found in site '{site_id}'")
            existing_configs = list(device.configs or [])
            if existing_configs:
                existing_poll_result = await session.execute(
                    select(DeviceConfig.id, DeviceConfig.poll_address).where(
                        DeviceConfig.id.in_(existing_configs)
                    )
                )
                for existing_id, existing_poll_address in existing_poll_result.all():
                    if existing_poll_address == payload["poll_address"]:
                        raise ValueError(
                            f"Device config with poll_address {payload['poll_address']} already exists "
                            f"(config_id '{existing_id}')"
                        )
            existing_configs.append(config_id)
            device.configs = existing_configs

            device_config = DeviceConfig(
                id=config_id,
                site_id=payload["Site_id"],
                device_id=payload["device_id"],
                poll_address=payload["poll_address"],
                poll_count=payload["poll_count"],
                poll_kind=payload["poll_kind"],
                registers=payload["registers"]
            )
            session.add(device_config)
            await session.commit()
            
            return DeviceConfigResponse(
                config_id=device_config.id,
                created_at=device_config.created_at,
                updated_at=device_config.updated_at,
                **payload
            )
        except IntegrityError as e:
            await session.rollback()
            raise ValueError("Device config already exists") from e
        except Exception:
            await session.rollback()
            raise


async def get_device_config(config_id: str) -> Optional[DeviceConfigResponse]:
    """
    Get a device config by ID.
    """
    async with get_session() as session:
        result = await session.execute(
            select(DeviceConfig).where(DeviceConfig.id == config_id)
        )
        config = result.scalar_one_or_none()
        if config is None:
            return None
        return DeviceConfigResponse(
            config_id=config.id,
            created_at=config.created_at,
            updated_at=config.updated_at,
            Site_id=config.site_id,
            device_id=config.device_id,
            poll_address=config.poll_address,
            poll_count=config.poll_count,
            poll_kind=config.poll_kind,
            registers=config.registers
        )


async def update_device_config(config_id: str, update: DeviceConfigData) -> Optional[DeviceConfigResponse]:
    """
    Update an existing device config.
    """
    async with get_session() as session:
        result = await session.execute(
            select(DeviceConfig).where(DeviceConfig.id == config_id)
        )
        config = result.scalar_one_or_none()
        if config is None:
            return None
        
        payload = update.model_dump(by_alias=True)
        config.site_id = payload["Site_id"]
        config.device_id = payload["device_id"]
        config.poll_address = payload["poll_address"]
        config.poll_count = payload["poll_count"]
        config.poll_kind = payload["poll_kind"]
        config.registers = payload["registers"]
        await session.commit()
        await session.refresh(config)
        
        return DeviceConfigResponse(
            config_id=config.id,
            created_at=config.created_at,
            updated_at=config.updated_at,
            Site_id=config.site_id,
            device_id=config.device_id,
            poll_address=config.poll_address,
            poll_count=config.poll_count,
            poll_kind=config.poll_kind,
            registers=config.registers
        )


async def delete_device_config(config_id: str) -> bool:
    """
    Delete a device config by ID.
    """
    async with get_session() as session:
        result = await session.execute(
            select(DeviceConfig).where(DeviceConfig.id == config_id)
        )
        config = result.scalar_one_or_none()
        if config is None:
            return False
        device_result = await session.execute(
            select(Device).where(Device.id == config.device_id)
        )
        device = device_result.scalar_one_or_none()
        if device is not None:
            existing_configs = list(device.configs or [])
            if config_id in existing_configs:
                existing_configs.remove(config_id)
                device.configs = existing_configs
        delete_result = await session.execute(
            delete(DeviceConfig).where(DeviceConfig.id == config_id)
        )
        await session.commit()
        return delete_result.rowcount > 0

