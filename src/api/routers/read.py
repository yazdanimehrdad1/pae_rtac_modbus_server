"""Modbus read endpoints."""

from datetime import datetime, timezone
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException, status

from schemas.api_models import ReadRequest, ReadResponse, RegisterData, SimpleReadResponse, RegisterValue
from modbus.client import ModbusClient, translate_modbus_error
from utils.dataframe import load_register_map_from_csv

router = APIRouter()

# Initialize Modbus client wrapper
modbus_client = ModbusClient()


@router.get("/read/register_map", response_model=List[RegisterData])
async def get_register_map():
    """Get the register map from the CSV file."""
    csv_path = Path("config/sel_751_register_map.csv")
    register_map = load_register_map_from_csv(csv_path)
    return register_map


@router.get("/read/main-751", response_model=ReadResponse)
async def read_751_main_data():
    """Read the main data from the 751 (hardcoded to address 1400, count 100)."""
    try:
        data = modbus_client.read_registers(
            kind="holding",
            address=1400,
            count=100,
            unit_id=1
        )
        
        # Map data to register map for better response
        csv_path = Path("config/sel_751_register_map.csv")
        register_map = load_register_map_from_csv(csv_path)
        
        # Create list of register data
        response_data = {}
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
        return ReadResponse(
            ok=True,
            timestamp=datetime.now(timezone.utc).isoformat(),
            kind="holding",
            address=1400,
            count=100,
            unit_id=1,
            data=response_data
        )
    except Exception as e:
        status_code, message = translate_modbus_error(e)
        raise HTTPException(status_code=status_code, detail=message)



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
        data = modbus_client.read_registers(
            kind=request.kind,
            address=request.address,
            count=request.count,
            unit_id=request.unit_id
        )
        
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
            unit_id=request.unit_id or modbus_client.default_unit_id,
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

