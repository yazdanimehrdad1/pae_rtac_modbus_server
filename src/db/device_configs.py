"""
Config database operations.

Handles CRUD operations for configs table.
"""

from typing import Optional
from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError

from db.session import get_session
from schemas.db_models.models import ConfigCreate, ConfigUpdate, ConfigResponse
from schemas.db_models.orm_models import Config, Device
from logger import get_logger

logger = get_logger(__name__)


CONFIG_INDEX_MIN = 1
CONFIG_INDEX_MAX = 10

# 
async def _generate_config_id(session, site_id: int, device_id: int) -> str:
    prefix = f"{site_id}-{device_id}-"
    device_result = await session.execute(
        select(Device.device_id).where(Device.device_id == device_id)
    )
    device_exists = device_result.scalar_one_or_none()
    if device_exists is None:
        raise ValueError(f"Device with id '{device_id}' not found")
    config_count_result = await session.execute(
        select(Config.config_id).where(Config.device_id == device_id)
    )
    existing_count = len(config_count_result.scalars().all())
    next_index = existing_count + 1
    if next_index > CONFIG_INDEX_MAX:
        raise ValueError("No available device config slots")
    if next_index < CONFIG_INDEX_MIN:
        next_index = CONFIG_INDEX_MIN
    return f"{prefix}{next_index}"


async def create_config_for_device(
    site_id: int,
    device_id: int,
    config: ConfigCreate
) -> ConfigResponse:
    """
    Create a new config.
    
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
            config_id = await _generate_config_id(session, site_id, device_id)
            payload = config.model_dump()
            device_result = await session.execute(
                select(Device).where(Device.device_id == device_id, Device.site_id == site_id)
            )
            device = device_result.scalar_one_or_none()
            if device is None:
                raise ValueError(f"Device with id '{device_id}' not found in site '{site_id}'")
            existing_poll_result = await session.execute(
                select(Config.config_id, Config.poll_start_index).where(
                    Config.device_id == device_id,
                    Config.site_id == site_id
                )
            )
            for existing_id, existing_poll_start in existing_poll_result.all():
                if existing_poll_start == payload["poll_start_index"]:
                    raise ValueError(
                        f"Config with poll_start_index {payload['poll_start_index']} already exists "
                        f"(config_id '{existing_id}')"
                    )

            config_row = Config(
                config_id=config_id,
                site_id=payload["site_id"],
                device_id=payload["device_id"],
                poll_kind=payload["poll_kind"],
                poll_start_index=payload["poll_start_index"],
                poll_count=payload["poll_count"],
                points=payload["points"],
                is_active=payload["is_active"],
                created_by=payload["created_by"],
            )
            session.add(config_row)
            await session.commit()
            
            return ConfigResponse(
                config_id=config_row.config_id,
                created_at=config_row.created_at,
                updated_at=config_row.updated_at,
                **payload
            )
        except IntegrityError as e:
            await session.rollback()
            raise ValueError("Config already exists") from e
        except Exception:
            await session.rollback()
            raise


async def get_config(config_id: str) -> Optional[ConfigResponse]:
    """
    Get a config by ID.
    """
    async with get_session() as session:
        result = await session.execute(
            select(Config).where(Config.config_id == config_id)
        )
        config = result.scalar_one_or_none()
        if config is None:
            return None
        return ConfigResponse(
            config_id=config.config_id,
            created_at=config.created_at,
            updated_at=config.updated_at,
            site_id=config.site_id,
            device_id=config.device_id,
            poll_kind=config.poll_kind,
            poll_start_index=config.poll_start_index,
            poll_count=config.poll_count,
            points=config.points,
            is_active=config.is_active,
            created_by=config.created_by,
        )


async def update_config(config_id: str, update: ConfigUpdate) -> Optional[ConfigResponse]:
    """
    Update an existing config.
    """
    async with get_session() as session:
        result = await session.execute(
            select(Config).where(Config.config_id == config_id)
        )
        config = result.scalar_one_or_none()
        if config is None:
            return None
        
        payload = update.model_dump()
        if payload.get("poll_kind") is not None:
            config.poll_kind = payload["poll_kind"]
        if payload.get("poll_start_index") is not None:
            config.poll_start_index = payload["poll_start_index"]
        if payload.get("poll_count") is not None:
            config.poll_count = payload["poll_count"]
        if payload.get("points") is not None:
            config.points = payload["points"]
        if payload.get("is_active") is not None:
            config.is_active = payload["is_active"]
        if payload.get("created_by") is not None:
            config.created_by = payload["created_by"]
        await session.commit()
        await session.refresh(config)
        
        return ConfigResponse(
            config_id=config.config_id,
            created_at=config.created_at,
            updated_at=config.updated_at,
            site_id=config.site_id,
            device_id=config.device_id,
            poll_kind=config.poll_kind,
            poll_start_index=config.poll_start_index,
            poll_count=config.poll_count,
            points=config.points,
            is_active=config.is_active,
            created_by=config.created_by,
        )


async def delete_config(config_id: str) -> bool:
    """
    Delete a config by ID.
    """
    async with get_session() as session:
        result = await session.execute(
            select(Config).where(Config.config_id == config_id)
        )
        config = result.scalar_one_or_none()
        if config is None:
            return False
        delete_result = await session.execute(
            delete(Config).where(Config.config_id == config_id)
        )
        await session.commit()
        return delete_result.rowcount > 0


async def get_configs_for_device(
    device_id: int,
    site_id: Optional[int] = None,
) -> list[ConfigResponse]:
    """
    Get all configs for a device, optionally scoped by site_id.
    """
    async with get_session() as session:
        query = select(Config).where(Config.device_id == device_id)
        if site_id is not None:
            query = query.where(Config.site_id == site_id)
        result = await session.execute(query.order_by(Config.poll_start_index))
        configs = result.scalars().all()
        responses: list[ConfigResponse] = []
        for config in configs:
            responses.append(
                ConfigResponse(
                    config_id=config.config_id,
                    created_at=config.created_at,
                    updated_at=config.updated_at,
                    site_id=config.site_id,
                    device_id=config.device_id,
                    poll_kind=config.poll_kind,
                    poll_start_index=config.poll_start_index,
                    poll_count=config.poll_count,
                    points=config.points,
                    is_active=config.is_active,
                    created_by=config.created_by,
                )
            )
        return responses

