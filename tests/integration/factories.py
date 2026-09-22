"""
Payload builders and create-via-API helpers shared by integration tests.

Tests arrange state through the public API wherever possible, so they exercise the same
write path a real client does. Only data the API can't create (readings) goes in via SQL.
"""

from datetime import datetime
from typing import Any

import asyncpg
from httpx import AsyncClient


def site_payload(**overrides: Any) -> dict[str, Any]:
    payload = {
        "client_id": "client-1",
        "name": "Test Site",
        "location": {"street": "1 Main St", "city": "Fresno", "state": "CA", "zip_code": 93701},
        "operator": "Test Operator",
        "capacity": "10 MW",
        "description": "integration test site",
        "coordinates": {"lat": 36.74, "lng": -119.78},
    }
    payload.update(overrides)
    return payload


def device_payload(**overrides: Any) -> dict[str, Any]:
    # METER has no standardized-point templates, so a new device starts with no points.
    payload = {
        "name": "meter-1",
        "type": "METER",
        "host": "10.0.0.10",
        "port": 502,
        "read_from_aggregator": False,
    }
    payload.update(overrides)
    return payload


def point_payload(**overrides: Any) -> dict[str, Any]:
    payload = {
        "name": "active_power",
        "poll_kind": "holding",
        "address": 100,
        "size": 2,
        "data_type": "float32",
        "unit": "kW",
    }
    payload.update(overrides)
    return payload


async def create_site(client: AsyncClient, **overrides: Any) -> dict[str, Any]:
    response = await client.post("/api/sites", json=site_payload(**overrides))
    assert response.status_code == 201, response.text
    return response.json()


async def create_device(client: AsyncClient, site_id: int, **overrides: Any) -> dict[str, Any]:
    response = await client.post(
        f"/api/devices/site/{site_id}/devices", json=device_payload(**overrides)
    )
    assert response.status_code == 201, response.text
    return response.json()


async def upsert_points(
    client: AsyncClient, site_id: int, device_id: int, points: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    response = await client.put(
        f"/api/device-points/site/{site_id}/device/{device_id}/bulk", json={"points": points}
    )
    assert response.status_code == 200, response.text
    return response.json()


async def insert_reading(
    db: asyncpg.Connection,
    point: dict[str, Any],
    timestamp: datetime,
    raw_value: float | None,
    derived_value: float | None,
) -> None:
    await db.execute(
        """
        INSERT INTO device_points_readings
            ("timestamp", site_id, device_id, device_point_id, raw_value, derived_value)
        VALUES ($1, $2, $3, $4, $5, $6)
        """,
        timestamp,
        point["site_id"],
        point["device_id"],
        point["id"],
        raw_value,
        derived_value,
    )
