"""
FastAPI application factory.

Creates and configures the FastAPI app instance with routers, middleware, and lifecycle hooks.
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from config import settings
from logger import setup_logging, get_logger
from scheduler.engine import start_scheduler, stop_scheduler

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
    
    # Mount routers
    from api.routers import health, read, cache
    app.include_router(health.router, tags=["health"])
    app.include_router(read.router, tags=["modbus"])
    app.include_router(cache.router, tags=["cache"])
    
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
        from cache.connection import get_redis_client, check_redis_health
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
        
        # Start scheduler
        await start_scheduler()
    
    @app.on_event("shutdown")
    async def shutdown():
        """Cleanup resources on application shutdown."""
        logger.info("Shutting down PAE RTAC Server")
        # Stop scheduler
        await stop_scheduler()
        # Close Redis connection
        from cache.connection import close_redis_client
        await close_redis_client()
        # TODO: Close database connections
    
    logger.info("FastAPI application created")
    return app


# Create app instance
app = create_app()

