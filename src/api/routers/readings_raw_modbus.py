"""Raw Modbus read endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status

from schemas.api_models import ReadRequest, SimpleReadResponse, RegisterValue
from helpers.modbus import translate_modbus_error
from modbus.client import ModbusClient
from modbus.modbus_utills import ModbusUtils
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
