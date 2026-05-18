"""
Devices controller.

Sits between the router and db.devices.
No cache layer — all reads and writes go directly to the DB.

To add caching in the future, only this file needs to be updated;
the router remains unchanged.
"""

from typing import List, Optional

import db.devices as devices_db
from logger import get_logger
from schemas.api_models import DeviceCreateRequest, DeviceUpdate, DeviceWithConfigs
from utils.exceptions import NotFoundError

logger = get_logger(__name__)


async def get_all_devices(site_id: int) -> List[DeviceWithConfigs]:
    return await devices_db.get_all_devices(site_id)


async def get_device_by_id(site_id: int, device_id: int) -> DeviceWithConfigs:
    device = await devices_db.get_device_by_id(device_id, site_id)
    if device is None:
        raise NotFoundError(f"Device with ID {device_id} not found in site {site_id}")
    return device


async def create_device(device: DeviceCreateRequest, site_id: int) -> DeviceWithConfigs:
    return await devices_db.create_device(device, site_id=site_id)


async def update_device(
    device_id: int, device_update: DeviceUpdate, site_id: int
) -> DeviceWithConfigs:
    return await devices_db.update_device(device_id, device_update, site_id=site_id)


async def delete_device(device_id: int, site_id: int) -> Optional[DeviceWithConfigs]:
    return await devices_db.delete_device(device_id, site_id=site_id)
