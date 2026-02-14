"""Modbus read endpoints."""

from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, HTTPException, status

from schemas.api_models import ReadRequest, ReadResponse, RegisterData, SimpleReadResponse, RegisterValue
from helpers.modbus import translate_modbus_error
from modbus.client import ModbusClient
from modbus.modbus_utills import ModbusUtils
from utils.map_csv_to_json import json_to_register_map
from db.devices import get_device_by_id_internal, get_device_id_by_name_internal
from db.device_configs import get_configs_for_device
from cache.cache import CacheService
from config import settings
from logger import get_logger

router = APIRouter()

# Initialize logger
logger = get_logger(__name__)

# Initialize Modbus utils wrapper
modbus_utils = ModbusUtils(ModbusClient())

# Initialize cache service
cache_service = CacheService()

@router.post("/read", response_model=SimpleReadResponse)
async def read_registers(request: ReadRequest):
    """
    Read Modbus registers or coils/discrete inputs.
    
    Supports four types of reads:
    - holding: Holding registers (function code 3)
    - input: Input registers (function code 4)
    - coils: Coils (function code 1)
    - discretes: Discrete inputs (function code 2)
    
    Returns an array of {register: value} pairs in the data field.
    
    TODO: Add support for batch polling multiple addresses in a single request
    TODO: Add word/byte-order conversion helpers for 32-bit and 64-bit values
           (e.g., convert two 16-bit registers to a 32-bit float/integer)
    """
    try:
        # Use standardized functions based on register type
        device_id = request.device_id or settings.modbus_device_id
        
        host = request.host or settings.modbus_host
        port = request.port or settings.modbus_port

        if request.kind == "holding":
            data = modbus_utils.read_holding_registers(
                address=request.address,
                count=request.count,
                server_id=device_id,
                host=host,
                port=port
            )
        elif request.kind == "input":
            data = modbus_utils.read_input_registers(
                address=request.address,
                count=request.count,
                server_id=device_id,
                host=host,
                port=port
            )
        elif request.kind == "coils":
            data = modbus_utils.read_coils(
                address=request.address,
                count=request.count,
                server_id=device_id,
                host=host,
                port=port
            )
        elif request.kind == "discretes":
            data = modbus_utils.read_discrete_inputs(
                address=request.address,
                count=request.count,
                server_id=device_id,
                host=host,
                port=port
            )
        else:
            raise ValueError(f"Invalid kind: {request.kind}")
        
        # TODO: Add Prometheus metrics here
        # Example: modbus_reads_total.labels(kind=request.kind, status="success").inc()
        #         modbus_read_latency_seconds.labels(kind=request.kind).observe(elapsed_time)
        
        # Create array of register:value pairs
        response_data = []
        for i, value in enumerate(data):
            register_number = request.address + i
            response_data.append(RegisterValue(
                register_number=register_number,
                value=value
            ))
        
        return SimpleReadResponse(
            ok=True,
            timestamp=datetime.now(timezone.utc).isoformat(),
            kind=request.kind,
            address=request.address,
            count=request.count,
            device_id=request.device_id or settings.modbus_device_id,
            data=response_data
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        status_code, message = translate_modbus_error(e)
        raise HTTPException(status_code=status_code, detail=message)



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
            from schemas.db_models.models import DeviceResponse
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
        
        
        # Get device configs from database if device has a site_id
        json_data = None
        if device.site_id:
            try:
                configs = await get_configs_for_device(device.device_id, site_id=device.site_id)
                if configs:
                    json_data = {"registers": configs[0].points}
            except Exception as e:
                logger.warning(f"Error getting device configs for device {device.device_id}: {e}")
                json_data = None
        
        response_data = {}
        
        if json_data is not None:
            # Use register map to map data with names and metadata
            register_map = json_to_register_map(json_data)
            
            for point in register_map.points:
                # Check if this register is within the requested address range
                # Calculate the index in the data array
                data_index = point.address - poll_address
                if 0 <= data_index < len(data):
                    response_data[point.address] = RegisterData(
                        name=point.name,
                        value=data[data_index],
                        scale_factor=point.scale_factor,
                        unit=point.unit,
                        Type=point.data_type
                    )
        else:
            # No register map available - raise error
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Register map not found for device '{device_name}'. Device may not be mapped to a CSV file or CSV file does not exist."
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



