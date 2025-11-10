"""Cache test endpoints for manual testing."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Optional

from cache import cache, check_redis_health

router = APIRouter()


class CacheSetRequest(BaseModel):
    key: str
    value: Any
    ttl: Optional[int] = None


class CacheGetResponse(BaseModel):
    key: str
    value: Any
    exists: bool


@router.get("/cache/health")
async def cache_health():
    """Check Redis cache health."""
    health_ok = await check_redis_health()
    return {
        "redis_connected": health_ok,
        "status": "healthy" if health_ok else "unhealthy"
    }


@router.post("/cache/set", response_model=dict)
async def cache_set(request: CacheSetRequest):
    """Set a value in cache."""
    result = await cache.set(request.key, request.value, ttl=request.ttl)
    return {
        "success": result,
        "key": request.key,
        "message": "Value cached" if result else "Failed to cache"
    }


@router.get("/cache/get/{key}", response_model=CacheGetResponse)
async def cache_get(key: str):
    """Get a value from cache."""
    value = await cache.get(key)
    exists = await cache.exists(key)
    return CacheGetResponse(
        key=key,
        value=value,
        exists=exists
    )


@router.delete("/cache/delete/{key}")
async def cache_delete(key: str):
    """Delete a key from cache."""
    deleted = await cache.delete(key)
    return {
        "success": deleted,
        "key": key,
        "message": "Key deleted" if deleted else "Key not found"
    }



@router.get("/cache/exists/{key}")
async def cache_exists(key: str):
    """Check if a key exists in cache."""
    exists = await cache.exists(key)
    return {
        "key": key,
        "exists": exists
    }


@router.get("/cache/keys")
async def cache_list_keys(pattern: Optional[str] = None):
    """
    List all cached keys, optionally filtered by pattern.
    
    Args:
        pattern: Optional pattern to match (e.g., "poll:*"). 
                If not provided, returns all keys.
    
    Returns:
        Dictionary with list of keys and count
    """
    keys = await cache.list_keys(pattern=pattern)
    return {
        "keys": keys,
        "count": len(keys),
        "pattern": pattern if pattern else "*"
    }


@router.delete("/cache/clear")
async def cache_clear_all():
    """
    Delete all cache keys and associated data.
    
    WARNING: This is a destructive operation that will permanently delete
    all cached data. Use with caution.
    
    Returns:
        Dictionary with number of keys deleted
    """
    deleted_count = await cache.clear_all()
    return {
        "success": True,
        "deleted_count": deleted_count,
        "message": f"Deleted {deleted_count} cache keys"
    }