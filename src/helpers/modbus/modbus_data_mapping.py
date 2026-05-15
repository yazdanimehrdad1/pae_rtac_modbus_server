"""
Modbus data mapping helpers.
"""

import struct
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Literal

from schemas.db_models.orm_models import DevicePoint, DevicePointsReading
from schemas.api_models import ModbusRegisterValues
from logger import get_logger
from helpers.modbus.modbus_data_converter import (
    concat_register_values,
    convert_multi_register_value,
)
from helpers.modbus.validation import validate_point_mapping_fields

logger = get_logger(__name__)


Quality = Literal[
    "GOOD",
    "BAD_ADDRESS",
    "BAD_REGISTER_COUNT",
    "BAD_CONVERSION",
    "BAD_DATA_TYPE",
    "BAD_EMPTY_DATA",
]
@dataclass
class RegisterExtractionResult:
    success: bool
    values: list[int]
    quality: Quality
    reason: Optional[str] = None


@dataclass
class DecodeResult:
    success: bool
    value: Optional[float | int | bool]
    quality: Quality
    reason: Optional[str] = None


def _extract_register_values(
    register_map: dict[int, int | bool],
    point_address: int,
    size: int,
) -> RegisterExtractionResult:
    """
    Extract the raw register values for one point from a register map.

    Example:
        point_address = 1400, size = 2
        → reads register_map[1400] and register_map[1401]
    """
    if not register_map:
        return RegisterExtractionResult(
            success=False,
            values=[],
            quality="BAD_EMPTY_DATA",
            reason="Register map is empty",
        )

    if size < 1:
        return RegisterExtractionResult(
            success=False,
            values=[],
            quality="BAD_REGISTER_COUNT",
            reason=f"Invalid size={size}",
        )

    addresses = range(point_address, point_address + size)
    missing = [a for a in addresses if a not in register_map]
    if missing:
        return RegisterExtractionResult(
            success=False,
            values=[],
            quality="BAD_ADDRESS",
            reason=f"Register addresses {missing} not available in poll data",
        )

    return RegisterExtractionResult(
        success=True,
        values=[register_map[a] for a in addresses],
        quality="GOOD",
    )



def _apply_word_order(
    register_values: list[int],
    word_order: str = "msw_first",
) -> list[int]:
    """
    Controls register order.

    msw_first:
        [high_word, low_word]

    lsw_first:
        [low_word, high_word]
    """
    if word_order == "lsw_first":
        return list(reversed(register_values))
    return register_values


def _registers_to_bytes(
    register_values: list[int],
    byte_order: str = "big",
) -> bytes:
    """
    Converts 16-bit Modbus registers to bytes.

    Each Modbus register is 16 bits.
    big:
        0x1234 -> 12 34

    little:
        0x1234 -> 34 12
    """
    byte_data = bytearray()
    for reg in register_values:
        if byte_order == "little":
            byte_data.extend(reg.to_bytes(2, byteorder="little", signed=False))
        else:
            byte_data.extend(reg.to_bytes(2, byteorder="big", signed=False))
    return bytes(byte_data)


def _decode_modbus_point_value(
    register_values: list[int],
    data_type: str,
    byte_order: str = "big",
    word_order: str = "msw_first",
    scale: float = 1.0,
    offset: float = 0.0,
) -> DecodeResult:
    """
    Decode raw Modbus registers into final engineering value.

    This handles:
        uint16, int16
        uint32, int32
        float32
        uint64, int64
        float64
        bool
        raw/status_word
    """
    try:
        ordered_registers = _apply_word_order(register_values, word_order)
        raw_bytes = _registers_to_bytes(ordered_registers, byte_order)

        data_type = data_type.lower()

        if data_type == "bool":
            value = bool(ordered_registers[0])

        elif data_type in ("uint16", "status_word", "raw"):
            value = int.from_bytes(raw_bytes, byteorder="big", signed=False)

        elif data_type == "int16":
            value = int.from_bytes(raw_bytes, byteorder="big", signed=True)

        elif data_type == "uint32":
            value = int.from_bytes(raw_bytes, byteorder="big", signed=False)

        elif data_type == "int32":
            value = int.from_bytes(raw_bytes, byteorder="big", signed=True)

        elif data_type == "float32":
            value = struct.unpack(">f", raw_bytes)[0]

        elif data_type == "uint64":
            value = int.from_bytes(raw_bytes, byteorder="big", signed=False)

        elif data_type == "int64":
            value = int.from_bytes(raw_bytes, byteorder="big", signed=True)

        elif data_type == "float64":
            value = struct.unpack(">d", raw_bytes)[0]

        else:
            return DecodeResult(
                success=False,
                value=None,
                quality="BAD_DATA_TYPE",
                reason=f"Unsupported data_type={data_type}",
            )

        if isinstance(value, (int, float)) and data_type != "bool":
            value = (value * scale) + offset

        return DecodeResult(
            success=True,
            value=value,
            quality="GOOD",
        )

    except Exception as exc:
        return DecodeResult(
            success=False,
            value=None,
            quality="BAD_CONVERSION",
            reason=str(exc),
        )


def _decode_register_value(
    register_values: ModbusRegisterValues,
    data_type: str,
    size: int,
    byte_order: str,
    point_name: str,
) -> int | float | bool:
    if size == 1:
        return register_values[0]
    try:
        return convert_multi_register_value(
            register_values=register_values,
            data_type=data_type,
            size=size,
            byte_order=byte_order,
        )
    except ValueError:
        logger.debug(
            f"Concatenated {len(register_values)} registers for '{point_name}' "
            f"(size={size})"
        )
        return concat_register_values(
            register_values=register_values,
            byte_order=byte_order,
        )


def _build_device_point_reading(
    point: DevicePoint,
    timestamp: datetime,
    derived_value: int | float | bool,
) -> DevicePointsReading:
    return DevicePointsReading(
        timestamp=timestamp,
        site_id=point.site_id,
        device_id=point.device_id,
        device_point_id=point.id,
        derived_value=derived_value,
    )



def map_modbus_data_to_device_points(
    timestamp_dt: datetime,
    device_points_list: list[DevicePoint],
    register_map: dict[int, int | bool],
) -> list[DevicePointsReading]:
    readings = []

    for point in device_points_list:
        extraction = _extract_register_values(
            register_map=register_map,
            point_address=point.address,
            size=point.size or 1,
        )

        if not extraction.success:
            readings.append(
                DevicePointsReading(
                    timestamp=timestamp_dt,
                    device_point_id=point.id,
                    derived_value=None,
                    quality=extraction.quality,
                )
            )
            continue

        decoded = _decode_modbus_point_value(
            register_values=extraction.values,
            data_type=point.data_type or "uint16",
            byte_order=point.byte_order or "big",
            word_order=point.word_order or "msw_first",
            scale=point.scale or 1.0,
            offset=point.offset or 0.0,
        )

        readings.append(
            DevicePointsReading(
                timestamp=timestamp_dt,
                device_point_id=point.id,
                derived_value=decoded.value,
                quality=decoded.quality,
            )
        )

    return readings

# def map_modbus_data_to_device_points(
#     timestamp_dt: datetime,
#     device_points_list: list[DevicePoint],
#     modbus_read_data: ModbusRegisterValues,
#     poll_start_address: int
# ) -> list[DevicePointsReading]:
#     """
#     Map raw Modbus read data to register points from register map.
#     """
#     logger.info(f"Mapping {len(device_points_list)} register points to Modbus read data")

#     mapped_registers_readings_list: List[DevicePointsReading] = []
#     consumed_registers: set[int] = set()

#     logger.info("this is poll_start_address %s", poll_start_address)

#     for point_index, point in enumerate(device_points_list):
#         point_name = point.name
#         point_address = point.address
#         point_size = point.size
#         point_data_type = point.data_type
#         point_byte_order = point.byte_order or "big-endian"

#         if not validate_point_mapping_fields(
#             point_index,
#             point_name,
#             point_address,
#             point_size,
#             poll_start_address,
#             len(modbus_read_data),
#         ):
#             continue

#         data_index = point_address - poll_start_address

#         if point_size == 1:
#             if point_address in consumed_registers:
#                 logger.warning(
#                     f"Skipping point '{point_name}' (address={point_address}, size={point_size}): "
#                     "register already processed"
#                 )
#                 continue
#             consumed_registers.add(point_address)
#             point_value_derived = modbus_read_data[data_index]
#         else:
#             point_registers = set(range(point_address, point_address + point_size))
#             if consumed_registers.intersection(point_registers):
#                 logger.warning(
#                     f"Skipping point '{point_name}' (address={point_address}, size={point_size}): "
#                     "registers already processed"
#                 )
#                 continue

#             consumed_registers.update(point_registers)
#             point_values = modbus_read_data[data_index:data_index + point_size]
#             try:
#                 point_value_derived = convert_multi_register_value(
#                     register_values=point_values,
#                     data_type=point_data_type,
#                     size=point_size,
#                     byte_order=point_byte_order
#                 )
#             except ValueError:
#                 point_value_derived = concat_register_values(
#                     register_values=point_values,
#                     byte_order=point_byte_order
#                 )
#                 logger.debug(
#                     f"Concatenated {len(point_values)} registers for '{point_name}' "
#                     f"(address={point_address}, size={point_size})"
#                 )

       

#         mapped_register_reading = DevicePointsReading(
#             timestamp=timestamp_dt,
#             site_id=point.site_id,
#             device_id=point.device_id,
#             device_point_id=point.id,
#             derived_value=point_value_derived
#         )

#         mapped_registers_readings_list.append(mapped_register_reading)
#         logger.debug(
#             f"Mapped register '{point_name}' (address={point_address}, index={data_index}): "
#             f"value={point_value_derived}"
#         )

#     logger.info(
#         f"Mapped {len(mapped_registers_readings_list)} out of {len(device_points_list)} register points "
#         f"from Modbus read data (start_address={poll_start_address}, read_count={len(modbus_read_data)})"
#     )

#     return mapped_registers_readings_list
