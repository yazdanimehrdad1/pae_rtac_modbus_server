"""
Modbus data mapping helpers.
"""

from datetime import datetime
from typing import List
import json

from schemas.db_models.orm_models import DevicePoint, DevicePointsReading
from schemas.api_models import ModbusRegisterValues
from logger import get_logger
from helpers.modbus.modbus_data_converter import (
    concat_register_values,
    convert_multi_register_value,
)
from helpers.modbus.validation import validate_point_mapping_fields

logger = get_logger(__name__)


def map_modbus_data_to_device_points(
    timestamp_dt: datetime,
    device_points_list: list[DevicePoint],
    modbus_read_data: ModbusRegisterValues,
    poll_start_address: int
) -> list[DevicePointsReading]:
    """
    Map raw Modbus read data to register points from register map.
    """
    logger.info(f"Mapping {len(device_points_list)} register points to Modbus read data")

    mapped_registers_readings_list: List[DevicePointsReading] = []
    consumed_registers: set[int] = set()
    #logger.info("this is modbus_read_data %s", json.dumps(modbus_read_data, indent=4))
    # logger.info(
    #     "this is device_points_list %s",
    #     json.dumps(
    #         [
    #             {
    #                 "id": point.id,
    #                 "name": point.name,
    #                 "address": point.address,
    #                 "size": point.size,
    #                 "data_type": point.data_type,
    #                 "site_id": point.site_id,
    #                 "device_id": point.device_id,
    #                 "is_derived": point.is_derived,
    #             }
    #             for point in device_points_list
    #         ],
    #         indent=4,
    #     ),
    # )
    logger.info("this is poll_start_address %s", poll_start_address)

    for point_index, point in enumerate(device_points_list):
        point_name = point.name
        point_address = point.address
        point_size = point.size
        point_data_type = point.data_type
        point_byte_order = point.byte_order or "big-endian"

        if not validate_point_mapping_fields(
            point_index,
            point_name,
            point_address,
            point_size,
            poll_start_address,
            len(modbus_read_data),
        ):
            continue

        data_index = point_address - poll_start_address

        if point_size == 1:
            if point_address in consumed_registers:
                logger.warning(
                    f"Skipping point '{point_name}' (address={point_address}, size={point_size}): "
                    "register already processed"
                )
                continue
            consumed_registers.add(point_address)
            point_value_derived = modbus_read_data[data_index]
        else:
            point_registers = set(range(point_address, point_address + point_size))
            if consumed_registers.intersection(point_registers):
                logger.warning(
                    f"Skipping point '{point_name}' (address={point_address}, size={point_size}): "
                    "registers already processed"
                )
                continue

            consumed_registers.update(point_registers)
            point_values = modbus_read_data[data_index:data_index + point_size]
            try:
                point_value_derived = convert_multi_register_value(
                    register_values=point_values,
                    data_type=point_data_type,
                    size=point_size,
                    byte_order=point_byte_order
                )
            except ValueError:
                point_value_derived = concat_register_values(
                    register_values=point_values,
                    byte_order=point_byte_order
                )
                logger.debug(
                    f"Concatenated {len(point_values)} registers for '{point_name}' "
                    f"(address={point_address}, size={point_size})"
                )

       

        mapped_register_reading = DevicePointsReading(
            timestamp=timestamp_dt,
            site_id=point.site_id,
            device_id=point.device_id,
            device_point_id=point.id,
            derived_value=point_value_derived
        )

        mapped_registers_readings_list.append(mapped_register_reading)
        logger.debug(
            f"Mapped register '{point_name}' (address={point_address}, index={data_index}): "
            f"value={point_value_derived}"
        )

    logger.info(
        f"Mapped {len(mapped_registers_readings_list)} out of {len(device_points_list)} register points "
        f"from Modbus read data (start_address={poll_start_address}, read_count={len(modbus_read_data)})"
    )

    return mapped_registers_readings_list
