"""Health check endpoints."""

from fastapi import APIRouter

from schemas.api_models import HealthResponse
from modbus.client import ModbusClient
from cache.connection import check_redis_health
from db.connection import check_db_health

router = APIRouter()

# Initialize Modbus client wrapper
modbus_client = ModbusClient()

#@healthz is for the api health check while health_modbus_client is checking the health of mobus can read from the modbus server
#  

@router.get("/healthz", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint that verifies API is running.
    
    Returns basic health status without performing Modbus operations.
    """
    return HealthResponse(
        ok=True,
        host=modbus_client.host,
        port=modbus_client.port,
        unit_id=modbus_client.default_unit_id,
        detail="API is healthy"
    )

@router.get("/health_modbus_client", response_model=HealthResponse)
async def health_modbus_client():
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

@router.get("/redis_health")
async def redis_health():
    """
    Redis health check endpoint.
    """
    return await check_redis_health()


@router.get("/db_health")
async def db_health():
    """
    Database health check endpoint.
    """
    return await check_db_health()
