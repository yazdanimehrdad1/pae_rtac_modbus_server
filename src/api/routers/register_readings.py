"""Register readings endpoints."""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Query

from db.register_readings import (
    get_all_readings,
    get_latest_reading,
    get_latest_readings_for_device
)
from db.devices import get_device_by_id
from cache.cache import CacheService
from logger import get_logger
from schemas.db_models.models import DeviceResponse

router = APIRouter(prefix="/register_readings", tags=["register_readings"])
logger = get_logger(__name__)

# Initialize cache service
cache_service = CacheService()


async def get_device_with_cache(device_id: int) -> DeviceResponse:
    """
    Get device by ID with cache-first lookup.
    
    Args:
        device_id: Device ID (database primary key)
        
    Returns:
        DeviceResponse if found
        
    Raises:
        HTTPException: If device not found
    """
    # First try cache
    cache_key = f"device:id:{device_id}"
    cached_device = await cache_service.get(cache_key)
    
    if cached_device is not None:
        # Device found in cache, reconstruct Pydantic model from dict
        logger.debug(f"Device ID {device_id} found in cache")
        return DeviceResponse(**cached_device)
    else:
        # Not in cache, query database
        logger.debug(f"Device ID {device_id} not in cache, querying database")
        device = await get_device_by_id(device_id)
        if device is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Device with ID {device_id} not found"
            )
        return device


@router.get("/device/{device_id}/latest")
async def get_device_latest_readings(
    device_id: int,
    register_addresses: Optional[str] = Query(None, description="Comma-separated list of register addresses (e.g., '100,101,102')")
):
    """
    Get latest readings for all registers (or specific registers) of a device.
    
    Args:
        device_id: Device ID
        register_addresses: Optional comma-separated list of register addresses to filter
        
    Returns:
        List of latest readings, one per register
        
    Raises:
        HTTPException: If device not found
    """
    try:
        # Verify device exists (cache-first lookup)
        device = await get_device_with_cache(device_id)
        
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
        readings = await get_latest_readings_for_device(device_id, register_list)
        
        return {
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


@router.get("/device/{device_id}/register/{register_address}/latest")
async def get_register_latest_reading(device_id: int, register_address: int):
    """
    Get the latest reading for a specific register.
    
    Args:
        device_id: Device ID
        register_address: Register address
        
    Returns:
        Latest reading for the register
        
    Raises:
        HTTPException: If device not found or reading not found
    """
    try:
        # Verify device exists (cache-first lookup)
        device = await get_device_with_cache(device_id)
        
        # Get latest reading
        reading = await get_latest_reading(device_id, register_address)
        
        if reading is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No readings found for device {device_id}, register {register_address}"
            )
        
        return reading
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting latest reading for device {device_id}, register {register_address}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve latest reading"
        )


@router.get("/device/{device_id}/register/{register_address}")
async def get_register_time_series(
    device_id: int,
    register_address: int,
    start_time: Optional[str] = Query(None, description="Start time in ISO format (e.g., '2025-01-18T08:00:00Z')"),
    end_time: Optional[str] = Query(None, description="End time in ISO format (e.g., '2025-01-18T09:00:00Z')"),
    limit: Optional[int] = Query(1000, ge=1, le=10000, description="Maximum number of readings to return")
):
    """
    Get time-series data for a specific register.
    
    Args:
        device_id: Device ID
        register_address: Register address
        start_time: Optional start time (ISO format)
        end_time: Optional end time (ISO format)
        limit: Maximum number of readings to return (default: 1000, max: 10000)
        
    Returns:
        List of readings ordered by timestamp (ascending for time-series)
        
    Raises:
        HTTPException: If device not found or invalid time format
    """
    try:
        # Verify device exists (cache-first lookup)
        device = await get_device_with_cache(device_id)
        
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
        
        # Get readings
        readings = await get_all_readings(
            device_id=device_id,
            register_address=register_address,
            start_time=start_dt,
            end_time=end_dt,
            limit=limit
        )
        
        # Reverse order for time-series (oldest first)
        readings.reverse()
        
        return {
            "device_id": device_id,
            "device_name": device.name,
            "register_address": register_address,
            "readings": readings,
            "count": len(readings)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting time-series for device {device_id}, register {register_address}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve time-series data"
        )


@router.get("/device/{device_id}/registers")
async def get_multiple_registers_time_series(
    device_id: int,
    register_addresses: str = Query(..., description="Comma-separated list of register addresses (e.g., '100,101,102')"),
    start_time: Optional[str] = Query(None, description="Start time in ISO format (e.g., '2025-01-18T08:00:00Z')"),
    end_time: Optional[str] = Query(None, description="End time in ISO format (e.g., '2025-01-18T09:00:00Z')"),
    limit: Optional[int] = Query(1000, ge=1, le=10000, description="Maximum number of readings per register")
):
    """
    Get time-series data for multiple registers.
    
    Args:
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
        device = await get_device_with_cache(device_id)
        
        # Parse register addresses
        try:
            register_list = [int(addr.strip()) for addr in register_addresses.split(',')]
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid register_addresses format. Expected comma-separated integers (e.g., '100,101,102')"
            )
        
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
        result = {}
        for register_address in register_list:
            readings = await get_all_readings(
                device_id=device_id,
                register_address=register_address,
                start_time=start_dt,
                end_time=end_dt,
                limit=limit
            )
            # Reverse order for time-series (oldest first)
            readings.reverse()
            result[str(register_address)] = readings
        
        return {
            "device_id": device_id,
            "device_name": device.name,
            "register_addresses": register_list,
            "readings": result,
            "count": sum(len(readings) for readings in result.values())
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting time-series for device {device_id}, registers {register_addresses}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve time-series data"
        )


@router.get("")
async def get_readings(
    device_id: Optional[int] = Query(None, description="Filter by device ID"),
    register_address: Optional[int] = Query(None, description="Filter by register address"),
    start_time: Optional[str] = Query(None, description="Start time in ISO format (e.g., '2025-01-18T08:00:00Z')"),
    end_time: Optional[str] = Query(None, description="End time in ISO format (e.g., '2025-01-18T09:00:00Z')"),
    limit: Optional[int] = Query(100, ge=1, le=10000, description="Maximum number of readings to return"),
    offset: Optional[int] = Query(0, ge=0, description="Number of readings to skip (for pagination)")
):
    """
    Get all register readings with optional filters.
    
    Args:
        device_id: Optional filter by device ID
        register_address: Optional filter by register address
        start_time: Optional start time (ISO format)
        end_time: Optional end time (ISO format)
        limit: Maximum number of readings to return (default: 100, max: 10000)
        offset: Number of readings to skip for pagination (default: 0)
        
    Returns:
        List of readings matching the filters
        
    Raises:
        HTTPException: If invalid time format
    """
    try:
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
        
        # Get readings
        readings = await get_all_readings(
            device_id=device_id,
            register_address=register_address,
            start_time=start_dt,
            end_time=end_dt,
            limit=limit,
            offset=offset
        )
        
        return {
            "readings": readings,
            "count": len(readings),
            "limit": limit,
            "offset": offset
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting readings: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve readings"
        )

