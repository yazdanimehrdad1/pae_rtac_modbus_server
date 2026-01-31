"""Site helper functions for comprehensive DB reads."""

from typing import Optional

from sqlalchemy import select

from db.connection import get_async_session_factory
from logger import get_logger
from schemas.db_models.models import (
    Coordinates,
    DeviceConfigResponse,
    DeviceWithConfigs,
    Location,
    SiteComprehensiveResponse,
)
from schemas.db_models.orm_models import Device, DeviceConfig, Site

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
            select(Device).where(Device.site_id == site_id).order_by(Device.id)
        )
        devices = device_result.scalars().all()

        config_ids = [
            config_id
            for device in devices
            for config_id in (device.configs or [])
        ]

        configs_by_id: dict[str, DeviceConfigResponse] = {}
        if config_ids:
            configs_result = await session.execute(
                select(DeviceConfig).where(DeviceConfig.id.in_(config_ids))
            )
            for config in configs_result.scalars().all():
                configs_by_id[config.id] = DeviceConfigResponse(
                    config_id=config.id,
                    site_id=config.site_id,
                    device_id=config.device_id,
                    poll_address=config.poll_address,
                    poll_count=config.poll_count,
                    poll_kind=config.poll_kind,
                    registers=config.registers,
                    created_at=config.created_at,
                    updated_at=config.updated_at,
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
            device_configs = [
                configs_by_id[config_id]
                for config_id in (device.configs or [])
                if config_id in configs_by_id
            ]
            device_items.append(
                DeviceWithConfigs(
                    id=device.id,
                    name=device.name,
                    modbus_host=device.modbus_host,
                    modbus_port=device.modbus_port,
                    modbus_timeout=device.modbus_timeout,
                    modbus_server_id=device.modbus_server_id,
                    site_id=device.site_id,
                    description=device.description,
                    main_type=device.main_type,
                    sub_type=device.sub_type,
                    poll_enabled=device.poll_enabled if device.poll_enabled is not None else True,
                    read_from_aggregator=device.read_from_aggregator if device.read_from_aggregator is not None else True,
                    configs=device.configs or [],
                    created_at=device.created_at,
                    updated_at=device.updated_at,
                    device_configs=device_configs,
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
