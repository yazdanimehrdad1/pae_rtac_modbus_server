"""
Application entrypoint.

Uvicorn ASGI server with lifecycle hooks.
"""

import uvicorn
from app import app
from config import settings
from logger import get_logger

logger = get_logger(__name__)

if __name__ == "__main__":
    logger.info(f"Starting PAE RTAC Server on {settings.api_host}:{settings.api_port}")
    uvicorn.run(
        "app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,  # TODO: Disable in production
        log_level=settings.log_level.lower()
    )

