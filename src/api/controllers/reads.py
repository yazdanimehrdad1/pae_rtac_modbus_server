from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status

from db.register_readings import (
    get_all_readings,
    get_latest_readings_for_device,
    get_latest_readings_for_device_n,
)
from helpers.date_time import parse_iso_datetime
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


async def points_time_series_response_controller(
    device_id: int,
    site_id: int,
    device_points: List[DevicePoint],
    register_list: List[int],
    start_time: Optional[str],
    end_time: Optional[str],
    limit: Optional[int],
) -> Tuple[Dict[str, Dict[str, Any]], int]:
    start_dt = parse_iso_datetime(start_time) if start_time else None
    end_dt = parse_iso_datetime(end_time) if end_time else None
    if start_time and start_dt is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid start_time format. Expected ISO format "
                "(e.g., '2025-01-18T08:00:00Z')"
            ),
        )
    if end_time and end_dt is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid end_time format. Expected ISO format "
                "(e.g., '2025-01-18T09:00:00Z')"
            ),
        )

    points_by_id = {point.id: point for point in device_points}
    points_by_address = {point.address: point for point in device_points}

    result: Dict[str, Dict[str, Any]] = {}
    for register_address in register_list:
        try:
            readings = await get_all_readings(
                site_id=site_id,
                device_id=device_id,
                register_address=register_address,
                start_time=start_dt,
                end_time=end_dt,
                limit=limit,
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            ) from exc

        base_point = points_by_address.get(register_address)
        if base_point is None:
            logger.warning(
                "No DevicePoint metadata found for device %s, address %s",
                device_id,
                register_address,
            )
            continue

        readings_by_point: Dict[int, List[PointReadSeriesItemModel]] = {}
        for reading in readings:
            point = points_by_id.get(reading["device_point_id"])
            if point is None:
                continue
            reading_model = LatestDevicePointReadingModel(
                device_point_id=point.id,
                register_address=point.address,
                name=point.name,
                data_type=point.data_type,
                unit=point.unit,
                scale_factor=point.scale_factor,
                is_derived=point.is_derived,
                timestamp=reading["timestamp"],
                derived_value=reading["derived_value"],
                bitfield_detail=point.bitfield_detail,
                enum_detail=point.enum_detail,
            )
            calculated_point = create_calculated_points(reading_model)
            readings_by_point.setdefault(point.id, []).append(
                PointReadSeriesItemModel(
                    timestamp=calculated_point.timestamp,
                    raw_value=reading.get("raw_value", reading["derived_value"]),
                    calculated_value=calculated_point.calculated_value,
                )
            )

        entry: Dict[str, Any] = {
            "device_point_id": base_point.id,
            "register_address": base_point.address,
            "name": base_point.name,
            "data_type": base_point.data_type,
            "unit": base_point.unit,
            "scale_factor": base_point.scale_factor,
            "is_derived": base_point.is_derived,
        }

        address_points = [p for p in device_points if p.address == register_address]
        for point in address_points:
            series_key = f"{point.name}_timeseries"
            series = readings_by_point.get(point.id, [])
            entry[series_key] = [item.model_dump() for item in series]

        result[str(register_address)] = entry

    total_timeseries_count = 0
    for entry in result.values():
        for key, value in entry.items():
            if key.endswith("_timeseries"):
                total_timeseries_count += len(value)

    return result, total_timeseries_count


async def points_latest_readings_n_response_controller(
    device_id: int,
    site_id: int,
    latest_n: int,
    register_list: Optional[List[int]],
) -> List[Dict[str, Any]]:
    try:
        readings = await get_latest_readings_for_device_n(
            device_id=device_id,
            site_id=site_id,
            latest_n=latest_n,
            register_addresses=register_list,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return readings
