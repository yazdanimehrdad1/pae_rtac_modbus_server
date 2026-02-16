"""Site helper functions for comprehensive DB reads."""

from typing import Optional

from sqlalchemy import select

from db.connection import get_async_session_factory
from logger import get_logger
from schemas.api_models import (
    ConfigResponse,
    Coordinates,
    DeviceWithConfigs,
    Location,
    SiteComprehensiveResponse,
)
from schemas.db_models.orm_models import Config, Device, Site

logger = get_logger(__name__)


async def get_complete_site_data(site_id: int) -> Optional[SiteComprehensiveResponse]:
    """
    Get a site with devices and device configs from the database only.
    
    Args:
        site_id: Site ID (4-digit number)
    
    Returns:
        Comprehensive site data, or None if not found
    """
    session_factory = get_async_session_factory()
    async with session_factory() as session:
        site_result = await session.execute(
            select(Site).where(Site.id == site_id)
        )
        site = site_result.scalar_one_or_none()
        if site is None:
            return None

        device_result = await session.execute(
            select(Device).where(Device.site_id == site_id).order_by(Device.device_id)
        )
        devices = device_result.scalars().all()

        device_ids = [device.device_id for device in devices]

        configs_by_device: dict[int, list[ConfigResponse]] = {}
        if device_ids:
            configs_result = await session.execute(
                select(Config).where(
                    Config.device_id.in_(device_ids),
                    Config.site_id == site_id
                )
            )
            for config in configs_result.scalars().all():
                configs_by_device.setdefault(config.device_id, []).append(
                    ConfigResponse(
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
                )

        coordinates = None
        if site.coordinates:
            coordinates = Coordinates(
                lat=site.coordinates["lat"],
                lng=site.coordinates["lng"],
            )
        location = None
        if site.location:
            location = Location(**site.location)

        device_items: list[DeviceWithConfigs] = []
        for device in devices:
            device_configs = configs_by_device.get(device.device_id, [])
            device_items.append(
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
                    configs=device_configs,
                )
            )

        return SiteComprehensiveResponse(
            site_id=site.id,
            client_id=site.client_id,
            name=site.name,
            location=location,
            operator=site.operator,
            capacity=site.capacity,
            device_count=site.device_count,
            description=site.description,
            coordinates=coordinates,
            devices=device_items,
            created_at=site.created_at,
            updated_at=site.updated_at,
            last_update=site.last_update,
        )
