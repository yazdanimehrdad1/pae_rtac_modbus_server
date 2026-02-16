"""Register readings endpoints."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, status, Query

from db.register_readings import (
    get_all_readings,
    get_latest_reading,
    get_latest_readings_for_device
)
from helpers.device_points import get_device_points
from helpers.devices import get_device_cache_db
from logger import get_logger

router = APIRouter(prefix="/register_readings", tags=["register_readings"])
logger = get_logger(__name__)


@router.get("/site/{site_id}/device/{device_id}/latest")
async def get_device_latest_readings(
    site_id: int,
    device_id: int,
    register_addresses: Optional[str] = Query(None, description="Comma-separated list of register addresses (e.g., '100,101,102')")
):
    """
    Get latest readings for all registers (or specific registers) of a device.
    
    Args:
        site_id: Site ID (4-digit number)
        device_id: Device ID
        register_addresses: Optional comma-separated list of register addresses to filter
        
    Returns:
        List of latest readings, one per register
        
    Raises:
        HTTPException: If device not found
    """
    try:
        # Verify device exists (cache-first lookup)
        device = await get_device_cache_db(site_id, device_id)
        
        # Parse register_addresses if provided
        register_list = None
        if register_addresses:
            try:
                register_list = [int(addr.strip()) for addr in register_addresses.split(',')]
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid register_addresses format. Expected comma-separated integers (e.g., '100,101,102')"
                )
        
        # Get latest readings
        try:
            readings = await get_latest_readings_for_device(device_id, site_id, register_list)
        except ValueError as e:
            # Site doesn't exist or device doesn't belong to site
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        
        return {
            "site_id": site_id,
            "device_id": device_id,
            "device_name": device.name,
            "readings": readings,
            "count": len(readings)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting latest readings for device {device_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve latest readings"
        )



@router.get("/timeseries/site/{site_id}/device/{device_id}")
async def get_multiple_registers_time_series(
    site_id: int,
    device_id: int,
    register_addresses: Optional[str] = Query(
        None,
        description="Comma-separated list of register addresses (e.g., '100,101,102'). If omitted, returns all points."
    ),
    start_time: Optional[str] = Query(None, description="Start time in ISO format (e.g., '2025-01-18T08:00:00Z')"),
    end_time: Optional[str] = Query(None, description="End time in ISO format (e.g., '2025-01-18T09:00:00Z')"),
    limit: Optional[int] = Query(1000, ge=1, le=10000, description="Maximum number of readings per register")
):
    """
    Get time-series data for multiple registers.
    
    Args:
        site_id: Site ID (4-digit number)
        device_id: Device ID
        register_addresses: Comma-separated list of register addresses (e.g., '100,101,102')
        start_time: Optional start time (ISO format)
        end_time: Optional end time (ISO format)
        limit: Maximum number of readings per register (default: 1000, max: 10000)
        
    Returns:
        Dictionary with readings grouped by register address
        
    Raises:
        HTTPException: If device not found or invalid parameters
    """
    try:
        # Verify device exists (cache-first lookup)
        device = await get_device_cache_db(site_id, device_id)
        
        # Get point metadata for this device
        device_points = await get_device_points(site_id, device_id)
        points_by_address = {point.address: point for point in device_points}

        # Parse register addresses (optional)
        if register_addresses:
            try:
                register_list = [int(addr.strip()) for addr in register_addresses.split(',')]
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid register_addresses format. Expected comma-separated integers (e.g., '100,101,102')"
                )
        else:
            register_list = sorted(points_by_address.keys())

        # Parse time strings to datetime objects
        start_dt = None
        end_dt = None
        
        if start_time:
            try:
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid start_time format. Expected ISO format (e.g., '2025-01-18T08:00:00Z')"
                )
        
        if end_time:
            try:
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid end_time format. Expected ISO format (e.g., '2025-01-18T09:00:00Z')"
                )
        
        # Get readings for each register
        result: Dict[str, Dict[str, Any]] = {}
        for register_address in register_list:
            try:
                readings = await get_all_readings(
                    site_id=site_id,
                    device_id=device_id,
                    register_address=register_address,
                    start_time=start_dt,
                    end_time=end_dt,
                    limit=limit
                )
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=str(e)
                )

            address_points = [p for p in device_points if p.address == register_address]
            if not address_points:
                logger.warning(
                    "No DevicePoint metadata found for device %s, address %s",
                    device_id,
                    register_address
                )
                continue

            # Prefer the non-derived (base) point for metadata when available
            base_point = next((p for p in address_points if not p.is_derived), address_points[0])

            # Reverse order for time-series (oldest first)
            readings.reverse()

            readings_by_point: Dict[int, List[Dict[str, Any]]] = {}
            for reading in readings:
                readings_by_point.setdefault(reading["device_point_id"], []).append({
                    "timestamp": reading["timestamp"],
                    "derived_value": reading["derived_value"]
                })

            entry: Dict[str, Any] = {
                "device_point_id": base_point.id,
                "register_address": base_point.address,
                "name": base_point.name,
                "data_type": base_point.data_type,
                "unit": base_point.unit,
                "scale_factor": base_point.scale_factor,
                "is_derived": base_point.is_derived
            }

            for point in address_points:
                series_key = f"{point.name}_timeseries"
                entry[series_key] = readings_by_point.get(point.id, [])

            result[str(register_address)] = entry
        
        total_timeseries_count = 0
        for entry in result.values():
            for key, value in entry.items():
                if key.endswith("_timeseries"):
                    total_timeseries_count += len(value)

        return {
            "site_id": site_id,
            "device_id": device_id,
            "device_name": device.name,
            "register_addresses": register_list,
            "readings": result,
            "count": total_timeseries_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting time-series for device {device_id}, registers {register_addresses}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve time-series data"
        )


# @router.get("")
# async def get_readings(
#     site_id: int = Query(..., description="Site ID (4-digit number) - required"),
#     device_id: int = Query(..., description="Device ID - required"),
#     register_address: Optional[int] = Query(None, description="Filter by register address"),
#     start_time: Optional[str] = Query(None, description="Start time in ISO format (e.g., '2025-01-18T08:00:00Z')"),
#     end_time: Optional[str] = Query(None, description="End time in ISO format (e.g., '2025-01-18T09:00:00Z')"),
#     limit: Optional[int] = Query(100, ge=1, le=10000, description="Maximum number of readings to return")
# ):
#     """
#     Get all register readings with optional filters.
    
#     Args:
#         site_id: Site ID (UUID) - required
#         device_id: Device ID - required
#         register_address: Optional filter by register address
#         start_time: Optional start time (ISO format)
#         end_time: Optional end time (ISO format)
#         limit: Maximum number of readings to return (default: 100, max: 10000)
        
#     Returns:
#         List of readings matching the filters
        
#     Raises:
#         HTTPException: If invalid time format
#     """
#     try:
#         # Parse time strings to datetime objects
#         start_dt = None
#         end_dt = None
        
#         if start_time:
#             try:
#                 start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
#             except ValueError:
#                 raise HTTPException(
#                     status_code=status.HTTP_400_BAD_REQUEST,
#                     detail=f"Invalid start_time format. Expected ISO format (e.g., '2025-01-18T08:00:00Z')"
#                 )
        
#         if end_time:
#             try:
#                 end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
#             except ValueError:
#                 raise HTTPException(
#                     status_code=status.HTTP_400_BAD_REQUEST,
#                     detail=f"Invalid end_time format. Expected ISO format (e.g., '2025-01-18T09:00:00Z')"
#                 )
        
#         # Get readings
#         try:
#             readings = await get_all_readings(
#                 site_id=site_id,
#                 device_id=device_id,
#                 register_address=register_address,
#                 start_time=start_dt,
#                 end_time=end_dt,
#                 limit=limit
#             )
#         except ValueError as e:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail=str(e)
#             )
        
#         return {
#             "site_id": site_id,
#             "readings": readings,
#             "count": len(readings),
#             "limit": limit
#         }
        
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Error getting readings: {e}", exc_info=True)
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Failed to retrieve readings"
#         )

