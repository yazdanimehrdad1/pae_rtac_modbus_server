"""Modbus read endpoints."""

from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, status

from rtac_modbus_service.schemas.api_models import ReadRequest, ReadResponse, RegisterData
from rtac_modbus_service.modbus.client import ModbusClient, translate_modbus_error
from rtac_modbus_service.utils.dataframe import load_register_map_from_csv

router = APIRouter()

# Initialize Modbus client wrapper
modbus_client = ModbusClient()


@router.post("/read", response_model=ReadResponse)
async def read_registers(request: ReadRequest):
    """
    Read Modbus registers or coils/discrete inputs.
    
    Supports four types of reads:
    - holding: Holding registers (function code 3)
    - input: Input registers (function code 4)
    - coils: Coils (function code 1)
    - discretes: Discrete inputs (function code 2)
    
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
        
        # for the response we want to map data to sel_751_register_map.csv  . So the response 
        # should be data = [{"name": "Voltage_L1", "value": data[0]}, {"name": "Current_L1", "value": data[1]}, {"name": "Power_Active", "value": data[2]}, {"name": "Status_Bit", "value": data[3]}]
        # so we need to load the register map from the csv file and map the data to the names
        csv_path = Path("config/sel_751_register_map.csv")
        register_map = load_register_map_from_csv(csv_path)
        
        # Create dictionary mapping register addresses to their data
        response_data = {}
        for point in register_map.points:
            # Check if this register is within the requested address range
            if request.address <= point.address < request.address + request.count:
                # Calculate the index in the data array
                data_index = point.address - request.address
                if 0 <= data_index < len(data):
                    response_data[point.address] = RegisterData(
                        name=point.name,
                        value=data[data_index],
                        Type=point.data_type if point.data_type else None
                    )
        return ReadResponse(
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

