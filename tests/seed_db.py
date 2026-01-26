"""Seed the database with a site, devices, and device configs."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))

from db.session import get_session  # noqa: E402
from logger import get_logger  # noqa: E402
from schemas.db_models.orm_models import Site, Device, DeviceConfig  # noqa: E402

logger = get_logger(__name__)

SEED_SITE = {
    "id": 1000,
    "owner": "seed-owner",
    "name": "seed-site",
    "location": "seed-location",
    "operator": "seed-operator",
    "capacity": "1MW",
    "description": "Seed site for local testing",
    "coordinates": {"lat": 32.7157, "lng": -117.1611},
}

SEED_DEVICES = [
    {
        "name": "seed-device-1",
        "modbus_host": "192.168.1.10",
        "modbus_port": 502,
        "modbus_timeout": 5.0,
        "modbus_server_id": 1,
        "description": "Seed device 1",
        "main_type": "meter",
        "sub_type": "seed-1",
        "poll_enabled": True,
        "read_from_aggregator": True,
    },
    {
        "name": "seed-device-2",
        "modbus_host": "192.168.1.11",
        "modbus_port": 502,
        "modbus_timeout": 5.0,
        "modbus_server_id": 1,
        "description": "Seed device 2",
        "main_type": "meter",
        "sub_type": "seed-2",
        "poll_enabled": True,
        "read_from_aggregator": True,
    },
    {
        "name": "seed-device-3",
        "modbus_host": "192.168.1.12",
        "modbus_port": 502,
        "modbus_timeout": 5.0,
        "modbus_server_id": 1,
        "description": "Seed device 3",
        "main_type": "meter",
        "sub_type": "seed-3",
        "poll_enabled": True,
        "read_from_aggregator": True,
    },
]

SEED_CONFIGS = {
    "seed-device-1": [
        {
            "poll_kind": "holding",
            "registers": [
                { "register_address": 1400, "register_name": "SEL_751_M_FREQ", "data_type": "uint16", "size": 1, "scale_factor": 1, "unit": None },
                { "register_address": 1401, "register_name": "SEL_751_M_FREQS", "data_type": "uint16", "size": 1, "scale_factor": 1, "unit": None },
                { "register_address": 1402, "register_name": "SEL_751_M_IA", "data_type": "uint16", "size": 1, "scale_factor": 1, "unit": None },
                { "register_address": 1403, "register_name": "SEL_751_M_IB", "data_type": "uint16", "size": 1, "scale_factor": 1, "unit": None },
                { "register_address": 1404, "register_name": "SEL_751_M_IC", "data_type": "uint16", "size": 1, "scale_factor": 1, "unit": None },
                { "register_address": 1405, "register_name": "SEL_751_M_IG", "data_type": "uint16", "size": 1, "scale_factor": 1, "unit": None },
                { "register_address": 1406, "register_name": "SEL_751_M_IN", "data_type": "uint16", "size": 1, "scale_factor": 1, "unit": None },
                { "register_address": 1407, "register_name": "SEL_751_M_P", "data_type": "uint16", "size": 1, "scale_factor": 1, "unit": None },
                { "register_address": 1408, "register_name": "SEL_751_M_PF", "data_type": "uint16", "size": 1, "scale_factor": 1, "unit": None },
                { "register_address": 1409, "register_name": "SEL_751_M_Q", "data_type": "uint16", "size": 1, "scale_factor": 1, "unit": None },
                { "register_address": 1410, "register_name": "SEL_751_M_S", "data_type": "uint16", "size": 1, "scale_factor": 1, "unit": None },
                { "register_address": 1411, "register_name": "SEL_751_M_VAB", "data_type": "uint16", "size": 1, "scale_factor": 1, "unit": None },
                { "register_address": 1412, "register_name": "SEL_751_M_VBC", "data_type": "uint16", "size": 1, "scale_factor": 1, "unit": None },
                { "register_address": 1413, "register_name": "SEL_751_M_VCA", "data_type": "uint16", "size": 1, "scale_factor": 1, "unit": None },
                { "register_address": 1414, "register_name": "SEL_751_M_VDC", "data_type": "uint16", "size": 1, "scale_factor": 1, "unit": None },
                { "register_address": 1415, "register_name": "SEL_751_M_VS", "data_type": "uint16", "size": 1, "scale_factor": 1, "unit": None }
            ],
        }
    ],
    "seed-device-2": [
        {
            "poll_kind": "holding",
            "registers": [
                { "register_address": 1420, "register_name": "SEL_751_1_FREQ", "data_type": "uint16", "size": 1, "scale_factor": 1, "unit": None },
                { "register_address": 1421, "register_name": "SEL_751_1_FREQS", "data_type": "uint16", "size": 1, "scale_factor": 1, "unit": None },
                { "register_address": 1422, "register_name": "SEL_751_1_IA", "data_type": "uint16", "size": 1, "scale_factor": 1, "unit": None },
                { "register_address": 1423, "register_name": "SEL_751_1_IB", "data_type": "uint16", "size": 1, "scale_factor": 1, "unit": None },
                { "register_address": 1424, "register_name": "SEL_751_1_IC", "data_type": "uint16", "size": 1, "scale_factor": 1, "unit": None },
                { "register_address": 1425, "register_name": "SEL_751_1_IG", "data_type": "uint16", "size": 1, "scale_factor": 1, "unit": None },
                { "register_address": 1426, "register_name": "SEL_751_1_IN", "data_type": "uint16", "size": 1, "scale_factor": 1, "unit": None },
                { "register_address": 1427, "register_name": "SEL_751_1_P", "data_type": "uint16", "size": 1, "scale_factor": 1, "unit": None },
                { "register_address": 1428, "register_name": "SEL_751_1_PF", "data_type": "uint16", "size": 1, "scale_factor": 1, "unit": None },
                { "register_address": 1429, "register_name": "SEL_751_1_Q", "data_type": "uint16", "size": 1, "scale_factor": 1, "unit": None },
                { "register_address": 1430, "register_name": "SEL_751_1_S", "data_type": "uint16", "size": 1, "scale_factor": 1, "unit": None },
                { "register_address": 1431, "register_name": "SEL_751_1_VAB", "data_type": "uint16", "size": 1, "scale_factor": 1, "unit": None },
                { "register_address": 1432, "register_name": "SEL_751_1_VBC", "data_type": "uint16", "size": 1, "scale_factor": 1, "unit": None },
                { "register_address": 1433, "register_name": "SEL_751_1_VCA", "data_type": "uint16", "size": 1, "scale_factor": 1, "unit": None },
                { "register_address": 1434, "register_name": "SEL_751_1_VDC", "data_type": "uint16", "size": 1, "scale_factor": 1, "unit": None },
                { "register_address": 1435, "register_name": "SEL_751_1_VS", "data_type": "uint16", "size": 1, "scale_factor": 1, "unit": None }
            ],
        }
    ],
     "seed-device-3": [
        {
            "poll_kind": "holding",
            "registers": [
                { "register_address": 1500, "register_name": "EOS_1_AI_BESS_MxC", "data_type": "uint16", "size": 1, "scale_factor": 1, "unit": None },
                { "register_address": 1501, "register_name": "EOS_1_AI_BESS_MxC", "data_type": "uint16", "size": 1, "scale_factor": 1, "unit": None },
                { "register_address": 1502, "register_name": "EOS_1_AI_BESS_MxC", "data_type": "uint16", "size": 1, "scale_factor": 1, "unit": None },
                { "register_address": 1503, "register_name": "EOS_1_AI_BESS_MxD", "data_type": "uint16", "size": 1, "scale_factor": 1, "unit": None },
                { "register_address": 1504, "register_name": "EOS_1_AI_BESS_MxD", "data_type": "uint16", "size": 1, "scale_factor": 1, "unit": None },
                { "register_address": 1505, "register_name": "EOS_1_AI_BESS_MxD", "data_type": "uint16", "size": 1, "scale_factor": 1, "unit": None },
                { "register_address": 1506, "register_name": "EOS_1_AI_BESS_READ_CHARGE_STATUS", "data_type": "uint16", "size": 1, "scale_factor": 1, "unit": None },
                { "register_address": 1507, "register_name": "EOS_1_AI_BESS_READ_CHARGE_STATUS", "data_type": "uint16", "size": 1, "scale_factor": 1, "unit": None },
                { "register_address": 1508, "register_name": "EOS_1_AI_BESS_READ_CHARGE_STATUS", "data_type": "uint16", "size": 1, "scale_factor": 1, "unit": None },
                { "register_address": 1509, "register_name": "EOS_1_AI_BESS_READ_KW_NOW", "data_type": "uint16", "size": 1, "scale_factor": 1, "unit": None },
                { "register_address": 1510, "register_name": "EOS_1_AI_BESS_READ_KW_NOW", "data_type": "uint16", "size": 1, "scale_factor": 1, "unit": None },
                { "register_address": 1511, "register_name": "EOS_1_AI_BESS_READ_KW_NOW", "data_type": "uint16", "size": 1, "scale_factor": 1, "unit": None },
                { "register_address": 1512, "register_name": "EOS_1_AI_BESS_SOC", "data_type": "uint16", "size": 1, "scale_factor": 1, "unit": None },
                { "register_address": 1513, "register_name": "EOS_1_AI_BESS_SOC", "data_type": "uint16", "size": 1, "scale_factor": 1, "unit": None },
                { "register_address": 1514, "register_name": "EOS_1_AI_BESS_SOC", "data_type": "uint16", "size": 1, "scale_factor": 1, "unit": None },
            ],
        }
    ],
}


def compute_poll_range(registers: list[dict]) -> tuple[int, int]:
    min_register_number = min(register["register_address"] for register in registers)
    max_register_end = max(
        register["register_address"] + register["size"] - 1
        for register in registers
    )
    poll_count = max_register_end - min_register_number + 1
    return min_register_number, poll_count


async def seed_db() -> None:
    async with get_session() as session:
        site_result = await session.execute(
            select(Site).where(Site.id == SEED_SITE["id"])
        )
        site = site_result.scalar_one_or_none()
        if site is None:
            site = Site(**SEED_SITE)
            session.add(site)
            await session.flush()
            logger.info("Created seed site %s (%s)", site.name, site.id)
        else:
            logger.info("Seed site already exists (%s)", site.id)

        devices_by_name: dict[str, Device] = {}
        for device_data in SEED_DEVICES:
            device_result = await session.execute(
                select(Device).where(Device.name == device_data["name"])
            )
            device = device_result.scalar_one_or_none()
            if device is None:
                device = Device(
                    **device_data,
                    site_id=site.id,
                    configs=[],
                )
                session.add(device)
                await session.flush()
                logger.info("Created seed device %s (%s)", device.name, device.id)
            else:
                logger.info("Seed device already exists (%s)", device.name)
            devices_by_name[device.name] = device

        for device_name, configs in SEED_CONFIGS.items():
            device = devices_by_name[device_name]
            existing_configs = list(device.configs or [])
            for idx, config_data in enumerate(configs, start=1):
                config_id = f"{site.id}-{device.id}-{idx}"
                config_result = await session.execute(
                    select(DeviceConfig).where(DeviceConfig.id == config_id)
                )
                if config_result.scalar_one_or_none() is not None:
                    logger.info("Seed device config already exists (%s)", config_id)
                    if config_id not in existing_configs:
                        existing_configs.append(config_id)
                    continue

                poll_address, poll_count = compute_poll_range(config_data["registers"])
                device_config = DeviceConfig(
                    id=config_id,
                    site_id=site.id,
                    device_id=device.id,
                    poll_address=poll_address,
                    poll_count=poll_count,
                    poll_kind=config_data["poll_kind"],
                    registers=config_data["registers"],
                )
                session.add(device_config)
                existing_configs.append(config_id)
                logger.info("Created seed device config %s", config_id)

            device.configs = existing_configs

        devices_for_site = await session.execute(
            select(Device).where(Device.site_id == site.id)
        )
        site.device_count = len(devices_for_site.scalars().all())

        await session.commit()
        logger.info("Seed complete: site=%s, devices=%s", site.id, site.device_count)


if __name__ == "__main__":
    asyncio.run(seed_db())
