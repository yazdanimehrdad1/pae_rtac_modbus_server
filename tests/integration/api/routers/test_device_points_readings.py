"""
Integration tests for /api/device-point-readings.

Guards the read side of stored readings against a real database: latest-per-point,
timeseries ordering (newest first) and limits, time-window filtering, enum translation,
display-timezone rendering, and the query validation rules (both at the endpoint and in
the global validate_time_range middleware).
"""

from datetime import UTC, datetime, timedelta

from integration.factories import (
    create_device,
    create_site,
    insert_reading,
    point_payload,
    upsert_points,
)

BASE_TIME = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)
ENUM_DETAIL = {"0": "OFF", "1": "ON"}


async def arrange_readings(client, db) -> tuple[int, int, dict, dict]:
    """A device with a float point (3 readings, 1 min apart) and an enum point (1 reading)."""
    site = await create_site(client)
    device = await create_device(client, site["site_id"])
    power, state = await upsert_points(
        client,
        site["site_id"],
        device["device_id"],
        [
            point_payload(name="active_power", address=100),
            point_payload(
                name="state", address=110, size=1, data_type="enum16", enum_detail=ENUM_DETAIL
            ),
        ],
    )
    for minute, value in enumerate([10.0, 20.0, 30.0]):
        await insert_reading(db, power, BASE_TIME + timedelta(minutes=minute), value, value)
    await insert_reading(db, state, BASE_TIME, 1.0, 1.0)
    return site["site_id"], device["device_id"], power, state


def latest_url(site_id: int, device_id: int) -> str:
    return f"/api/device-point-readings/site/{site_id}/device/{device_id}/latest"


def timeseries_url(site_id: int, device_id: int) -> str:
    return f"/api/device-point-readings/timeseries/site/{site_id}/device/{device_id}"


class TestLatest:
    async def test_returns_newest_reading_per_point(self, client, db):
        site_id, device_id, power, state = await arrange_readings(client, db)
        response = await client.get(latest_url(site_id, device_id))
        assert response.status_code == 200
        body = response.json()
        assert body["meta"]["total_count"] == 2
        assert body["readings"][str(power["id"])]["value"] == 30.0
        assert body["readings"][str(state["id"])]["value"] == 1.0

    async def test_point_ids_filter(self, client, db):
        site_id, device_id, power, _ = await arrange_readings(client, db)
        response = await client.get(
            latest_url(site_id, device_id), params={"point_ids": str(power["id"])}
        )
        assert list(response.json()["readings"]) == [str(power["id"])]

    async def test_translate_labels_enum_values(self, client, db):
        site_id, device_id, _, state = await arrange_readings(client, db)
        response = await client.get(latest_url(site_id, device_id), params={"translate": True})
        assert response.json()["readings"][str(state["id"])]["translated_value"] == "ON"

    async def test_device_without_readings_is_empty(self, client):
        site = await create_site(client)
        device = await create_device(client, site["site_id"])
        response = await client.get(latest_url(site["site_id"], device["device_id"]))
        assert response.status_code == 200
        assert response.json()["readings"] == {}


class TestTimeseries:
    async def test_newest_first_with_counts(self, client, db):
        site_id, device_id, power, _ = await arrange_readings(client, db)
        response = await client.get(timeseries_url(site_id, device_id))
        assert response.status_code == 200
        series = response.json()["readings"][str(power["id"])]
        assert series["count"] == 3
        assert [entry["value"] for entry in series["timeseries"]] == [30.0, 20.0, 10.0]

    async def test_limit_keeps_the_most_recent(self, client, db):
        site_id, device_id, power, _ = await arrange_readings(client, db)
        response = await client.get(timeseries_url(site_id, device_id), params={"limit": 2})
        series = response.json()["readings"][str(power["id"])]
        assert [entry["value"] for entry in series["timeseries"]] == [30.0, 20.0]

    async def test_time_window_filters_readings(self, client, db):
        site_id, device_id, power, _ = await arrange_readings(client, db)
        response = await client.get(
            timeseries_url(site_id, device_id),
            params={
                "point_ids": str(power["id"]),
                "start_time": (BASE_TIME + timedelta(seconds=30)).isoformat(),
                "end_time": (BASE_TIME + timedelta(minutes=5)).isoformat(),
            },
        )
        assert response.status_code == 200
        series = response.json()["readings"][str(power["id"])]
        assert [entry["value"] for entry in series["timeseries"]] == [30.0, 20.0]

    async def test_tz_renders_timestamps_in_that_zone(self, client, db):
        site_id, device_id, power, _ = await arrange_readings(client, db)
        response = await client.get(
            timeseries_url(site_id, device_id),
            params={"point_ids": str(power["id"]), "tz": "America/Los_Angeles"},
        )
        newest = response.json()["readings"][str(power["id"])]["timeseries"][0]["time"]
        # 12:02 UTC on 2026-01-15 is 04:02 PST.
        assert newest == "2026-01-15T04:02:00-08:00"


class TestQueryValidation:
    async def test_time_range_with_explicit_bounds_is_422(self, client, db):
        site_id, device_id, _, _ = await arrange_readings(client, db)
        response = await client.get(
            timeseries_url(site_id, device_id),
            params={"time_range": "1H", "start_time": BASE_TIME.isoformat()},
        )
        assert response.status_code == 422

    async def test_naive_bound_without_tz_is_rejected(self, client, db):
        site_id, device_id, _, _ = await arrange_readings(client, db)
        response = await client.get(
            timeseries_url(site_id, device_id), params={"start_time": "2026-01-15T12:00:00"}
        )
        assert response.status_code == 422

    async def test_middleware_rejects_start_after_end(self, client, db):
        site_id, device_id, _, _ = await arrange_readings(client, db)
        response = await client.get(
            timeseries_url(site_id, device_id),
            params={
                "start_time": (BASE_TIME + timedelta(hours=1)).isoformat(),
                "end_time": BASE_TIME.isoformat(),
            },
        )
        assert response.status_code == 400

    async def test_middleware_rejects_unparseable_time(self, client, db):
        site_id, device_id, _, _ = await arrange_readings(client, db)
        response = await client.get(
            timeseries_url(site_id, device_id),
            params={"start_time": "yesterday", "end_time": BASE_TIME.isoformat()},
        )
        assert response.status_code == 400
