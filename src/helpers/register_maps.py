"""Validation helpers for register maps."""

from fastapi import HTTPException, status
from schemas.db_models.models import RegisterMapCreate


def get_expected_format() -> dict:
    """
    Get the expected format for a register map request body.
    
    Returns:
        Dictionary describing the expected format
    """
    return {
        "metadata": {
            "ID": "int (optional)",
            "device_id": "int (optional)",
            "start_register_address": "int (required, 0-65535)",
            "end_register_address": "int (required, 0-65535, must be >= start_register_address)",
            "type": "string (required, one of: 'holding', 'input', 'coil', 'discrete')",
            "overflow": "bool (optional, default: false)",
            "expand": "bool (optional)"
        },
        "registers": [
            {
                "register_address": "int (required, 0-65535)",
                "register_name": "string (required)",
                "size": "int (required, >= 1)",
                "data_type": "string (required, one of: 'int16', 'uint16', 'int32', 'uint32', 'float32', 'int64', 'uint64', 'float64', 'bool', 'bitfield32', 'enum')",
                "scale_factor": "float (optional)",
                "unit": "string (optional, e.g., 'V', 'A', 'kW')",
                "bitfield_definition": "object (optional, maps bit positions as strings to definition names, e.g., {'0': 'definition_0', '1': 'definition_1'})",
                "enum_definition": "object (optional, maps values as strings to definition names, e.g., {'0': 'enum_definition_0', '1': 'enum_definition_1'})"
            }
        ]
    }


def validate_register_map_format(register_map: RegisterMapCreate) -> None:
    """
    Validate that the register map has all required fields and correct format.
    
    Args:
        register_map: Register map to validate
        
    Raises:
        HTTPException: If validation fails with detailed error message
    """
    # Check if metadata field exists
    if not hasattr(register_map, 'metadata') or register_map.metadata is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "Missing required field",
                "message": "The 'metadata' field is required in the request body",
                "expected_format": get_expected_format()
            }
        )
    
    # Check if registers field exists and is not empty
    if not hasattr(register_map, 'registers') or not register_map.registers:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "Missing required field",
                "message": "The 'registers' field is required and must contain at least one register",
                "expected_format": get_expected_format()
            }
        )
    
    # Validate register map format
    metadata = register_map.metadata
    registers = register_map.registers
    
    # Validate metadata required fields
    if not hasattr(metadata, 'start_register_address') or metadata.start_register_address is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "Missing required field",
                "message": "The 'metadata.start_register_address' field is required",
                "expected_format": get_expected_format()
            }
        )
    
    if not hasattr(metadata, 'end_register_address') or metadata.end_register_address is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "Missing required field",
                "message": "The 'metadata.end_register_address' field is required",
                "expected_format": get_expected_format()
            }
        )
    
    if not hasattr(metadata, 'type') or metadata.type is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "Missing required field",
                "message": "The 'metadata.type' field is required (must be one of: 'holding', 'input', 'coil', 'discrete')",
                "expected_format": get_expected_format()
            }
        )
    
    # Validate registers array
    for idx, reg in enumerate(registers):
        if not hasattr(reg, 'register_address') or reg.register_address is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "error": "Missing required field",
                    "message": f"The 'registers[{idx}].register_address' field is required",
                    "expected_format": get_expected_format()
                }
            )
        
        if not hasattr(reg, 'register_name') or not reg.register_name:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "error": "Missing required field",
                    "message": f"The 'registers[{idx}].register_name' field is required",
                    "expected_format": get_expected_format()
                }
            )
        
        if not hasattr(reg, 'size') or reg.size is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "error": "Missing required field",
                    "message": f"The 'registers[{idx}].size' field is required",
                    "expected_format": get_expected_format()
                }
            )
    
    # Validate start_register_address <= end_register_address
    if metadata.start_register_address > metadata.end_register_address:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Invalid register map format",
                "message": "start_register_address must be less than or equal to end_register_address",
                "expected_format": get_expected_format()
            }
        )
    
    # Validate that all register addresses are within the range
    invalid_registers = []
    for idx, reg in enumerate(registers):
        if reg.register_address < metadata.start_register_address:
            invalid_registers.append({
                "index": idx,
                "register_address": reg.register_address,
                "error": f"register_address ({reg.register_address}) is less than start_register_address ({metadata.start_register_address})"
            })
        elif reg.register_address > metadata.end_register_address:
            invalid_registers.append({
                "index": idx,
                "register_address": reg.register_address,
                "error": f"register_address ({reg.register_address}) is greater than end_register_address ({metadata.end_register_address})"
            })
        # Check overflow: if overflow is False, register_address + size should not exceed end_register_address
        elif not metadata.overflow:
            max_address = reg.register_address + reg.size - 1
            if max_address > metadata.end_register_address:
                invalid_registers.append({
                    "index": idx,
                    "register_address": reg.register_address,
                    "size": reg.size,
                    "max_address": max_address,
                    "error": f"register_address ({reg.register_address}) + size ({reg.size}) - 1 = {max_address} exceeds end_register_address ({metadata.end_register_address}) and overflow is disabled"
                })
    
    if invalid_registers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Invalid register addresses",
                "message": "One or more registers have addresses outside the specified range",
                "invalid_registers": invalid_registers,
                "expected_format": get_expected_format()
            }
        )

