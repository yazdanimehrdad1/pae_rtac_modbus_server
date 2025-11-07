"""
Unit tests for Redis cache functionality.

Run with: pytest tests/test_cache.py -v
"""

import pytest
import asyncio
from cache import cache, get_redis_client, check_redis_health, close_redis_client


@pytest.fixture(scope="module")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module", autouse=True)
async def setup_redis():
    """Setup Redis connection before tests."""
    health_ok = await check_redis_health()
    if not health_ok:
        pytest.skip("Redis is not available")
    yield
    # Cleanup
    await close_redis_client()


@pytest.mark.asyncio
async def test_redis_connection():
    """Test Redis connection."""
    health_ok = await check_redis_health()
    assert health_ok, "Redis should be connected"


@pytest.mark.asyncio
async def test_cache_set_get():
    """Test basic set and get operations."""
    test_key = "test:set_get"
    test_value = {"test": "data", "number": 123}
    
    # Set value
    result = await cache.set(test_key, test_value, ttl=60)
    assert result is True
    
    # Get value
    retrieved = await cache.get(test_key)
    assert retrieved == test_value
    
    # Cleanup
    await cache.delete(test_key)


@pytest.mark.asyncio
async def test_cache_string():
    """Test caching string values."""
    test_key = "test:string"
    test_value = "simple string"
    
    await cache.set(test_key, test_value, ttl=60)
    retrieved = await cache.get(test_key)
    assert retrieved == test_value
    
    await cache.delete(test_key)


@pytest.mark.asyncio
async def test_cache_exists():
    """Test exists check."""
    test_key = "test:exists"
    test_value = {"data": "test"}
    
    # Key shouldn't exist initially
    exists = await cache.exists(test_key)
    assert exists is False
    
    # Set key
    await cache.set(test_key, test_value, ttl=60)
    
    # Key should exist now
    exists = await cache.exists(test_key)
    assert exists is True
    
    await cache.delete(test_key)


@pytest.mark.asyncio
async def test_cache_delete():
    """Test delete operation."""
    test_key = "test:delete"
    test_value = {"data": "test"}
    
    # Set and verify exists
    await cache.set(test_key, test_value, ttl=60)
    assert await cache.exists(test_key) is True
    
    # Delete
    deleted = await cache.delete(test_key)
    assert deleted is True
    
    # Verify deleted
    assert await cache.exists(test_key) is False


@pytest.mark.asyncio
async def test_cache_ttl():
    """Test TTL operations."""
    test_key = "test:ttl"
    test_value = {"data": "test"}
    
    await cache.set(test_key, test_value, ttl=120)
    
    ttl = await cache.get_ttl(test_key)
    assert ttl is not None
    assert 100 <= ttl <= 120  # Should be around 120 seconds
    
    await cache.delete(test_key)


@pytest.mark.asyncio
async def test_cache_increment():
    """Test increment operation."""
    test_key = "test:increment"
    
    # Start fresh
    await cache.delete(test_key)
    
    # Increment
    count1 = await cache.increment(test_key, amount=5)
    assert count1 == 5
    
    count2 = await cache.increment(test_key, amount=3)
    assert count2 == 8
    
    count3 = await cache.increment(test_key, amount=0)  # Get current value
    assert count3 == 8
    
    await cache.delete(test_key)


@pytest.mark.asyncio
async def test_cache_pattern_clear():
    """Test pattern-based clearing."""
    # Set multiple keys
    await cache.set("test:pattern:1", "value1", ttl=60)
    await cache.set("test:pattern:2", "value2", ttl=60)
    await cache.set("test:pattern:3", "value3", ttl=60)
    await cache.set("test:other:1", "value4", ttl=60)  # Should not be cleared
    
    # Clear pattern
    cleared = await cache.clear_pattern("test:pattern:*")
    assert cleared == 3
    
    # Verify pattern keys are gone
    assert await cache.exists("test:pattern:1") is False
    assert await cache.exists("test:pattern:2") is False
    assert await cache.exists("test:pattern:3") is False
    
    # Verify other key still exists
    assert await cache.exists("test:other:1") is True
    
    # Cleanup
    await cache.delete("test:other:1")


@pytest.mark.asyncio
async def test_cache_key_prefix():
    """Test that keys are prefixed correctly."""
    test_key = "mykey"
    test_value = {"data": "test"}
    
    await cache.set(test_key, test_value, ttl=60)
    
    # Direct Redis check (if needed)
    client = await get_redis_client()
    prefixed_key = f"rtac_modbus:{test_key}"
    exists = await client.exists(prefixed_key)
    assert exists > 0
    
    await cache.delete(test_key)

