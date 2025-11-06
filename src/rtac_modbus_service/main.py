"""
Application entrypoint.

Uvicorn ASGI server with lifecycle hooks.
"""

import uvicorn
from rtac_modbus_service.app import app
from rtac_modbus_service.config import settings
from rtac_modbus_service.logging import get_logger

logger = get_logger(__name__)

if __name__ == "__main__":
    logger.info(f"Starting RTAC Modbus Service on {settings.api_host}:{settings.api_port}")
    uvicorn.run(
        "rtac_modbus_service.app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,  # TODO: Disable in production
        log_level=settings.log_level.lower()
    )

