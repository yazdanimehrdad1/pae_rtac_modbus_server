"""
FastAPI application factory.

Creates and configures the FastAPI app instance with routers, middleware, and lifecycle hooks.
"""

from fastapi import FastAPI

from config import settings
from logger import setup_logging, get_logger
from scheduler.engine import start_scheduler, stop_scheduler
from api.middlewear.time_range import validate_time_range

# Router imports
from api.routers import (
    health,
    readings_device,
    readings_raw_modbus,
    cache,
    devices,
    readings_registers,
    sites,
    csv_exports,
    device_configs,
    device_points,
)

# Cache connection imports
from cache.connection import (
    get_redis_client,
    check_redis_health,
    close_redis_client
)

# Database connection imports
from db.connection import (
    get_db_pool,
    get_async_engine,
    check_db_health,
    close_all_db_connections
)

# Register map loader import (disabled - devices must be created via API)
# from utils.config_loader import load_device_configs

# Setup logging
setup_logging(log_level=settings.log_level)
logger = get_logger(__name__)


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        Configured FastAPI app instance
    """
    app = FastAPI(
        title="PAE RTAC Server",
        description="Modbus TCP service for polling and storing time-series data",
        version="1.0.0"
    )

    app.middleware("http")(validate_time_range)
    
    # Mount routers with /api prefix
    app.include_router(health.router, prefix="/api", tags=["health"])
    app.include_router(readings_device.router, prefix="/api", tags=["modbus"])
    app.include_router(readings_raw_modbus.router, prefix="/api", tags=["raw-modbus"])
    app.include_router(cache.router, prefix="/api", tags=["cache"])
    app.include_router(devices.router, prefix="/api", tags=["devices"])
    app.include_router(readings_registers.router, prefix="/api", tags=["register_readings"])
    app.include_router(sites.router, prefix="/api", tags=["sites"])
    app.include_router(csv_exports.router, prefix="/api", tags=["csv-exports"])
    app.include_router(device_configs.router, prefix="/api", tags=["configs"])
    app.include_router(device_points.router, prefix="/api", tags=["device-points"])
    
    # TODO: Add other routers when implemented
    # from api.routers import points, metrics
    # app.include_router(points.router, prefix="/api/v1/points", tags=["points"])
    # app.include_router(metrics.router, tags=["metrics"])
    
    # TODO: Add middleware
    # - CORS
    # - Request logging
    # - Error handling
    
    # Lifecycle hooks
    @app.on_event("startup")
    async def startup():
        """Initialize services on application startup."""
        logger.info("Starting PAE RTAC Server")
        # Initialize Redis connection
        try:
            await get_redis_client()
            health_ok = await check_redis_health()
            if health_ok:
                logger.info("Redis cache initialized successfully")
            else:
                logger.warning("Redis health check failed, but continuing startup")
        except Exception as e:
            logger.error(f"Failed to initialize Redis: {e}")
            # Continue startup even if Redis fails (graceful degradation)
        
        # Initialize database connections (both asyncpg legacy and SQLAlchemy new)
        try:
            # Initialize legacy asyncpg pool (for backward compatibility)
            await get_db_pool()
            # Initialize SQLAlchemy async engine (new)
            get_async_engine()
            
            health_ok = await check_db_health()
            if health_ok:
                logger.info("PostgreSQL database initialized successfully (asyncpg + SQLAlchemy)")
            else:
                logger.warning("Database health check failed, but continuing startup")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            # Continue startup even if database fails (graceful degradation)
        
        # Load device configurations from file
        # NOTE: Device creation is disabled - devices must be created via API endpoints
        # Register maps can be loaded separately if needed
        # try:
        #     results = await load_device_configs()
        #     if results:
        #         successful = sum(1 for v in results.values() if v.get("success", False))
        #         logger.info(f"Register map loading completed: {successful}/{len(results)} successful")
        # except Exception as e:
        #     logger.error(f"Failed to load register maps from CSV files: {e}", exc_info=True)
        #     # Continue startup even if register map loading fails (graceful degradation)
        logger.info("Device auto-creation disabled - devices must be created via API endpoints")
        
        # Start scheduler
        await start_scheduler()
    
    @app.on_event("shutdown")
    async def shutdown():
        """Cleanup resources on application shutdown."""
        logger.info("Shutting down PAE RTAC Server")
        # Stop scheduler
        await stop_scheduler()
        # Close Redis connection
        await close_redis_client()
        # Close database connections (both asyncpg and SQLAlchemy)
        await close_all_db_connections()
    
    logger.info("FastAPI application created")
    return app


# Create app instance
app = create_app()

