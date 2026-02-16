"""
Modbus data mapping helpers.
"""

from datetime import datetime
from typing import List, Optional
import json

from schemas.db_models.orm_models import DevicePoint, DevicePointsReading
from schemas.api_models import ModbusRegisterValues
from logger import get_logger
from helpers.modbus.modbus_data_converter import convert_multi_register_value
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
    logger.info("this is modbus_read_data %s", json.dumps(modbus_read_data, indent=4))
    logger.info(
        "this is device_points_list %s",
        json.dumps(
            [
                {
                    "id": point.id,
                    "name": point.name,
                    "address": point.address,
                    "size": point.size,
                    "data_type": point.data_type,
                    "site_id": point.site_id,
                    "device_id": point.device_id,
                    "is_derived": point.is_derived,
                }
                for point in device_points_list
            ],
            indent=4,
        ),
    )
    logger.info("this is poll_start_address %s", poll_start_address)

    for point_index, point in enumerate(device_points_list):
        point_name = point.name
        point_address = point.address
        point_size = point.size
        point_data_type = point.data_type
        point_scale_factor = point.scale_factor or 1.0
        point_unit = point.unit or ""
        point_byte_order = point.byte_order or "big-endian"
        point_bitfield_detail = point.bitfield_detail or None
        point_enum_detail = point.enum_detail or None
        point_is_derived = point.is_derived or False

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

        if point_address in consumed_registers and not point_is_derived:
            logger.warning(
                f"Skipping point '{point_name}' (address={point_address}): "
                "starting register already consumed"
            )
            continue

        if not point_is_derived:
            point_registers = set(range(point_address, point_address + point_size))
            consumed_registers.update(point_registers)

        point_values = modbus_read_data[data_index:data_index + point_size]

        if point_size == 1:
            point_value = point_values[0]
        else:
            try:
                point_value = convert_multi_register_value(
                    register_values=point_values,
                    data_type=point_data_type,
                    size=point_size,
                    byte_order=point_byte_order
                )
            except ValueError as e:
                logger.error(
                    f"Failed to convert multi-register value for '{point_name}' "
                    f"(address={point_address}, size={point_size}, data_type={point_data_type}): {e}"
                )
                point_value = point_values[0]
                logger.warning(
                    f"Using first register value only for '{point_name}' due to conversion error"
                )

        point_value_derived = None

        if point_data_type == "bitfield" and point_is_derived is False:
            point_value_derived = point_value
            point_unit = "bit"
        elif point_data_type == "enum" and point_is_derived is False:
            point_value_derived = point_value
            point_unit = "enum"
        elif point_data_type == "single_bit" and point_is_derived is True:
            bit_index = point.bitfield_value
            if bit_index is None:
                logger.warning(
                    f"Skipping single_bit derived value for '{point_name}': bitfield_value is None"
                )
                point_value_derived = None
            else:
                try:
                    bit_index = int(bit_index)
                except (TypeError, ValueError):
                    logger.warning(
                        f"Skipping single_bit derived value for '{point_name}': "
                        f"invalid bitfield_value={bit_index!r}"
                    )
                    point_value_derived = None
                else:
                    bits = bin(point_value)[2:]
                    if bit_index < 0 or bit_index >= len(bits):
                        logger.warning(
                            f"Skipping single_bit derived value for '{point_name}': "
                            f"bitfield_value={bit_index} out of range for value={point_value}"
                        )
                        point_value_derived = None
                    else:
                        point_value_derived = int(bits[bit_index])
        elif point_data_type == "single_enum" and point_is_derived is True:
            point_value_derived = point_value == point.enum_value
        else:
            point_value_derived = point_value * point_scale_factor

        mapped_register_reading = DevicePointsReading(
            timestamp=timestamp_dt,
            site_id=point.site_id,
            device_id=point.device_id,
            device_point_id=point.id,
            raw_value=point_value,
            derived_value=point_value_derived
        )

        mapped_registers_readings_list.append(mapped_register_reading)
        logger.debug(
            f"Mapped register '{point_name}' (address={point_address}, index={data_index}): "
            f"value={point_value}"
        )

    logger.info(
        f"Mapped {len(mapped_registers_readings_list)} out of {len(device_points_list)} register points "
        f"from Modbus read data (start_address={poll_start_address}, read_count={len(modbus_read_data)})"
    )

    return mapped_registers_readings_list
