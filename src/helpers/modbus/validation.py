"""
Validation helpers for Modbus data mapping.
"""

from typing import Optional

from logger import get_logger

logger = get_logger(__name__)


def validate_point_mapping_fields(
    point_index: int,
    point_name: str,
    point_address: Optional[int],
    point_size: Optional[int],
    poll_start_address: int,
    read_length: int,
) -> bool:
    if point_address is None:
        logger.warning(
            "Skipping point %s ('%s'): missing required field 'point_address'",
            point_index,
            point_name,
        )
        return False
    if point_size is None or point_size < 1:
        logger.warning(
            "Skipping point %s ('%s') (address=%s): invalid or missing 'size' field (got %s)",
            point_index,
            point_name,
            point_address,
            point_size,
        )
        return False
    data_index = point_address - poll_start_address
    if data_index < 0:
        logger.debug(
            "Skipping point %s ('%s') (address=%s size=%s ): "
            "address is before poll start address %s",
            point_index,
            point_name,
            point_address,
            point_size,
            poll_start_address,
        )
        return False
    if data_index + point_size > read_length:
        logger.debug(
            "Skipping point %s ('%s') (address=%s, size=%s): "
            "extends beyond read data range (read %s values, "
            "need index %s to %s)",
            point_index,
            point_name,
            point_address,
            point_size,
            read_length,
            data_index,
            data_index + point_size - 1,
        )
        return False
    return True
