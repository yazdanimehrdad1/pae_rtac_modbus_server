from typing import Any, Dict, List, Tuple

from fastapi import HTTPException, status

from db.register_readings import get_latest_readings_for_device
from log_config import get_logger
from schemas.db_models.orm_models import DevicePoint

logger = get_logger(__name__)

async def points_latest_readings_response_controller(
    device_id: int,
    site_id: str,
    points_by_address: Dict[int, DevicePoint],
    register_list: List[int],
) -> Tuple[Dict[str, Dict[str, Any]], int]:
    try:
        readings = await get_latest_readings_for_device(
            device_id=device_id,
            site_id=site_id,
            register_addresses=register_list,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    readings_by_point: Dict[int, List[Dict[str, Any]]] = {}
    for reading in readings:
        readings_by_point.setdefault(reading["device_point_id"], []).append(
            {
                "timestamp": reading["timestamp"],
                "derived_value": reading["derived_value"],
            }
        )

    result: Dict[str, Dict[str, Any]] = {}
    total_readings_count = 0
    for register_address in register_list:
        base_point = points_by_address.get(register_address)
        if base_point is None:
            logger.warning(
                "No DevicePoint metadata found for device %s, address %s",
                device_id,
                register_address,
            )
            continue
        entry: Dict[str, Any] = {
            "device_point_id": base_point.id,
            "register_address": base_point.address,
            "name": base_point.name,
            "data_type": base_point.data_type,
            "unit": base_point.unit,
            "scale_factor": base_point.scale_factor,
        }

        series_key = f"{base_point.name}_reads"
        series = readings_by_point.get(base_point.id, [])
        entry[series_key] = series
        total_readings_count += len(series)

        result[str(register_address)] = entry

    return result, total_readings_count
