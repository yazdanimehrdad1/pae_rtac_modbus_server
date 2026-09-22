"""Seed the database with development mock data.

Idempotent — safe to run multiple times. Skips rows that already exist.

Run via:
    make seed-db                    # copies files into running container then executes
    python tests/seed_db/seed_db.py # run locally (requires DB to be reachable)
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from sqlalchemy import func, select

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from db.session import get_session  # noqa: E402
from helpers.device_points.scan_range_computation import (  # noqa: E402
    compute_device_scan_ranges,
)
from logger import get_logger  # noqa: E402
from schemas.api_models.responses import DevicePointResponse  # noqa: E402
from schemas.db_models.orm_models import Device, DevicePoint, Site  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dev_mock_data import DEVICE_POINTS, DEVICES, SITES  # noqa: E402

logger = get_logger(__name__)


async def seed() -> None:
    async with get_session() as session:

        # ------------------------------------------------------------------ #
        # 1. Sites                                                            #
        # ------------------------------------------------------------------ #
        site_by_name: dict[str, Site] = {}
        for site_data in SITES:
            result = await session.execute(
                select(Site).where(Site.name == site_data["name"])
            )
            site = result.scalar_one_or_none()
            if site is None:
                site = Site(**site_data)
                session.add(site)
                await session.flush()
                logger.info("Created site '%s' (id=%s)", site.name, site.id)
            else:
                logger.info("Site already exists '%s' (id=%s)", site.name, site.id)
            site_by_name[site.name] = site

        # ------------------------------------------------------------------ #
        # 2. Devices                                                          #
        # ------------------------------------------------------------------ #
        device_by_name: dict[str, Device] = {}
        for device_data in DEVICES:
            site = site_by_name[device_data["site_name"]]
            fields = {k: v for k, v in device_data.items() if k != "site_name"}

            result = await session.execute(
                select(Device).where(Device.name == fields["name"])
            )
            device = result.scalar_one_or_none()
            if device is None:
                device = Device(**fields, site_id=site.id)
                session.add(device)
                await session.flush()
                logger.info("Created device '%s' (id=%s)", device.name, device.device_id)
            else:
                logger.info(
                    "Device already exists '%s' (id=%s)", device.name, device.device_id
                )
            device_by_name[device.name] = device

        # ------------------------------------------------------------------ #
        # 3. Device points                                                    #
        # ------------------------------------------------------------------ #
        for device_name, point_defs in DEVICE_POINTS.items():
            device = device_by_name[device_name]

            for point_data in point_defs:
                result = await session.execute(
                    select(DevicePoint).where(
                        DevicePoint.site_id == device.site_id,
                        DevicePoint.device_id == device.device_id,
                        DevicePoint.name == point_data["name"],
                    )
                )
                if result.scalar_one_or_none() is not None:
                    logger.info(
                        "Device point already exists '%s.%s'",
                        device_name, point_data["name"],
                    )
                    continue

                session.add(DevicePoint(
                    site_id=device.site_id,
                    device_id=device.device_id,
                    address=point_data["address"],
                    name=point_data["name"],
                    size=point_data.get("size", 1),
                    data_type=point_data.get("data_type", "uint16"),
                    scale_factor=point_data.get("scale_factor", 1.0),
                    unit=point_data.get("unit"),
                    poll_kind=point_data["poll_kind"],
                    category="NATIVE",
                    byte_order=point_data.get("byte_order", "big-endian"),
                    word_order=point_data.get("word_order", "msw_first"),
                    bitfield_detail=point_data.get("bitfield_detail"),
                    enum_detail=point_data.get("enum_detail"),
                ))
                logger.info(
                    "Created device point '%s.%s' (addr=%s)",
                    device_name, point_data["name"], point_data["address"],
                )

            await session.flush()

        # ------------------------------------------------------------------ #
        # 4. Recompute scan_ranges from each device's active NATIVE points    #
        # ------------------------------------------------------------------ #
        for device in device_by_name.values():
            if device.scan_ranges_locked:
                logger.info(
                    "Scan ranges locked for '%s' — leaving untouched", device.name
                )
                continue

            points_result = await session.execute(
                select(DevicePoint).where(
                    DevicePoint.device_id == device.device_id,
                    DevicePoint.category == "NATIVE",
                    DevicePoint.deleted_at.is_(None),
                )
            )
            native_points = [
                DevicePointResponse.model_validate(point)
                for point in points_result.scalars().all()
            ]
            device.scan_ranges = compute_device_scan_ranges(native_points).model_dump()
            logger.info("Computed scan ranges for '%s': %s", device.name, device.scan_ranges)

        # ------------------------------------------------------------------ #
        # 5. Sync device_count on each site                                   #
        # ------------------------------------------------------------------ #
        for site in site_by_name.values():
            count_result = await session.execute(
                select(func.count()).select_from(Device).where(Device.site_id == site.id)
            )
            site.device_count = count_result.scalar_one()

        await session.commit()
        logger.info("Seeding complete.")


if __name__ == "__main__":
    asyncio.run(seed())
