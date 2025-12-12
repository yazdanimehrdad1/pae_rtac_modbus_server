"""Modbus register configuration models."""

from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator


class RegisterPoint(BaseModel):
    """
    Schema for a single Modbus register point.
    
    Represents one register or group of registers to read from a Modbus device.
    """
    name: str = Field(..., description="Human-readable name/label for this register")
    address: int = Field(..., ge=0, le=65535, description="Modbus register address")
    kind: Literal["holding", "input", "coils", "discretes"] = Field(
        ..., description="Type of register: holding, input, coils, or discretes"
    )
    size: int = Field(..., ge=1, le=2000, description="Number of registers/bits to read")
    device_id: Optional[int] = Field(None, ge=1, le=255, description="Modbus unit/slave ID (optional, uses default if not specified)")
    
    # Optional fields for data processing
    data_type: Optional[Literal["int16", "uint16", "int32", "uint32", "float32", "bool"]] = Field(
        default="uint16", description="Data type interpretation"
    )
    scale_factor: Optional[float] = Field(
        default=1.0, description="Scale factor to apply to raw value"
    )
    unit: Optional[str] = Field(None, description="Physical unit (e.g., 'V', 'A', 'kW')")
    tags: Optional[str] = Field(default="", description="Tags for categorization/filtering")
    
    @field_validator("size")
    @classmethod
    def validate_size_for_type(cls, v: int, info) -> int:
        """Validate size based on data type if specified."""
        if hasattr(info, "data") and "data_type" in info.data:
            data_type = info.data.get("data_type")
            if data_type in ["int32", "uint32", "float32"] and v < 2:
                raise ValueError(f"Data type {data_type} requires at least 2 registers")
        return v


class RegisterMap(BaseModel):
    """Container for a collection of register points."""
    points: list[RegisterPoint] = Field(..., description="List of register points to read")
    
    def get_points_by_kind(self, kind: Literal["holding", "input", "coils", "discretes"]) -> list[RegisterPoint]:
        """Filter points by register kind."""
        return [p for p in self.points if p.kind == kind]
    
    def get_points_by_device_id(self, device_id: int) -> list[RegisterPoint]:
        """Filter points by device ID."""
        return [p for p in self.points if p.device_id == device_id]
    
    def get_point_by_name(self, name: str) -> Optional[RegisterPoint]:
        """Get a point by its name."""
        for p in self.points:
            if p.name == name:
                return p
        return None

