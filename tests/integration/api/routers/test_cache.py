"""
Integration tests for the /api/cache admin surface against a real Redis.

Guards set/get/exists/delete round-trips, JSON value types, TTLs, pattern listing, and
clear — all through the key prefix the service applies.
"""

import pytest


class TestCacheRoundTrip:
    @pytest.mark.parametrize(
        "value", ["text", 42, {"nested": {"list": [1, 2]}}, [1, "two", 3.0]]
    )
    async def test_set_then_get_returns_same_value(self, client, value):
        response = await client.post("/api/cache/set", json={"key": "k", "value": value})
        assert response.json()["success"] is True

        fetched = await client.get("/api/cache/get/k")
        assert fetched.json() == {"key": "k", "value": value, "exists": True}

    async def test_missing_key(self, client):
        fetched = await client.get("/api/cache/get/absent")
        assert fetched.json() == {"key": "absent", "value": None, "exists": False}
        assert (await client.get("/api/cache/exists/absent")).json()["exists"] is False

    async def test_delete(self, client):
        await client.post("/api/cache/set", json={"key": "k", "value": 1})
        assert (await client.delete("/api/cache/delete/k")).json()["success"] is True
        assert (await client.get("/api/cache/exists/k")).json()["exists"] is False
        assert (await client.delete("/api/cache/delete/k")).json()["success"] is False

    async def test_ttl_is_applied(self, client):
        await client.post("/api/cache/set", json={"key": "k", "value": 1, "ttl": 120})
        [entry] = (await client.get("/api/cache/keys")).json()["keys"]
        assert 0 < entry["ttl"] <= 120


class TestCacheKeys:
    async def test_pattern_filters_keys(self, client):
        for key in ("poll:1", "poll:2", "other"):
            await client.post("/api/cache/set", json={"key": key, "value": 1})
        response = await client.get("/api/cache/keys", params={"pattern": "poll:*"})
        assert response.json()["count"] == 2

    async def test_clear_deletes_everything(self, client):
        for key in ("a", "b"):
            await client.post("/api/cache/set", json={"key": key, "value": 1})
        cleared = await client.delete("/api/cache/clear")
        assert cleared.json()["deleted_count"] == 2
        assert (await client.get("/api/cache/keys")).json()["count"] == 0

    async def test_health(self, client):
        response = await client.get("/api/cache/health")
        assert response.json() == {"redis_connected": True, "status": "healthy"}
