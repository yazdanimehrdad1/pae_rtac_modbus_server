from typing import Any, Dict, List, Tuple

from fastapi import HTTPException, status

from db.register_readings import get_latest_readings_for_device
from logger import get_logger
from schemas.api_models.types import (
    LatestDevicePointReadingModel,
    PointReadSeriesItemModel,
)
from schemas.db_models.orm_models import DevicePoint
from utils.create_calculated_points import create_calculated_points

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

    readings_by_point: Dict[int, List[PointReadSeriesItemModel]] = {}
    for reading in readings:
        reading_model = LatestDevicePointReadingModel(**reading)
        calculated_point = create_calculated_points(reading_model)
        readings_by_point.setdefault(reading_model.device_point_id, []).append(
            PointReadSeriesItemModel(
                timestamp=calculated_point.timestamp,
                raw_value=reading.get("raw_value", reading_model.derived_value),
                calculated_value=calculated_point.calculated_value,
            )
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

        series_key = f"{base_point.name}_latest"
        series = readings_by_point.get(base_point.id, [])
        entry[series_key] = [item.model_dump() for item in series]
        total_readings_count += len(series)

        result[str(register_address)] = entry

    return result, total_readings_count
