"""Health check endpoints."""

from fastapi import APIRouter

from rtac_modbus_service.schemas.api_models import HealthResponse
from rtac_modbus_service.modbus.client import ModbusClient

router = APIRouter()

# Initialize Modbus client wrapper
modbus_client = ModbusClient()


@router.get("/health", response_model=HealthResponse)
@router.get("/healthz", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint that verifies connectivity and performs a small test read.
    
    Attempts to connect to the Modbus server and reads a single holding register
    at address 0 to confirm end-to-end communication is working.
    """
    ok, detail = modbus_client.health_check()
    
    return HealthResponse(
        ok=ok,
        host=modbus_client.host,
        port=modbus_client.port,
        unit_id=modbus_client.default_unit_id,
        detail=detail
    )


@router.get("/readyz")
async def readiness_check():
    """
    Readiness check endpoint.
    
    Returns 200 if the service is ready to accept requests.
    This endpoint does not check Modbus connectivity.
    """
    return {"status": "ready"}
