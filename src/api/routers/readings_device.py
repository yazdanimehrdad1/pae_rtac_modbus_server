"""Modbus read endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status

from schemas.api_models import ReadResponse, RegisterData
from helpers.modbus import translate_modbus_error
from services.modbus.client import ModbusClient
from services.modbus.modbus_utills import ModbusUtils
from db.devices import get_device_by_id_internal, get_device_id_by_name_internal
from cache.cache import CacheService
from config import settings
from logger import get_logger
from helpers.device_reads.create_calculated_points import json_to_register_map

router = APIRouter()

# Initialize logger
logger = get_logger(__name__)

# Initialize Modbus utils wrapper
modbus_utils = ModbusUtils(ModbusClient())

# Initialize cache service
cache_service = CacheService()

@router.get("/read/main-sel-751", response_model=ReadResponse)
async def read_main_sel_751_data():
    """Read the main data from the 751 device using device-specific configuration."""
    device_name = "main-sel-751"
    
    try:
        # Get device from database to get host/port configuration
        # First try cache
        cache_key = f"device:{device_name}"
        cached_device = await cache_service.get(cache_key)
        
        if cached_device is not None:
            # Device found in cache, reconstruct Pydantic model from dict
            logger.debug(f"Device '{device_name}' found in cache")
            from schemas.api_models import DeviceResponse
            device = DeviceResponse(**cached_device)
        else:
            # Not in cache, query database
            logger.debug(f"Device '{device_name}' not in cache, querying database")
            db_device_id = await get_device_id_by_name_internal(device_name)
            if db_device_id is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Device '{device_name}' not found in database"
                )
            device = await get_device_by_id_internal(db_device_id)
            if device is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Device '{device_name}' not found in database"
                )
        
        # Use main SEL 751 polling configuration
        poll_address = settings.main_sel_751_poll_address
        poll_count = settings.main_sel_751_poll_count
        poll_kind = settings.main_sel_751_poll_kind
        modbus_device_id = settings.modbus_device_id
        
        # Read Modbus registers using device-specific host/port
        if poll_kind == "holding":
            data = modbus_utils.read_holding_registers(
                address=poll_address,
                count=poll_count,
                server_id=modbus_device_id,
                host=device.host,
                port=device.port
            )
        elif poll_kind == "input":
            data = modbus_utils.read_input_registers(
                address=poll_address,
                count=poll_count,
                server_id=modbus_device_id,
                host=device.host,
                port=device.port
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported register kind '{poll_kind}' for device '{device_name}'"
            )
        
        
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="This endpoint previously used device configs for register naming. Configs have been removed — use device points instead."
        )
        return ReadResponse(
            ok=True,
            timestamp=datetime.now(timezone.utc).isoformat(),
            kind=poll_kind,
            address=poll_address,
            count=poll_count,
            device_id=modbus_device_id,
            data=response_data
        )
    except HTTPException:
        raise
    except Exception as e:
        # Try to get device info for better error messages
        try:
            db_device_id = await get_device_id_by_name_internal(device_name)
            if db_device_id:
                device = await get_device_by_id_internal(db_device_id)
                if device:
                    status_code, message = translate_modbus_error(
                        e,
                        host=device.host,
                        port=device.port
                    )
                else:
                    status_code, message = translate_modbus_error(e)
            else:
                status_code, message = translate_modbus_error(e)
        except:
            status_code, message = translate_modbus_error(e)
        raise HTTPException(status_code=status_code, detail=message)



