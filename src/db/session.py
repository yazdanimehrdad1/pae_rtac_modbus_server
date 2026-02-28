"""
SQLAlchemy async session management utilities.

Provides helper functions for working with async database sessions.
"""

from contextlib import asynccontextmanager
from typing import AsyncContextManager
from sqlalchemy.ext.asyncio import AsyncSession

from db.connection import get_async_session_factory
from logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def get_session() -> AsyncContextManager[AsyncSession]:
    """
    Get async database session (alternative to get_async_session from connection).
    
    This is a convenience wrapper that provides the same functionality
    as get_async_session() from connection.py.
    
    Usage:
        async with get_session() as session:
            # Use session here
            result = await session.execute(select(Model))
            ...
    
    Yields:
        AsyncSession: Database session
    """
    factory = get_async_session_factory()
    
    async with factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def execute_in_session(
    operation,
    *args,
    **kwargs
):
    """
    Execute a database operation in a new session.
    
    Creates a new session, executes the operation, and handles cleanup.
    Useful for one-off operations outside of request context.
    
    Args:
        operation: Async function that takes a session as first argument
        *args: Positional arguments to pass to operation
        **kwargs: Keyword arguments to pass to operation
        
    Returns:
        Result of the operation
        
    Example:
        async def get_user(session: AsyncSession, user_id: int):
            result = await session.execute(select(User).where(User.id == user_id))
            return result.scalar_one_or_none()
        
        user = await execute_in_session(get_user, user_id=1)
    """
    factory = get_async_session_factory()
    
    async with factory() as session:
        try:
            result = await operation(session, *args, **kwargs)
            await session.commit()
            return result
        except Exception:
            await session.rollback()
            raise
