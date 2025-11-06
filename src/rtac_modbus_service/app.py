"""
FastAPI application factory.

Creates and configures the FastAPI app instance with routers, middleware, and lifecycle hooks.
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from rtac_modbus_service.config import settings
from rtac_modbus_service.logging import setup_logging, get_logger

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
        title="RTAC Modbus Service",
        description="Modbus TCP service for polling and storing time-series data",
        version="1.0.0"
    )
    
    # Mount routers
    from rtac_modbus_service.api.routers import health, read
    app.include_router(health.router, tags=["health"])
    app.include_router(read.router, tags=["modbus"])
    
    # TODO: Add other routers when implemented
    # from rtac_modbus_service.api.routers import points, metrics
    # app.include_router(points.router, prefix="/api/v1/points", tags=["points"])
    # app.include_router(metrics.router, tags=["metrics"])
    
    # TODO: Add middleware
    # - CORS
    # - Request logging
    # - Error handling
    
    # TODO: Add lifecycle hooks
    # @app.on_event("startup")
    # async def startup():
    #     logger.info("Starting RTAC Modbus Service")
    #     # Initialize scheduler
    #     # Initialize database connections
    # 
    # @app.on_event("shutdown")
    # async def shutdown():
    #     logger.info("Shutting down RTAC Modbus Service")
    #     # Stop scheduler
    #     # Close database connections
    
    logger.info("FastAPI application created")
    return app


# Create app instance
app = create_app()

