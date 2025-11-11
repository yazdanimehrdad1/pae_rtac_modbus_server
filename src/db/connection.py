"""
PostgreSQL/TimescaleDB connection management.

Handles database connection creation, connection pooling, and lifecycle management.
"""

from typing import Optional
import asyncpg

from config import settings
from logger import get_logger

logger = get_logger(__name__)

# Global database connection pool
_db_pool: Optional[asyncpg.Pool] = None


async def get_db_pool() -> asyncpg.Pool:
    """
    Get or create database connection pool.
    
    Uses connection pooling for efficient resource management.
    
    Returns:
        PostgreSQL async connection pool
        
    Raises:
        asyncpg.PostgresConnectionError: If unable to connect to database
    """
    global _db_pool
    
    if _db_pool is None:
        logger.info(
            f"Connecting to PostgreSQL at {settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
        )
        
        try:
            _db_pool = await asyncpg.create_pool(
                host=settings.postgres_host,
                port=settings.postgres_port,
                database=settings.postgres_db,
                user=settings.postgres_user,
                password=settings.postgres_password,
                min_size=1,
                max_size=settings.database_pool_size,
            )
            
            # Test connection
            async with _db_pool.acquire() as conn:
                await conn.execute("SELECT 1")
            logger.info("Successfully connected to PostgreSQL")
            
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise
    
    return _db_pool


async def close_db_pool() -> None:
    """
    Close database connection pool.
    
    Should be called during application shutdown.
    """
    global _db_pool
    
    if _db_pool is not None:
        await _db_pool.close()
        _db_pool = None
        logger.info("PostgreSQL connection pool closed")


async def check_db_health() -> bool:
    """
    Check if database connection is healthy.
    
    Returns:
        True if database is accessible, False otherwise
    """
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute("SELECT 1")
        return True
    except Exception as e:
        logger.warning(f"Database health check failed: {e}")
        return False

