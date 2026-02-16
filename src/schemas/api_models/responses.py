"""API response models."""

from datetime import datetime
from typing import Optional, Dict, List, Literal
from pydantic import BaseModel, Field

from schemas.api_models.mappers import RegisterData, RegisterValue
from schemas.api_models.requests import ConfigPoint, Coordinates, Location


class ReadResponse(BaseModel):
    """Response model for read operations."""
    ok: bool
    timestamp: str = Field(..., description="ISO format timestamp of when the read operation completed")
    kind: str
    address: int
    count: int
    device_id: int = Field(..., description="Modbus unit/slave ID")
    data: dict[int, RegisterData] = Field(
        ..., description="Dictionary mapping register addresses to their data (name, value, type)"
    )


class SimpleReadResponse(BaseModel):
    """Simplified response model for POST /read endpoint with array of register:value pairs."""
    ok: bool
    timestamp: str = Field(..., description="ISO format timestamp of when the read operation completed")
    kind: str
    address: int
    count: int
    device_id: int = Field(..., description="Modbus unit/slave ID")
    data: List[RegisterValue] = Field(
        default_factory=list, description="Array of register number and value pairs"
    )


class HealthResponse(BaseModel):
    """Response model for health check."""
    ok: bool
    host: str
    port: int
    device_id: int = Field(..., description="Modbus unit/slave ID")
    detail: Optional[str] = None


class DeviceListItem(BaseModel):
    """Response model for device data in list views."""
    device_id: int = Field(..., description="Device ID")
    site_id: int = Field(..., description="Site ID (4-digit number)")
    name: str = Field(..., description="Device name")
    type: str = Field(..., description="Device type")
    protocol: str = Field(..., description="Communication protocol")
    vendor: Optional[str] = Field(None, description="Device vendor")
    model: Optional[str] = Field(None, description="Device model")
    host: str = Field(..., description="Device hostname or IP address")
    port: int = Field(..., description="Device port")
    timeout: Optional[float] = Field(default=None, description="Optional timeout (seconds)")
    server_address: int = Field(..., description="Server address")
    description: Optional[str] = Field(None, description="Device description")
    poll_enabled: bool = Field(True, description="Whether polling is enabled for this device")
    read_from_aggregator: bool = Field(True, description="Whether to read from edge aggregator")
    created_at: datetime = Field(..., description="Timestamp when device was created")
    updated_at: datetime = Field(..., description="Timestamp when device was last updated")

    model_config = {
        "from_attributes": True,
    }


class DeviceResponse(DeviceListItem):
    """Response model for device data."""


class DeviceDeleteResponse(BaseModel):
    """Response model for a deleted device."""
    device_id: int = Field(..., description="Deleted device ID")
    site_id: int = Field(..., description="Site ID for the deleted device")


class DeviceWithConfigs(DeviceListItem):
    """Device response with expanded configs."""
    configs: List["ConfigResponse"] = Field(
        default_factory=list,
        description="Expanded configs",
    )


class SiteResponse(BaseModel):
    """Response model for site data."""
    site_id: int = Field(..., alias="id", description="Site ID (4-digit number)")
    client_id: str = Field(..., description="Client identifier")
    name: str = Field(..., description="Site name")
    location: Location = Field(..., description="Site location details")
    operator: str = Field(..., description="Site operator")
    capacity: str = Field(..., description="Site capacity")
    deviceCount: int = Field(..., alias="device_count", description="Number of devices at this site")
    description: Optional[str] = Field(None, description="Site description")
    coordinates: Optional[Coordinates] = Field(None, description="Geographic coordinates")
    devices: Optional[List[DeviceListItem]] = Field(
        default=None, description="List of devices at this site"
    )
    createdAt: datetime = Field(..., alias="created_at", description="Timestamp when site was created")
    updatedAt: datetime = Field(..., alias="updated_at", description="Timestamp when site was last updated")
    lastUpdate: datetime = Field(..., alias="last_update", description="Timestamp of last update")

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
    }


class SiteDeleteResponse(BaseModel):
    """Response model for a deleted site."""
    site_id: int = Field(..., description="Deleted site ID")


class SiteComprehensiveResponse(BaseModel):
    """Comprehensive site response with devices and configs."""
    site_id: int = Field(..., alias="id", description="Site ID (4-digit number)")
    client_id: str = Field(..., description="Client identifier")
    name: str = Field(..., description="Site name")
    location: Location = Field(..., description="Site location details")
    operator: str = Field(..., description="Site operator")
    capacity: str = Field(..., description="Site capacity")
    deviceCount: int = Field(..., alias="device_count", description="Number of devices at this site")
    description: Optional[str] = Field(None, description="Site description")
    coordinates: Optional[Coordinates] = Field(None, description="Geographic coordinates")
    devices: List[DeviceWithConfigs] = Field(default_factory=list, description="Devices with configs")
    createdAt: datetime = Field(..., alias="created_at", description="Timestamp when site was created")
    updatedAt: datetime = Field(..., alias="updated_at", description="Timestamp when site was last updated")
    lastUpdate: datetime = Field(..., alias="last_update", description="Timestamp of last update")

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
    }


class ConfigResponse(BaseModel):
    """Response model for config."""
    config_id: str = Field(..., description="Config ID")
    site_id: int = Field(..., description="Site ID (4-digit number)")
    device_id: int = Field(..., description="Device ID (database primary key)")
    poll_kind: Literal["holding", "input", "coils"] = Field(
        ..., description="Register type"
    )
    poll_start_index: int = Field(..., ge=0, le=65535, description="Start index for polling")
    poll_count: int = Field(..., ge=1, description="Number of registers to read during polling")
    points: List[ConfigPoint] = Field(..., min_length=1, description="Point definitions")
    is_active: bool = Field(..., description="Whether the config is active")
    created_at: datetime = Field(..., description="Timestamp when config was created")
    updated_at: datetime = Field(..., description="Timestamp when config was last updated")
    created_by: str = Field(..., description="Config creator identifier")

    model_config = {
        "from_attributes": True,
    }


class ConfigDeleteResponse(BaseModel):
    """Response model for a deleted config."""
    config_id: str = Field(..., description="Deleted config ID")


class DevicePointResponse(BaseModel):
    """Response model for a device point."""
    id: int = Field(..., description="Primary key")
    site_id: int = Field(..., description="Site ID")
    device_id: int = Field(..., description="Device ID")
    config_id: str = Field(..., description="Config ID")
    name: str = Field(..., description="Point name")
    address: int = Field(..., description="Point address")
    size: int = Field(..., description="Point size")
    data_type: str = Field(..., description="Data type")
    scale_factor: Optional[float] = Field(None, description="Scale factor")
    unit: Optional[str] = Field(None, description="Unit")
    enum_value: Optional[str] = Field(None, description="Enum value if applicable")
    bitfield_value: Optional[str] = Field(None, description="Bitfield value if applicable")
    is_derived: bool = Field(False, description="Whether this point is derived from bitfield/enum expansion")
    enum_detail: Optional[Dict[str, str]] = Field(None, description="Enum detail mapping")
    bitfield_detail: Optional[Dict[str, str]] = Field(None, description="Bitfield detail mapping")
    byte_order: str = Field("big-endian", description="Byte order for interpretation")

    model_config = {
        "from_attributes": True,
    }
