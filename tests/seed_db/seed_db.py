"""Seed the database with development mock data.

Idempotent — safe to run multiple times. Skips rows that already exist.

Run via:
    make seed-db          # copies files into running container then executes
    python tests/seed_db.py  # run locally (requires DB to be reachable)
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from sqlalchemy import func, select

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from db.session import get_session  # noqa: E402
from logger import get_logger  # noqa: E402
from schemas.db_models.orm_models import Config, Device, DevicePoint, Site  # noqa: E402

sys.path.insert(0, str(ROOT / "tests"))
from dev_mock_data import DEVICE_CONFIGS, DEVICES, SITES  # noqa: E402

logger = get_logger(__name__)


def _poll_range(points: list[dict]) -> tuple[int, int]:
    """Return (poll_start_index, poll_count) derived from a list of point defs."""
    start = min(p["address"] for p in points)
    end = max(p["address"] + p.get("size", 1) - 1 for p in points)
    return start, end - start + 1


async def seed() -> None:
    async with get_session() as session:

        # ------------------------------------------------------------------ #
        # 1. Sites                                                             #
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
        # 2. Devices                                                           #
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
                logger.info(
                    "Created device '%s' (id=%s)", device.name, device.device_id
                )
            else:
                logger.info(
                    "Device already exists '%s' (id=%s)", device.name, device.device_id
                )
            device_by_name[device.name] = device

        # ------------------------------------------------------------------ #
        # 3. Configs + DevicePoints                                            #
        # ------------------------------------------------------------------ #
        for device_name, configs in DEVICE_CONFIGS.items():
            device = device_by_name[device_name]
            site_id = device.site_id

            for idx, config_data in enumerate(configs, start=1):
                config_id = f"{site_id}-{device.device_id}-{idx}"
                points = config_data["points"]
                poll_start, poll_count = _poll_range(points)

                # Config row
                result = await session.execute(
                    select(Config).where(Config.config_id == config_id)
                )
                if result.scalar_one_or_none() is None:
                    config = Config(
                        config_id=config_id,
                        site_id=site_id,
                        device_id=device.device_id,
                        poll_kind=config_data["poll_kind"],
                        poll_start_index=poll_start,
                        poll_count=poll_count,
                        points=points,
                        is_active=config_data.get("is_active", True),
                        created_by=config_data.get("created_by", "seed-script"),
                    )
                    session.add(config)
                    await session.flush()
                    logger.info("Created config '%s'", config_id)
                else:
                    logger.info("Config already exists '%s'", config_id)

                # DevicePoint rows — one per point definition
                for point_data in points:
                    result = await session.execute(
                        select(DevicePoint).where(
                            DevicePoint.site_id == site_id,
                            DevicePoint.device_id == device.device_id,
                            DevicePoint.name == point_data["name"],
                        )
                    )
                    if result.scalar_one_or_none() is None:
                        point = DevicePoint(
                            site_id=site_id,
                            device_id=device.device_id,
                            config_id=config_id,
                            address=point_data["address"],
                            name=point_data["name"],
                            size=point_data.get("size", 1),
                            data_type=point_data.get("data_type", "uint16"),
                            scale_factor=point_data.get("scale_factor", 1.0),
                            unit=point_data.get("unit"),
                            is_derived=False,
                            byte_order=point_data.get("byte_order", "big"),
                            bitfield_detail=point_data.get("bitfield_detail"),
                            enum_detail=point_data.get("enum_detail"),
                        )
                        session.add(point)
                        logger.info(
                            "Created device point '%s.%s' (addr=%s)",
                            device_name, point_data["name"], point_data["address"],
                        )
                    else:
                        logger.info(
                            "Device point already exists '%s.%s'",
                            device_name, point_data["name"],
                        )

        # ------------------------------------------------------------------ #
        # 4. Sync device_count on each site                                   #
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
