"""
Modbus register mapper utility.

Maps raw Modbus read data to register points from CSV configuration.
This is the fundamental mapping that links register metadata with their actual read values.
"""

from pathlib import Path
from typing import List, Dict, Any, Union
import pandas as pd
import struct

from schemas.modbus_models import RegisterMap, RegisterPoint
from logger import get_logger

logger = get_logger(__name__)


class MappedRegisterData:
    """
    Data structure representing a register point with its read value(s).
    
    This is the fundamental data type that links register metadata with actual values.
    """
    
    def __init__(
        self,
        name: str,
        address: int,
        size: int,
        value: Union[int, float],
        data_type: str = "uint16",
        scale_factor: float = 1.0,
        unit: str = ""
    ):
        self.name = name
        self.address = address
        self.size = size
        self.value = value  # Raw values from Modbus read
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
            "data_type": self.data_type,
            "scale_factor": self.scale_factor,
            "unit": self.unit
        }
    
    def __repr__(self):
        return f"MappedRegisterData(name={self.name}, address={self.address}, value={self.value})"


# ============================================================================
# Multi-register value conversion helper functions
# ============================================================================

def _convert_uint32(register_values: List[int], byte_order: str = "big") -> int:
    """
    Convert two 16-bit registers to a 32-bit unsigned integer.
    
    Args:
        register_values: List of 2 register values (16-bit each)
        byte_order: "big" (Modbus standard) or "little"
        
    Returns:
        32-bit unsigned integer value
    """
    if len(register_values) != 2:
        raise ValueError(f"uint32 requires exactly 2 registers, got {len(register_values)}")
    
    if byte_order == "big":
        # Big-endian: high word first (Modbus standard)
        # register[0] is high 16 bits, register[1] is low 16 bits
        return (register_values[0] << 16) | register_values[1]
    else:
        # Little-endian: low word first
        return (register_values[1] << 16) | register_values[0]


def _convert_int32(register_values: List[int], byte_order: str = "big") -> int:
    """
    Convert two 16-bit registers to a 32-bit signed integer.
    
    Args:
        register_values: List of 2 register values (16-bit each)
        byte_order: "big" (Modbus standard) or "little"
        
    Returns:
        32-bit signed integer value
    """
    if len(register_values) != 2:
        raise ValueError(f"int32 requires exactly 2 registers, got {len(register_values)}")
    
    # First combine as unsigned, then convert to signed
    if byte_order == "big":
        combined = (register_values[0] << 16) | register_values[1]
    else:
        combined = (register_values[1] << 16) | register_values[0]
    
    # Convert to signed 32-bit integer (handle two's complement)
    if combined >= 0x80000000:
        return combined - 0x100000000
    return combined


def _convert_float32(register_values: List[int], byte_order: str = "big") -> float:
    """
    Convert two 16-bit registers to a 32-bit IEEE 754 float.
    
    Args:
        register_values: List of 2 register values (16-bit each)
        byte_order: "big" (Modbus standard) or "little"
        
    Returns:
        32-bit float value
    """
    if len(register_values) != 2:
        raise ValueError(f"float32 requires exactly 2 registers, got {len(register_values)}")
    
    # Pack registers into bytes
    if byte_order == "big":
        # Big-endian: high word first
        bytes_data = struct.pack('>HH', register_values[0], register_values[1])
    else:
        # Little-endian: low word first
        bytes_data = struct.pack('<HH', register_values[1], register_values[0])
    
    # Unpack as float32
    return struct.unpack('>f', bytes_data)[0] if byte_order == "big" else struct.unpack('<f', bytes_data)[0]


def _convert_int64(register_values: List[int], byte_order: str = "big") -> int:
    """
    Convert four 16-bit registers to a 64-bit signed integer.
    
    Args:
        register_values: List of 4 register values (16-bit each)
        byte_order: "big" (Modbus standard) or "little"
        
    Returns:
        64-bit signed integer value
    """
    if len(register_values) != 4:
        raise ValueError(f"int64 requires exactly 4 registers, got {len(register_values)}")
    
    if byte_order == "big":
        # Big-endian: highest word first
        combined = (
            (register_values[0] << 48) |
            (register_values[1] << 32) |
            (register_values[2] << 16) |
            register_values[3]
        )
    else:
        # Little-endian: lowest word first
        combined = (
            (register_values[3] << 48) |
            (register_values[2] << 32) |
            (register_values[1] << 16) |
            register_values[0]
        )
    
    # Convert to signed 64-bit integer (handle two's complement)
    if combined >= 0x8000000000000000:
        return combined - 0x10000000000000000
    return combined


def _convert_uint64(register_values: List[int], byte_order: str = "big") -> int:
    """
    Convert four 16-bit registers to a 64-bit unsigned integer.
    
    Args:
        register_values: List of 4 register values (16-bit each)
        byte_order: "big" (Modbus standard) or "little"
        
    Returns:
        64-bit unsigned integer value
    """
    if len(register_values) != 4:
        raise ValueError(f"uint64 requires exactly 4 registers, got {len(register_values)}")
    
    if byte_order == "big":
        # Big-endian: highest word first
        return (
            (register_values[0] << 48) |
            (register_values[1] << 32) |
            (register_values[2] << 16) |
            register_values[3]
        )
    else:
        # Little-endian: lowest word first
        return (
            (register_values[3] << 48) |
            (register_values[2] << 32) |
            (register_values[1] << 16) |
            register_values[0]
        )


def _convert_float64(register_values: List[int], byte_order: str = "big") -> float:
    """
    Convert four 16-bit registers to a 64-bit IEEE 754 double precision float.
    
    Args:
        register_values: List of 4 register values (16-bit each)
        byte_order: "big" (Modbus standard) or "little"
        
    Returns:
        64-bit float (double) value
    """
    if len(register_values) != 4:
        raise ValueError(f"float64 requires exactly 4 registers, got {len(register_values)}")
    
    # Pack registers into bytes
    if byte_order == "big":
        # Big-endian: highest word first
        bytes_data = struct.pack('>HHHH', register_values[0], register_values[1], 
                                 register_values[2], register_values[3])
    else:
        # Little-endian: lowest word first
        bytes_data = struct.pack('<HHHH', register_values[3], register_values[2], 
                                 register_values[1], register_values[0])
    
    # Unpack as float64 (double)
    return struct.unpack('>d', bytes_data)[0] if byte_order == "big" else struct.unpack('<d', bytes_data)[0]


def convert_multi_register_value(
    register_values: List[Union[int, bool]],
    data_type: str,
    size: int,
    byte_order: str = "big"
) -> Union[int, float]:
    """
    Convert multiple 16-bit register values to a single value based on data type.
    
    Handles conversion for multi-register data types:
    - size=2: int32, uint32, float32
    - size=4: int64, uint64, float64
    
    Args:
        register_values: List of register values (16-bit integers from Modbus read)
        data_type: Data type string (e.g., "uint32", "int32", "float32", "int64", "uint64", "float64")
        size: Number of registers (must match data_type requirements)
        byte_order: Byte order - "big" (Modbus standard) or "little" (default: "big")
        
    Returns:
        Converted value as int or float
        
    Raises:
        ValueError: If size/data_type combination is invalid or unsupported
    """
    # Validate inputs
    if not register_values:
        raise ValueError("register_values cannot be empty")
    
    if byte_order not in ("big", "little"):
        raise ValueError(f"byte_order must be 'big' or 'little', got '{byte_order}'")
    
    # Convert bool to int if needed
    register_values_int = [int(v) for v in register_values]
    
    # Validate size matches data_type expectations
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
        # Single register types (int16, uint16, bool) - handled by caller
        raise ValueError(
            f"convert_multi_register_value should not be called for single-register types. "
            f"Use the value directly for data_type='{data_type}' with size=1"
        )
    else:
        raise ValueError(
            f"Unsupported data_type '{data_type}' with size={size}. "
            f"Supported multi-register types: {list(expected_sizes.keys())}"
        )
    
    # Dispatch to appropriate conversion function
    if data_type == "uint32":
        return _convert_uint32(register_values_int, byte_order)
    elif data_type == "int32":
        return _convert_int32(register_values_int, byte_order)
    elif data_type == "float32":
        return _convert_float32(register_values_int, byte_order)
    elif data_type == "int64":
        return _convert_int64(register_values_int, byte_order)
    elif data_type == "uint64":
        return _convert_uint64(register_values_int, byte_order)
    elif data_type == "float64":
        return _convert_float64(register_values_int, byte_order)
    else:
        # This should not be reached due to validation above, but just in case
        raise ValueError(f"Unsupported data_type: {data_type}")


# ============================================================================
# Main mapping function
# ============================================================================

def map_modbus_data_to_registers(
    register_map: Union[RegisterMap, Dict[str, Any]],
    modbus_read_data: List[Union[int, bool]],
    poll_start_address: int
) -> List[MappedRegisterData]:
    """
    Map raw Modbus read data to register points from register map.
    
    This function does NOT perform Modbus reads - it only maps already-read data.
    
    This function:
    1. Takes register map (cache/db) and raw Modbus read data
    2. Iterates through each register point in the map
    3. Finds the associated value(s) from the Modbus read data based on register address
    4. Creates a list of MappedRegisterData objects linking register info with their values
    
    Args:
        register_map: RegisterMap object or dictionary with 'registers' key
        modbus_read_data: Raw array of values from Modbus read (e.g., [100, 200, 300, ...])
                         This is the result from modbus_client.read_registers()
        poll_start_address: The starting address of the Modbus read (used to calculate array index)
                           Example: if read_registers(address=1400, count=100), then poll_start_address=1400
        
    Returns:
        List of MappedRegisterData objects, one for each register point that was found in the read data
    """
    # Handle both RegisterMap object and dictionary formats
    if isinstance(register_map, dict):
        # Dictionary format: {"registers": [...], "metadata": {...}}
        register_points = register_map.get("registers", [])
        # Convert dict registers to RegisterPoint-like objects (using dict access)
        points = register_points
    else:
        # RegisterMap object format
        points = register_map.points
    
    logger.debug(f"Mapping {len(points)} register points to Modbus read data")
    
    # Helper function to get point attribute (handles both dict and RegisterPoint)
    def get_attr(point, attr, default=None):
        if isinstance(point, dict):
            return point.get(attr, default)
        return getattr(point, attr, default)
    
    # 2. Iterate through each register point and map to Modbus read data
    mapped_registers: List[MappedRegisterData] = []
    
    # Track consumed registers to prevent overlapping register mappings
    # When a point has size > 1, it consumes multiple consecutive registers
    consumed_registers: set[int] = set()
    
    for point in points:
        # Extract point attributes (works for both dict and RegisterPoint)
        # Standardized to use register_address and register_name
        point_name = get_attr(point, "register_name") or get_attr(point, "name", "")
        point_address = get_attr(point, "register_address") or get_attr(point, "address")
        point_size = get_attr(point, "size", 1)
        point_data_type = get_attr(point, "data_type", "uint16")
        point_scale_factor = get_attr(point, "scale_factor", 1.0)
        point_unit = get_attr(point, "unit", "")
        
        # Skip points with missing required fields
        if point_address is None:
            logger.warning(
                f"Skipping point '{point_name}': missing required field 'register_address'"
            )
            continue
        
        if point_size is None or point_size < 1:
            logger.warning(
                f"Skipping point '{point_name}' (address={point_address}): "
                f"invalid or missing 'size' field (got {point_size})"
            )
            continue
        
        # 3. Calculate the array index for this register address
        # If poll_start_address is 1400 and point.address is 1400, index is 0
        # If poll_start_address is 1400 and point.address is 1401, index is 1
        data_index = point_address - poll_start_address
        
        
        # Check if this register is within the read data range
        if data_index < 0:
            logger.debug(
                f"Skipping point '{point_name}' (address={point_address}): "
                f"address is before poll start address {poll_start_address}"
            )
            continue
        # what if the last point has a size of 2? so the index is 1400 + 2 = 1402 and the length of the modbus_read_data is 1400?
        # so we need to check if the index + size is greater than the length of the modbus_read_data
        # so if the index + size is greater than the length of the modbus_read_data then we need to skip the point
        if data_index + point_size > len(modbus_read_data):
            logger.debug(
                f"Skipping point '{point_name}' (address={point_address}, size={point_size}): "
                f"extends beyond read data range (read {len(modbus_read_data)} values, "
                f"need index {data_index} to {data_index + point_size - 1})"
            )
            continue
            

        # Check for overlapping registers with previously processed points
        # Calculate the range of registers this point uses
        point_registers = set(range(point_address, point_address + point_size))
        
        # Check if any of these registers have already been consumed
        if point_registers & consumed_registers:
            overlapping = point_registers & consumed_registers
            logger.warning(
                f"Skipping point '{point_name}' (address={point_address}, size={point_size}): "
                f"overlaps with previously processed registers {sorted(overlapping)}"
            )
            continue
        
        # Mark all registers in this point's range as consumed
        consumed_registers.update(point_registers)

        # Extract the value(s) for this register point
        point_values = modbus_read_data[data_index:data_index + point_size]
        
        # Convert array to single value based on size and data_type
        if point_size == 1:
            # Single register: use the value directly
            point_value = point_values[0]
        else:
            # Multi-register: use convert_multi_register_value to combine registers
            try:
                point_value = convert_multi_register_value(
                    register_values=point_values,
                    data_type=point_data_type,
                    size=point_size,
                    byte_order="big"  # Modbus standard is big-endian
                )
            except ValueError as e:
                logger.error(
                    f"Failed to convert multi-register value for '{point_name}' "
                    f"(address={point_address}, size={point_size}, data_type={point_data_type}): {e}"
                )
                # Fallback to first value to avoid breaking the mapping
                point_value = point_values[0]
                logger.warning(
                    f"Using first register value only for '{point_name}' due to conversion error"
                )
        
        
        # 4. Create MappedRegisterData object linking register info with values
        mapped_register = MappedRegisterData(
            name=point_name,
            address=point_address,
            size=point_size,
            value=point_value,
            data_type=point_data_type or "uint16",
            scale_factor=point_scale_factor or 1.0,
            unit=point_unit or ""
        )
        
        mapped_registers.append(mapped_register)
        logger.debug(
            f"Mapped register '{point_name}' (address={point_address}, index={data_index}): "
            f"value={point_value}"
        )
    
    logger.info(
        f"Mapped {len(mapped_registers)} out of {len(points)} register points "
        f"from Modbus read data (start_address={poll_start_address}, read_count={len(modbus_read_data)})"
    )
    
    return mapped_registers



def mapped_registers_to_dataframe(mapped_registers: List[MappedRegisterData]) -> pd.DataFrame:
    """
    Convert list of MappedRegisterData objects to pandas DataFrame.
    
    Args:
        mapped_registers: List of MappedRegisterData objects
        
    Returns:
        DataFrame with columns: name, address, size, value, data_type, scale_factor, unit
    """
    data = [reg.to_dict() for reg in mapped_registers]
    return pd.DataFrame(data)

#
def mapped_registers_to_dict(mapped_registers: List[MappedRegisterData]) -> Dict[str, Dict[str, Any]]:
    """
    Convert list of MappedRegisterData objects to dictionary keyed by register name.
    
    Args:
        mapped_registers: List of MappedRegisterData objects
        
    Returns:
        Dictionary mapping register name to its data dictionary
    """
    return {reg.address: reg.to_dict() for reg in mapped_registers}

