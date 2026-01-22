"""
FastAPI Microservice for Modbus TCP Communication

This service provides REST endpoints to interact with a Modbus TCP server.
It uses pymodbus for Modbus protocol communication and follows best practices
for connection management and error handling.
"""

from typing import Optional, Literal

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

from modbus_client import ModbusClient, translate_modbus_error

app = FastAPI(
    title="Modbus TCP Service",
    description="REST API for Modbus TCP communication",
    version="1.0.0"
)

# Initialize Modbus client wrapper
modbus = ModbusClient()


# Pydantic models for request/response validation
class ReadRequest(BaseModel):
    """Request model for reading Modbus registers"""
    kind: Literal["holding", "input", "coils", "discretes"] = Field(
        ..., description="Type of register to read"
    )
    address: int = Field(..., ge=0, le=65535, description="Starting address")
    count: int = Field(..., ge=1, le=2000, description="Number of registers/bits to read")
    device_id: Optional[int] = Field(None, ge=1, le=255, description="Modbus unit/slave ID (optional)")


class ReadResponse(BaseModel):
    """Response model for read operations"""
    ok: bool
    kind: str
    address: int
    count: int
    device_id: int
    data: list


class HealthResponse(BaseModel):
    """Response model for health check"""
    ok: bool
    host: str
    port: int
    device_id: int
    detail: Optional[str] = None


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint that verifies connectivity and performs a small test read.
    
    Attempts to connect to the Modbus server and reads a single holding register
    at address 0 to confirm end-to-end communication is working.
    """
    ok, detail = modbus.modbus_server_health_check()
    
    return HealthResponse(
        ok=ok,
        host=modbus.host,
        port=modbus.port,
        device_id=modbus.default_device_id,
        detail=detail
    )


@app.post("/read", response_model=ReadResponse)
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
        data = modbus.read_registers(
            kind=request.kind,
            address=request.address,
            count=request.count,
            device_id=request.device_id
        )
        
        # TODO: Add Prometheus metrics here
        # Example: modbus_reads_total.labels(kind=request.kind, status="success").inc()
        #         modbus_read_latency_seconds.labels(kind=request.kind).observe(elapsed_time)
        
        return ReadResponse(
            ok=True,
            kind=request.kind,
            address=request.address,
            count=request.count,
            device_id=request.device_id or modbus.default_device_id,
            data=data
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        status_code, message = translate_modbus_error(e)
        raise HTTPException(status_code=status_code, detail=message)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "modbus_service:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
