"""Database models for TimescaleDB hypertables."""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

# TODO: Define SQLAlchemy models:
# - Time-series point table (hypertable)
# - Metadata tables
# - TimescaleDB extension setup


class DeviceCreate(BaseModel):
    """Request model for creating a new device."""
    name: str = Field(..., min_length=1, max_length=255, description="Unique device name/identifier")
    host: str = Field(..., min_length=1, max_length=255, description="Modbus device hostname or IP address")
    port: int = Field(default=502, ge=1, le=65535, description="Modbus TCP port (default: 502)")
    device_id: int = Field(default=1, ge=1, le=255, description="Modbus unit/slave ID")
    description: Optional[str] = Field(default=None, description="Optional device description")
    poll_address: Optional[int] = Field(None, description="Start address for polling Modbus registers")
    poll_count: Optional[int] = Field(None, description="Number of registers to read during polling")
    poll_kind: Optional[str] = Field(None, description="Register type: holding, input, coils, or discretes")
    poll_enabled: bool = Field(True, description="Whether polling is enabled for this device")


class DeviceUpdate(BaseModel):
    """
    Request model for updating a device.
    
    Note: register_map cannot be updated through this endpoint.
    Register maps are managed separately through the register_map endpoints.
    """
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Device name/identifier")
    host: Optional[str] = Field(None, min_length=1, max_length=255, description="Modbus device hostname or IP address")
    port: Optional[int] = Field(None, ge=1, le=65535, description="Modbus TCP port")
    device_id: Optional[int] = Field(None, ge=1, le=255, description="Modbus unit/slave ID")
    description: Optional[str] = Field(None, description="Device description")


class DeviceListItem(BaseModel):
    """Response model for device data in list views (without register_map for performance)."""
    id: int = Field(..., description="Device ID")
    name: str = Field(..., description="Device name")
    host: str = Field(..., description="Device hostname or IP address")
    port: int = Field(..., description="Modbus TCP port")
    device_id: int = Field(..., description="Modbus unit/slave ID")
    description: Optional[str] = Field(None, description="Device description")
    poll_address: Optional[int] = Field(None, description="Start address for polling Modbus registers")
    poll_count: Optional[int] = Field(None, description="Number of registers to read during polling")
    poll_kind: Optional[str] = Field(None, description="Register type: holding, input, coils, or discretes")
    poll_enabled: bool = Field(True, description="Whether polling is enabled for this device")
    created_at: datetime = Field(..., description="Timestamp when device was created")
    updated_at: datetime = Field(..., description="Timestamp when device was last updated")
    
    model_config = {
        "from_attributes": True,
    }


class DeviceResponse(DeviceListItem):
    """Response model for device data with optional register map."""
    register_map: Optional[Dict[str, Any]] = Field(None, description="Device register map (loaded lazily from DB/CSV)")


__all__ = ["DeviceCreate", "DeviceUpdate", "DeviceListItem", "DeviceResponse"]
