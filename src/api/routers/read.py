"""Modbus read endpoints."""

from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, HTTPException, status

from schemas.api_models import ReadRequest, ReadResponse, RegisterData, SimpleReadResponse, RegisterValue
from modbus.client import ModbusClient, translate_modbus_error
from modbus.modbus_utills import ModbusUtils
from utils.map_csv_to_json import json_to_register_map, get_register_map_for_device
from config import settings

router = APIRouter()

# Initialize Modbus utils wrapper
modbus_utils = ModbusUtils(ModbusClient())

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
        
        if request.kind == "holding":
            data = modbus_utils.read_holding_registers(
                address=request.address,
                count=request.count,
                device_id=device_id
            )
        elif request.kind == "input":
            data = modbus_utils.read_input_registers(
                address=request.address,
                count=request.count,
                device_id=device_id
            )
        elif request.kind == "coils":
            data = modbus_utils.read_coils(
                address=request.address,
                count=request.count,
                device_id=device_id
            )
        elif request.kind == "discretes":
            data = modbus_utils.read_discrete_inputs(
                address=request.address,
                count=request.count,
                device_id=device_id
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
    """Read the main data from the 751 (hardcoded to address 1400, count 100)."""
    try:
        data = modbus_utils.read_device_registers_main_sel_751()
        
        # Get register map from database (with CSV fallback if not in DB)
        device_name = "main-sel-751"
        json_data = await get_register_map_for_device(device_name)
        
        response_data = {}
        
        if json_data is not None:
            # Use register map to map data with names and metadata
            register_map = json_to_register_map(json_data)
            
            for point in register_map.points:
                # Check if this register is within the requested address range
                # Calculate the index in the data array
                data_index = point.address - 1400
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
            kind="holding",
            address=1400,
            count=100,
            device_id=1,
            data=response_data
        )
    except Exception as e:
        status_code, message = translate_modbus_error(e)
        raise HTTPException(status_code=status_code, detail=message)



