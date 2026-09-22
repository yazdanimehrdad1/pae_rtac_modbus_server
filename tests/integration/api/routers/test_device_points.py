"""
Integration tests for /api/device-points.

Guards point CRUD against a real database: bulk upsert by name, category filtering,
soft/hard delete and restore, and that the device's scan ranges are recomputed from its
NATIVE points after each write, unless a manual override locked them.
"""

from integration.factories import create_device, create_site, point_payload, upsert_points


def points_url(site_id: int, device_id: int) -> str:
    return f"/api/device-points/site/{site_id}/device/{device_id}"


async def get_device(client, site_id: int, device_id: int) -> dict:
    response = await client.get(f"/api/devices/site/{site_id}/devices/{device_id}")
    assert response.status_code == 200, response.text
    return response.json()


async def make_device(client) -> tuple[int, int]:
    site = await create_site(client)
    device = await create_device(client, site["site_id"])
    return site["site_id"], device["device_id"]


class TestBulkUpsert:
    async def test_creates_points_and_recomputes_scan_ranges(self, client):
        site_id, device_id = await make_device(client)
        points = await upsert_points(
            client,
            site_id,
            device_id,
            [
                point_payload(name="active_power", address=100, size=2, data_type="float32"),
                point_payload(name="state", address=105, size=1, data_type="enum16"),
            ],
        )
        assert {point["name"] for point in points} == {"active_power", "state"}
        assert all(point["category"] == "NATIVE" for point in points)

        device = await get_device(client, site_id, device_id)
        # 100-101 and 105 are within MAX_INTER_POINT_GAP, so one range covers both.
        assert device["scan_ranges"]["holding"] == [{"start_index": 100, "count": 6}]
        assert device["scan_ranges_locked"] is False

    async def test_existing_name_is_updated_not_duplicated(self, client):
        site_id, device_id = await make_device(client)
        await upsert_points(client, site_id, device_id, [point_payload(unit="kW")])
        await upsert_points(client, site_id, device_id, [point_payload(unit="MW")])

        listed = await client.get(points_url(site_id, device_id))
        assert [(point["name"], point["unit"]) for point in listed.json()] == [
            ("active_power", "MW")
        ]

    async def test_native_point_without_address_is_400(self, client):
        site_id, device_id = await make_device(client)
        response = await client.put(
            f"{points_url(site_id, device_id)}/bulk",
            json={"points": [point_payload(address=None)]},
        )
        assert response.status_code == 400

    async def test_size_not_matching_data_type_is_422(self, client):
        site_id, device_id = await make_device(client)
        response = await client.put(
            f"{points_url(site_id, device_id)}/bulk",
            json={"points": [point_payload(data_type="int32", size=1)]},
        )
        assert response.status_code == 422

    async def test_unknown_device_is_404(self, client):
        site = await create_site(client)
        response = await client.put(
            f"{points_url(site['site_id'], 9999)}/bulk", json={"points": [point_payload()]}
        )
        assert response.status_code == 404


class TestListPoints:
    async def test_category_filter(self, client):
        site = await create_site(client)
        device = await create_device(client, site["site_id"], name="bess-1", type="BESS")
        await upsert_points(client, site["site_id"], device["device_id"], [point_payload()])
        url = points_url(site["site_id"], device["device_id"])

        native = await client.get(url, params={"category": "NATIVE"})
        assert [point["name"] for point in native.json()] == ["active_power"]

        standardized = await client.get(url, params={"category": "STANDARDIZED"})
        assert standardized.json()
        assert all(point["category"] == "STANDARDIZED" for point in standardized.json())


class TestUpdatePoint:
    async def test_update_moves_point_and_recomputes_scan_ranges(self, client):
        site_id, device_id = await make_device(client)
        [point] = await upsert_points(client, site_id, device_id, [point_payload()])

        response = await client.put(
            f"{points_url(site_id, device_id)}/{point['id']}", json={"address": 300}
        )
        assert response.status_code == 200
        assert response.json()["address"] == 300

        device = await get_device(client, site_id, device_id)
        assert device["scan_ranges"]["holding"] == [{"start_index": 300, "count": 2}]

    async def test_rename_to_existing_name_is_409(self, client):
        site_id, device_id = await make_device(client)
        _, second = await upsert_points(
            client,
            site_id,
            device_id,
            [point_payload(name="first", address=100), point_payload(name="second", address=200)],
        )
        response = await client.put(
            f"{points_url(site_id, device_id)}/{second['id']}", json={"name": "first"}
        )
        assert response.status_code == 409

    async def test_unknown_point_is_404(self, client):
        site_id, device_id = await make_device(client)
        response = await client.put(
            f"{points_url(site_id, device_id)}/9999", json={"unit": "kW"}
        )
        assert response.status_code == 404


class TestDeleteAndRestorePoints:
    async def test_soft_delete_hides_point_and_restore_brings_it_back(self, client):
        site_id, device_id = await make_device(client)
        [point] = await upsert_points(client, site_id, device_id, [point_payload()])
        url = points_url(site_id, device_id)

        deleted = await client.delete(url, params={"point_ids": [point["id"]]})
        assert deleted.status_code == 200
        assert [item["id"] for item in deleted.json()] == [point["id"]]
        assert (await client.get(url)).json() == []
        assert [item["id"] for item in (await client.get(f"{url}/deleted")).json()] == [
            point["id"]
        ]

        restored = await client.post(f"{url}/{point['id']}/restore")
        assert restored.status_code == 200
        assert restored.json()["deleted_at"] is None
        assert [item["id"] for item in (await client.get(url)).json()] == [point["id"]]

    async def test_hard_delete_requires_confirm(self, client):
        site_id, device_id = await make_device(client)
        [point] = await upsert_points(client, site_id, device_id, [point_payload()])
        response = await client.delete(
            points_url(site_id, device_id), params={"point_ids": [point["id"]], "mode": "hard"}
        )
        assert response.status_code == 400
        assert response.json()["detail"]["error"] == "ConfirmationRequired"

    async def test_hard_delete_is_permanent(self, client):
        site_id, device_id = await make_device(client)
        [point] = await upsert_points(client, site_id, device_id, [point_payload()])
        url = points_url(site_id, device_id)
        response = await client.delete(
            url, params={"point_ids": [point["id"]], "mode": "hard", "confirm": True}
        )
        assert response.status_code == 200
        assert (await client.get(url, params={"include_deleted": True})).json() == []

    async def test_missing_point_ids_are_404(self, client):
        site_id, device_id = await make_device(client)
        response = await client.delete(points_url(site_id, device_id), params={"point_ids": [9999]})
        assert response.status_code == 404


class TestScanRangeOverride:
    async def test_override_locks_ranges_until_reset(self, client):
        site_id, device_id = await make_device(client)
        await upsert_points(client, site_id, device_id, [point_payload(address=100, size=2)])
        url = f"{points_url(site_id, device_id)}/scan-ranges"
        manual = {"holding": [{"start_index": 0, "count": 50}], "input": [], "coils": []}

        override = await client.put(url, json=manual)
        assert override.status_code == 200

        # A point write must not overwrite locked ranges.
        await upsert_points(client, site_id, device_id, [point_payload(name="extra", address=400)])
        device = await get_device(client, site_id, device_id)
        assert device["scan_ranges_locked"] is True
        assert device["scan_ranges"]["holding"] == manual["holding"]

        reset = await client.delete(url)
        assert reset.status_code == 200
        device = await get_device(client, site_id, device_id)
        assert device["scan_ranges_locked"] is False
        assert device["scan_ranges"]["holding"] == [
            {"start_index": 100, "count": 2},
            {"start_index": 400, "count": 2},
        ]
