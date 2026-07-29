"""Database connection and models."""

from db.connection import (
    check_db_health,
    close_all_db_connections,
    close_async_engine,
    close_db_pool,
    get_async_engine,
    get_async_session,
    get_async_session_factory,
    get_db_pool,
)
from db.session import execute_in_session, get_session

__all__ = [
    # Legacy asyncpg functions (for backward compatibility)
    "get_db_pool",
    "close_db_pool",
    "check_db_health",
    # SQLAlchemy 2.0+ async functions
    "get_async_engine",
    "get_async_session_factory",
    "get_async_session",
    "close_async_engine",
    "close_all_db_connections",
    # Session utilities
    "get_session",
    "execute_in_session",
]
