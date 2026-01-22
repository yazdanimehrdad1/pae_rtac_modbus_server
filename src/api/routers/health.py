"""Health check endpoints."""

from typing import Dict, Any, Optional
from fastapi import APIRouter

from sqlalchemy import text

from schemas.api_models import HealthResponse
from modbus.client import ModbusClient
from cache.connection import check_redis_health, get_redis_client
from db.connection import check_db_health, get_async_engine, get_db_pool
from config import settings

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
        device_id=modbus_client.default_server_id,
        detail="API is healthy"
    )

@router.get("/health_modbus_client", response_model=HealthResponse)
async def health_modbus_client():
    """
    Health check endpoint that verifies connectivity and performs a small test read.
    
    Attempts to connect to the Modbus server and reads a single holding register
    at address 0 to confirm end-to-end communication is working.
    """
    ok, detail = modbus_client.modbus_server_health_check()
    return HealthResponse(
        ok=ok,
        host=modbus_client.host,
        port=modbus_client.port,
        device_id=modbus_client.default_server_id,
        detail=detail
    )

@router.get("/redis_health")
async def redis_health() -> Dict[str, Any]:
    """
    Redis health check endpoint with detailed information.
    
    Returns:
        Dictionary containing Redis connection status, configuration, and server information
    """
    try:
        client = await get_redis_client()
        
        # Test connection
        ping_result = await client.ping()
        
        # Get Redis server info
        info = await client.info()
        
        # Get connection pool info
        pool = client.connection_pool
        pool_info = {
            "max_connections": pool.max_connections,
            "connection_kwargs": {
                "host": pool.connection_kwargs.get("host"),
                "port": pool.connection_kwargs.get("port"),
                "db": pool.connection_kwargs.get("db"),
            }
        }
        
        return {
            "status": "healthy" if ping_result else "unhealthy",
            "connected": ping_result,
            "configuration": {
                "host": settings.redis_host,
                "port": settings.redis_port,
                "db": settings.redis_db,
                "max_connections": settings.redis_max_connections,
                "health_check_interval": settings.redis_health_check_interval,
            },
            "server_info": {
                "redis_version": info.get("redis_version"),
                "used_memory_human": info.get("used_memory_human"),
                "used_memory_peak_human": info.get("used_memory_peak_human"),
                "connected_clients": info.get("connected_clients"),
                "total_commands_processed": info.get("total_commands_processed"),
                "keyspace": {
                    f"db{settings.redis_db}": info.get(f"db{settings.redis_db}", "N/A")
                }
            },
            "connection_pool": pool_info
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "connected": False,
            "error": str(e),
            "configuration": {
                "host": settings.redis_host,
                "port": settings.redis_port,
                "db": settings.redis_db,
                "max_connections": settings.redis_max_connections,
                "health_check_interval": settings.redis_health_check_interval,
            }
        }


@router.get("/db_health")
async def db_health() -> Dict[str, Any]:
    """
    Database health check endpoint with detailed information.
    
    Returns:
        Dictionary containing database connection status, configuration, and server information
    """
    try:
        # Test connection first
        health_ok = await check_db_health()
        
        # Get database information
        engine = get_async_engine()
        async with engine.connect() as conn:
            # Get PostgreSQL version
            version_result = await conn.execute(text("SELECT version()"))
            version = version_result.scalar()
            
            # Get database size
            size_result = await conn.execute(
                text("SELECT pg_size_pretty(pg_database_size(current_database()))")
            )
            db_size = size_result.scalar()
            
            # Get connection count
            conn_count_result = await conn.execute(
                text("SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()")
            )
            active_connections = conn_count_result.scalar()
            
            # Get max connections
            max_conn_result = await conn.execute(text("SHOW max_connections"))
            max_connections = max_conn_result.scalar()
            
            # Check for TimescaleDB extension
            timescale_result = await conn.execute(
                text("SELECT extversion FROM pg_extension WHERE extname = 'timescaledb'")
            )
            timescale_version = timescale_result.scalar_one_or_none()
            
            # Get database name
            db_name_result = await conn.execute(text("SELECT current_database()"))
            db_name = db_name_result.scalar()
            
            # Get pool info from engine
            pool = engine.pool
            pool_info = {
                "size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "max_overflow": pool._max_overflow,
            }
            
            # Try to get asyncpg pool info if available
            asyncpg_pool_info = None
            try:
                asyncpg_pool = await get_db_pool()
                asyncpg_pool_info = {
                    "min_size": asyncpg_pool.get_min_size(),
                    "max_size": asyncpg_pool.get_max_size(),
                    "size": asyncpg_pool.get_size(),
                    "idle_size": asyncpg_pool.get_idle_size(),
                }
            except Exception:
                pass  # asyncpg pool might not be initialized
            
            server_info = {
                "postgresql_version": version.split(",")[0] if version else "Unknown",
                "database_name": db_name,
                "database_size": db_size,
                "active_connections": active_connections,
                "max_connections": max_connections,
                "connection_usage_percent": round((active_connections / int(max_connections)) * 100, 2) if max_connections else 0,
                "timescaledb_version": timescale_version if timescale_version else None,
            }
            
            return {
                "status": "healthy" if health_ok else "unhealthy",
                "connected": health_ok,
                "configuration": {
                    "host": settings.postgres_host,
                    "port": settings.postgres_port,
                    "database": settings.postgres_db,
                    "user": settings.postgres_user,
                    "pool_size": settings.database_pool_size,
                    "max_overflow": settings.database_max_overflow,
                },
                "server_info": server_info,
                "connection_pools": {
                    "sqlalchemy": pool_info,
                    "asyncpg": asyncpg_pool_info,
                }
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "connected": False,
            "error": str(e),
            "configuration": {
                "host": settings.postgres_host,
                "port": settings.postgres_port,
                "database": settings.postgres_db,
                "user": settings.postgres_user,
                "pool_size": settings.database_pool_size,
                "max_overflow": settings.database_max_overflow,
            }
        }
