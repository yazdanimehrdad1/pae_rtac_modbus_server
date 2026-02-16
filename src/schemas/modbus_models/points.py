"""Modbus register point models."""

from typing import Literal, Optional, Dict
from pydantic import BaseModel, Field, field_validator


class RegisterPoint(BaseModel):
    """
    Schema for a single Modbus register point.

    Represents one register or group of registers to read from a Modbus device.
    """
    register_address: int = Field(..., ge=0, le=65535, description="Modbus register address")
    register_name: str = Field(..., description="Human-readable name/label for this register")
    data_type: Literal[
        "int16",
        "uint16",
        "int32",
        "uint32",
        "float32",
        "int64",
        "uint64",
        "float64",
        "bool",
    ] = Field(default="uint16", description="Data type interpretation")
    size: int = Field(..., ge=1, le=2000, description="Number of registers/bits to read")
    scale_factor: Optional[float] = Field(
        default=1.0, description="Scale factor to apply to raw value"
    )
    unit: Optional[str] = Field(None, description="Physical unit (e.g., 'V', 'A', 'kW')")
    bitfield_detail: Optional[Dict[str, str]] = Field(
        default=None, description="Bitfield detail mapping (optional)"
    )
    enum_detail: Optional[Dict[str, str]] = Field(
        default=None, description="Enum detail mapping (optional)"
    )

    @field_validator("size")
    @classmethod
    def validate_size_for_type(cls, v: int, info) -> int:
        """Validate size based on data type if specified."""
        if hasattr(info, "data") and "data_type" in info.data:
            data_type = info.data.get("data_type")
            # 32-bit types require 2 registers
            if data_type in ["int32", "uint32", "float32"] and v < 2:
                raise ValueError(f"Data type {data_type} requires at least 2 registers")
            # 64-bit types require 4 registers
            if data_type in ["int64", "uint64", "float64"] and v < 4:
                raise ValueError(f"Data type {data_type} requires at least 4 registers")
        return v
