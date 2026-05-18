"""
Device configs controller.

Sits between the router and the helper layer.
All CRUD operations go through helpers/device_configs/device_config_crud.py,
which in turn calls db.device_configs.

To change CRUD behaviour in the future, only this file needs to be updated;
the router remains unchanged.
"""

from typing import Optional

from helpers.device_configs.device_config_crud import (
    create_config_db,
    get_config_db,
    update_config_db,
    delete_config_db,
)
from logger import get_logger
from schemas.api_models import ConfigCreateRequest, ConfigResponse, ConfigUpdate

logger = get_logger(__name__)


async def create_config(
    site_id: int, device_id: int, config: ConfigCreateRequest
) -> ConfigResponse:
    return await create_config_db(site_id, device_id, config)


async def get_config(config_id: str) -> Optional[ConfigResponse]:
    return await get_config_db(config_id)


async def update_config(config_id: str, update: ConfigUpdate) -> Optional[ConfigResponse]:
    return await update_config_db(config_id, update)


async def delete_config(config_id: str) -> bool:
    return await delete_config_db(config_id)
