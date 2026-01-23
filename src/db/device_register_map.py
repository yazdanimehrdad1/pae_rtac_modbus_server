"""
Legacy device register map database operations.

Register maps are deprecated in favor of device_configs.
"""

from typing import Optional, Dict, Any

from logger import get_logger

logger = get_logger(__name__)

async def get_register_map(device_id: int, site_id: str) -> Optional[Dict[str, Any]]:
    logger.warning("register_map is deprecated; use device_configs instead")
    return None




async def create_register_map(site_id: str, device_id: int, register_map: Dict[str, Any]) -> bool:
    logger.warning("register_map is deprecated; use device_configs instead")
    return False

async def update_register_map(site_id: str, device_id: int, register_map: Dict[str, Any]) -> bool:
    logger.warning("register_map is deprecated; use device_configs instead")
    return False


async def delete_register_map(site_id: str, device_id: int) -> bool:
    logger.warning("register_map is deprecated; use device_configs instead")
    return False



