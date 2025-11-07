"""
Redis caching service.

Provides high-level caching operations with TTL support and key prefixing.
"""

import json
from typing import Any, Optional
from datetime import timedelta

import redis.asyncio as aioredis

from rtac_modbus_service.cache.connection import get_redis_client
from rtac_modbus_service.config import settings
from rtac_modbus_service.logging import get_logger

logger = get_logger(__name__)


class CacheService:
    """
    Redis-based caching service.
    
    Provides methods for storing and retrieving cached data with TTL support.
    Automatically handles key prefixing and JSON serialization.
    """
    
    def __init__(self, key_prefix: Optional[str] = None, default_ttl: Optional[int] = None):
        """
        Initialize cache service.
        
        Args:
            key_prefix: Prefix for all cache keys (defaults to settings.cache_key_prefix)
            default_ttl: Default TTL in seconds (defaults to settings.cache_default_ttl)
        """
        self.key_prefix = key_prefix or settings.cache_key_prefix
        self.default_ttl = default_ttl or settings.cache_default_ttl
    
    def _make_key(self, key: str) -> str:
        """Create a prefixed cache key."""
        return f"{self.key_prefix}:{key}"
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key (will be prefixed automatically)
            
        Returns:
            Cached value if found, None otherwise
        """
        try:
            client = await get_redis_client()
            full_key = self._make_key(key)
            value = await client.get(full_key)
            
            if value is None:
                return None
            
            # Try to deserialize JSON, fallback to raw string
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
                
        except Exception as e:
            logger.warning(f"Cache get failed for key '{key}': {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Set value in cache with optional TTL.
        
        Args:
            key: Cache key (will be prefixed automatically)
            value: Value to cache (will be JSON serialized if not a string)
            ttl: Time to live in seconds (defaults to self.default_ttl)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            client = await get_redis_client()
            full_key = self._make_key(key)
            
            # Serialize value to JSON if not a string
            if isinstance(value, str):
                serialized_value = value
            else:
                serialized_value = json.dumps(value)
            
            ttl = ttl if ttl is not None else self.default_ttl
            
            await client.setex(full_key, ttl, serialized_value)
            return True
            
        except Exception as e:
            logger.warning(f"Cache set failed for key '{key}': {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """
        Delete value from cache.
        
        Args:
            key: Cache key (will be prefixed automatically)
            
        Returns:
            True if deleted, False otherwise
        """
        try:
            client = await get_redis_client()
            full_key = self._make_key(key)
            result = await client.delete(full_key)
            return result > 0
        except Exception as e:
            logger.warning(f"Cache delete failed for key '{key}': {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.
        
        Args:
            key: Cache key (will be prefixed automatically)
            
        Returns:
            True if key exists, False otherwise
        """
        try:
            client = await get_redis_client()
            full_key = self._make_key(key)
            result = await client.exists(full_key)
            return result > 0
        except Exception as e:
            logger.warning(f"Cache exists check failed for key '{key}': {e}")
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.
        
        Args:
            pattern: Pattern to match (e.g., "device:*")
            
        Returns:
            Number of keys deleted
        """
        try:
            client = await get_redis_client()
            full_pattern = self._make_key(pattern)
            deleted = 0
            
            async for key in client.scan_iter(match=full_pattern):
                await client.delete(key)
                deleted += 1
            
            return deleted
        except Exception as e:
            logger.warning(f"Cache clear_pattern failed for pattern '{pattern}': {e}")
            return 0
    
    async def get_ttl(self, key: str) -> Optional[int]:
        """
        Get remaining TTL for a key.
        
        Args:
            key: Cache key (will be prefixed automatically)
            
        Returns:
            TTL in seconds, None if key doesn't exist or has no TTL
        """
        try:
            client = await get_redis_client()
            full_key = self._make_key(key)
            ttl = await client.ttl(full_key)
            return ttl if ttl >= 0 else None
        except Exception as e:
            logger.warning(f"Cache get_ttl failed for key '{key}': {e}")
            return None
    
    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """
        Increment a numeric value in cache.
        
        Args:
            key: Cache key (will be prefixed automatically)
            amount: Amount to increment by (default: 1)
            
        Returns:
            New value after increment, None if operation failed
        """
        try:
            client = await get_redis_client()
            full_key = self._make_key(key)
            return await client.incrby(full_key, amount)
        except Exception as e:
            logger.warning(f"Cache increment failed for key '{key}': {e}")
            return None


# Global cache service instance
cache = CacheService()

