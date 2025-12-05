"""
Modbus register mapper utility.

Maps raw Modbus read data to register points from CSV configuration.
This is the fundamental mapping that links register metadata with their actual read values.
"""

from pathlib import Path
from typing import List, Dict, Any, Union
import pandas as pd

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
        kind: str,
        size: int,
        unit_id: int,
        value: Union[int, float],
        data_type: str = "uint16",
        scale_factor: float = 1.0,
        unit: str = "",
        tags: str = None
    ):
        self.name = name
        self.address = address
        self.kind = kind
        self.size = size
        self.unit_id = unit_id
        self.value = value  # Raw values from Modbus read
        self.data_type = data_type
        self.scale_factor = scale_factor
        self.unit = unit
        self.tags = tags or ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "address": self.address,
            "kind": self.kind,
            "size": self.size,
            "unit_id": self.unit_id,
            "value": self.value,
            "data_type": self.data_type,
            "scale_factor": self.scale_factor,
            "unit": self.unit,
            "tags": self.tags
        }
    
    def __repr__(self):
        return f"MappedRegisterData(name={self.name}, address={self.address}, value={self.value})"


def map_modbus_data_to_registers(
    register_map: RegisterMap,
    modbus_read_data: List[Union[int, bool]],
    poll_start_address: int
) -> List[MappedRegisterData]:
    """
    Map raw Modbus read data to register points from register map.
    
    This function does NOT perform Modbus reads - it only maps already-read data.
    
    This function:
    1. Takes register map (already loaded from CSV) and raw Modbus read data
    2. Iterates through each register point in the map
    3. Finds the associated value(s) from the Modbus read data based on register address
    4. Creates a list of MappedRegisterData objects linking register info with their values
    
    Args:
        register_map: RegisterMap object (already loaded from CSV)
        modbus_read_data: Raw array of values from Modbus read (e.g., [100, 200, 300, ...])
                         This is the result from modbus_client.read_registers()
        poll_start_address: The starting address of the Modbus read (used to calculate array index)
                           Example: if read_registers(address=1400, count=100), then poll_start_address=1400
        
    Returns:
        List of MappedRegisterData objects, one for each register point that was found in the read data
        
    Example:
        >>> from utils.map_csv_to_json import map_csv_to_json, json_to_register_map
        >>> register_map = json_to_register_map(map_csv_to_json(Path("config/main_sel_751_register_map.csv")))
        >>> # Modbus read: modbus_client.read_registers(kind="holding", address=1400, count=100, unit_id=1)
        >>> modbus_data = [5000, 1, 100, 200, 300, 400, 500, 600, 0, 0, 10000, 20000, ...]
        >>> mapped = map_modbus_data_to_registers(register_map, modbus_data, poll_start_address=1400)
        >>> # If address 1400 has value 5000, address 1401 has value 1, etc.
        >>> # Returns list of MappedRegisterData objects with register info + values
    """
    logger.debug(f"Mapping {len(register_map.points)} register points to Modbus read data")
    
    # 2. Iterate through each register point and map to Modbus read data
    mapped_registers: List[MappedRegisterData] = []
    
    for point in register_map.points:
        # 3. Calculate the array index for this register address
        # If poll_start_address is 1400 and point.address is 1400, index is 0
        # If poll_start_address is 1400 and point.address is 1401, index is 1
        data_index = point.address - poll_start_address
        
        
        # Check if this register is within the read data range
        if data_index < 0:
            logger.debug(
                f"Skipping point '{point.name}' (address={point.address}): "
                f"address is before poll start address {poll_start_address}"
            )
            continue
        
        if data_index + point.size > len(modbus_read_data):
            logger.debug(
                f"Skipping point '{point.name}' (address={point.address}, size={point.size}): "
                f"extends beyond read data range (read {len(modbus_read_data)} values, "
                f"need index {data_index} to {data_index + point.size - 1})"
            )
            continue
        

        # TODO: If the point.size or point.data_type represents a 32 bit register it needs to be taken care of here. 
        # For example if the point.size is 2 and the point.data_type is "uint32" then the value should be the first 2 registers concatenated together.
        # If the point.size is 2 and the point.data_type is "int32" then the value should be the first 2 registers concatenated together and then sign extended to 32 bits.
        # If the point.size is 4 and the point.data_type is "float32" then the value should be the first 4 registers concatenated together and then converted to a float32.
        # If the point.size is 4 and the point.data_type is "int32" then the value should be the first 4 registers concatenated together and then converted to a int32.
        # If the point.size is 4 and the point.data_type is "uint32" then the value should be the first 4 registers concatenated together and then converted to a uint32.
        # If the point.size is 8 and the point.data_type is "float64" then the value should be the first 8 registers concatenated together and then converted to a float64.
        # If the point.size is 8 and the point.data_type is "int64" then the value should be the first 8 registers concatenated together and then converted to a int64.
        # If the point.size is 8 and the point.data_type is "uint64" then the value should be the first 8 registers concatenated together and then converted to a uint64.
        # So the output of map_modbus_data_to_registers should contain the calculated value for registers that are 32 bits, ...

        # Extract the value(s) for this register point and convert to single value
        # For size=1: extract single value
        # For size>1: combine registers based on data_type (TODO: implement 32-bit, 64-bit conversion)
        point_values = modbus_read_data[data_index:data_index + point.size]
        
        # Convert array to single value based on size and data_type
        if point.size == 1:
            # Single register: use the value directly
            point_value = point_values[0]
        else:
            # Multi-register: for now, use first value (TODO: implement proper 32-bit/64-bit conversion)
            # This should be expanded based on the TODO comments above
            point_value = point_values[0]
            logger.warning(
                f"Register '{point.name}' has size={point.size} but multi-register conversion not yet implemented. "
                f"Using first value only."
            )
        
        
        # 4. Create MappedRegisterData object linking register info with values
        mapped_register = MappedRegisterData(
            name=point.name,
            address=point.address,
            kind=point.kind,
            size=point.size,
            unit_id=point.unit_id or 1,  # Default to 1 if not specified
            value=point_value,
            data_type=point.data_type or "uint16",
            scale_factor=point.scale_factor or 1.0,
            unit=point.unit or "",
            tags=point.tags or ""
        )
        
        mapped_registers.append(mapped_register)
        logger.debug(
            f"Mapped register '{point.name}' (address={point.address}, index={data_index}): "
            f"value={point_value}"
        )
    
    logger.info(
        f"Mapped {len(mapped_registers)} out of {len(register_map.points)} register points "
        f"from Modbus read data (start_address={poll_start_address}, read_count={len(modbus_read_data)})"
    )
    
    return mapped_registers



def mapped_registers_to_dataframe(mapped_registers: List[MappedRegisterData]) -> pd.DataFrame:
    """
    Convert list of MappedRegisterData objects to pandas DataFrame.
    
    Args:
        mapped_registers: List of MappedRegisterData objects
        
    Returns:
        DataFrame with columns: name, address, kind, size, unit_id, value, data_type, scale_factor, unit, tags
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

