"""Database connection and models."""

from db.connection import (
    get_db_pool,
    close_db_pool,
    check_db_health,
    get_async_engine,
    get_async_session_factory,
    get_async_session,
    close_async_engine,
    close_all_db_connections,
)
from db.session import get_session, execute_in_session

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
