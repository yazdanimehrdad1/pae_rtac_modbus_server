"""
Modbus multi-register value conversion helpers.
"""

from typing import List, Union, Optional, Dict, Any
import struct


class MappedRegisterData:
    """
    Data structure representing a register point with its read value(s).
    """

    def __init__(
        self,
        name: str,
        address: int,
        size: int,
        value: Union[int, float],
        value_derived: Optional[Union[int, float]] = None,
        value_scaled: Optional[Union[int, float]] = None,
        data_type: str = "uint16",
        scale_factor: float = 1.0,
        unit: str = ""
    ):
        self.name = name
        self.address = address
        self.size = size
        self.value = value  # Raw values from Modbus read
        self.value_derived = value_derived
        self.value_scaled = value_scaled
        self.data_type = data_type
        self.scale_factor = scale_factor
        self.unit = unit

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "address": self.address,
            "size": self.size,
            "value": self.value,
            "value_derived": self.value_derived,
            "value_scaled": self.value_scaled,
            "data_type": self.data_type,
            "scale_factor": self.scale_factor,
            "unit": self.unit
        }

    def __repr__(self):
        return f"MappedRegisterData(name={self.name}, address={self.address}, value={self.value})"


def _convert_uint32(register_values: List[int], byte_order: str = "big") -> int:
    """
    Convert two 16-bit registers to a 32-bit unsigned integer.
    """
    if len(register_values) != 2:
        raise ValueError(f"uint32 requires exactly 2 registers, got {len(register_values)}")

    if byte_order == "big":
        return (register_values[0] << 16) | register_values[1]
    return (register_values[1] << 16) | register_values[0]


def _convert_int32(register_values: List[int], byte_order: str = "big") -> int:
    """
    Convert two 16-bit registers to a 32-bit signed integer.
    """
    if len(register_values) != 2:
        raise ValueError(f"int32 requires exactly 2 registers, got {len(register_values)}")

    if byte_order == "big":
        combined = (register_values[0] << 16) | register_values[1]
    else:
        combined = (register_values[1] << 16) | register_values[0]

    if combined >= 0x80000000:
        return combined - 0x100000000
    return combined


def _convert_float32(register_values: List[int], byte_order: str = "big") -> float:
    """
    Convert two 16-bit registers to a 32-bit IEEE 754 float.
    """
    if len(register_values) != 2:
        raise ValueError(f"float32 requires exactly 2 registers, got {len(register_values)}")

    if byte_order == "big":
        bytes_data = struct.pack(">HH", register_values[0], register_values[1])
        return struct.unpack(">f", bytes_data)[0]

    bytes_data = struct.pack("<HH", register_values[1], register_values[0])
    return struct.unpack("<f", bytes_data)[0]


def _convert_int64(register_values: List[int], byte_order: str = "big") -> int:
    """
    Convert four 16-bit registers to a 64-bit signed integer.
    """
    if len(register_values) != 4:
        raise ValueError(f"int64 requires exactly 4 registers, got {len(register_values)}")

    if byte_order == "big":
        combined = (
            (register_values[0] << 48) |
            (register_values[1] << 32) |
            (register_values[2] << 16) |
            register_values[3]
        )
    else:
        combined = (
            (register_values[3] << 48) |
            (register_values[2] << 32) |
            (register_values[1] << 16) |
            register_values[0]
        )

    if combined >= 0x8000000000000000:
        return combined - 0x10000000000000000
    return combined


def _convert_uint64(register_values: List[int], byte_order: str = "big") -> int:
    """
    Convert four 16-bit registers to a 64-bit unsigned integer.
    """
    if len(register_values) != 4:
        raise ValueError(f"uint64 requires exactly 4 registers, got {len(register_values)}")

    if byte_order == "big":
        return (
            (register_values[0] << 48) |
            (register_values[1] << 32) |
            (register_values[2] << 16) |
            register_values[3]
        )
    return (
        (register_values[3] << 48) |
        (register_values[2] << 32) |
        (register_values[1] << 16) |
        register_values[0]
    )


def _convert_float64(register_values: List[int], byte_order: str = "big") -> float:
    """
    Convert four 16-bit registers to a 64-bit IEEE 754 double precision float.
    """
    if len(register_values) != 4:
        raise ValueError(f"float64 requires exactly 4 registers, got {len(register_values)}")

    if byte_order == "big":
        bytes_data = struct.pack(">HHHH", register_values[0], register_values[1],
                                 register_values[2], register_values[3])
        return struct.unpack(">d", bytes_data)[0]

    bytes_data = struct.pack("<HHHH", register_values[3], register_values[2],
                             register_values[1], register_values[0])
    return struct.unpack("<d", bytes_data)[0]


def convert_multi_register_value(
    register_values: List[Union[int, bool]],
    data_type: str,
    size: int,
    byte_order: str
) -> Union[int, float]:
    """
    Convert multiple 16-bit register values to a single value based on data type.
    """
    if not register_values:
        raise ValueError("register_values cannot be empty")

    if byte_order not in ("big-endian", "little-endian"):
        raise ValueError(f"byte_order must be 'big-endian' or 'little-endian', got '{byte_order}'")

    register_values_int = [int(v) for v in register_values]

    expected_sizes = {
        "int32": 2,
        "uint32": 2,
        "float32": 2,
        "int64": 4,
        "uint64": 4,
        "float64": 4,
    }

    if data_type in expected_sizes:
        expected_size = expected_sizes[data_type]
        if size != expected_size:
            raise ValueError(
                f"data_type '{data_type}' requires size={expected_size}, but got size={size}"
            )
        if len(register_values_int) < expected_size:
            raise ValueError(
                f"data_type '{data_type}' requires {expected_size} registers, "
                f"but only {len(register_values_int)} provided"
            )
    elif size == 1:
        raise ValueError(
            "convert_multi_register_value should not be called for single-register types. "
            f"Use the value directly for data_type='{data_type}' with size=1"
        )
    else:
        raise ValueError(
            f"Unsupported data_type '{data_type}' with size={size}. "
            f"Supported multi-register types: {list(expected_sizes.keys())}"
        )

    if data_type == "uint32":
        return _convert_uint32(register_values_int, byte_order)
    if data_type == "int32":
        return _convert_int32(register_values_int, byte_order)
    if data_type == "float32":
        return _convert_float32(register_values_int, byte_order)
    if data_type == "int64":
        return _convert_int64(register_values_int, byte_order)
    if data_type == "uint64":
        return _convert_uint64(register_values_int, byte_order)
    if data_type == "float64":
        return _convert_float64(register_values_int, byte_order)
    raise ValueError(f"Unsupported data_type: {data_type}")
