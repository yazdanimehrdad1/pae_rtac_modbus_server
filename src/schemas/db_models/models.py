"""Database models for TimescaleDB hypertables."""

from datetime import datetime
from typing import Optional, Dict, List, Literal
from pydantic import BaseModel, Field

# TODO: Define SQLAlchemy models:
# - Time-series point table (hypertable)
# - Metadata tables
# - TimescaleDB extension setup


class DeviceCreateRequest(BaseModel):
    """Request model for creating a new device."""
    name: str = Field(..., min_length=1, max_length=255, description="Unique device name/identifier")
    type: Literal["meter", "relay", "RTAC", "inverter", "BESS"] = Field(
        ..., description="Device type"
    )
    vendor: Optional[str] = Field(default=None, max_length=255, description="Device vendor")
    model: Optional[str] = Field(default=None, max_length=255, description="Device model")
    host: str = Field(..., min_length=1, max_length=255, description="Device hostname or IP address")
    port: int = Field(default=502, ge=1, le=65535, description="Device port (default: 502)")
    timeout: Optional[float] = Field(default=None, ge=0, description="Optional timeout (seconds)")
    server_address: int = Field(default=1, ge=1, description="Server address (default: 1)")
    description: Optional[str] = Field(default=None, description="Optional device description")
    poll_enabled: bool = Field(True, description="Whether polling is enabled for this device")
    read_from_aggregator: bool = Field(True, description="Whether to read from edge aggregator")


class DeviceUpdate(BaseModel):
    """Request model for updating a device."""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Device name/identifier")
    type: Optional[Literal["meter", "relay", "RTAC", "inverter", "BESS"]] = Field(
        None, description="Device type"
    )
    vendor: Optional[str] = Field(None, max_length=255, description="Device vendor")
    model: Optional[str] = Field(None, max_length=255, description="Device model")
    host: Optional[str] = Field(None, min_length=1, max_length=255, description="Device hostname or IP address")
    port: Optional[int] = Field(None, ge=1, le=65535, description="Device port")
    timeout: Optional[float] = Field(default=None, ge=0, description="Optional timeout (seconds)")
    server_address: Optional[int] = Field(None, ge=1, description="Server address")
    description: Optional[str] = Field(None, description="Device description")
    poll_enabled: Optional[bool] = Field(None, description="Whether polling is enabled for this device")
    read_from_aggregator: Optional[bool] = Field(None, description="Whether to read from edge aggregator")


class DeviceListItem(BaseModel):
    """Response model for device data in list views."""
    device_id: int = Field(..., description="Device ID")
    site_id: int = Field(..., description="Site ID (4-digit number)")
    name: str = Field(..., description="Device name")
    type: str = Field(..., description="Device type")
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
        description="Expanded configs"
    )


class Coordinates(BaseModel):
    """Coordinates model for site location."""
    lat: float = Field(..., description="Latitude")
    lng: float = Field(..., description="Longitude")


class Location(BaseModel):
    """Location model for site address details."""
    street: str = Field(..., min_length=1, max_length=255, description="Street address")
    city: str = Field(..., min_length=1, max_length=255, description="City")
    state: str = Field(..., min_length=1, max_length=255, description="State/province")
    zip_code: int = Field(..., ge=0, description="Zip/postal code")


class SiteCreateRequest(BaseModel):
    """Request model for creating a new site."""
    client_id: str = Field(..., min_length=1, max_length=255, description="Client identifier")
    name: str = Field(..., min_length=1, max_length=255, description="Site name")
    location: Location = Field(..., description="Site location details")
    operator: str = Field(..., min_length=1, max_length=255, description="Site operator")
    capacity: str = Field(..., min_length=1, max_length=255, description="Site capacity")
    description: Optional[str] = Field(default=None, description="Optional site description")
    coordinates: Optional[Coordinates] = Field(default=None, description="Geographic coordinates")


class SiteUpdate(BaseModel):
    """Request model for updating a site."""
    client_id: Optional[str] = Field(None, min_length=1, max_length=255, description="Client identifier")
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Site name")
    location: Optional[Location] = Field(None, description="Site location details")
    operator: Optional[str] = Field(None, min_length=1, max_length=255, description="Site operator")
    capacity: Optional[str] = Field(None, min_length=1, max_length=255, description="Site capacity")
    description: Optional[str] = Field(None, description="Site description")
    coordinates: Optional[Coordinates] = Field(None, description="Geographic coordinates")


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
    devices: Optional[List[DeviceListItem]] = Field(default=None, description="List of devices at this site")
    createdAt: datetime = Field(..., alias="created_at", description="Timestamp when site was created")
    updatedAt: datetime = Field(..., alias="updated_at", description="Timestamp when site was last updated")
    lastUpdate: datetime = Field(..., alias="last_update", description="Timestamp of last update")
    
    model_config = {
        "from_attributes": True,
        "populate_by_name": True,  # Allow both field name and alias
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


class ConfigPoint(BaseModel):
    """Single point definition in a config."""
    name: str = Field(..., alias="point_name", description="Human-readable point name/label")
    address: int = Field(..., alias="point_address", ge=0, le=65535, description="Modbus point address")
    size: int = Field(..., alias="point_size", ge=1, description="Number of registers/bits")
    data_type: str = Field(..., alias="point_data_type", description="Data type interpretation")
    scale_factor: Optional[float] = Field(None, alias="point_scale_factor", description="Scale factor to apply to raw value")
    unit: Optional[str] = Field(None, alias="point_unit", description="Physical unit (e.g., 'V', 'A', 'kW')")
    bitfield_detail: Optional[Dict[str, str]] = Field(
        None,
        alias="point_bitfield_detail",
        description="Bitfield detail mapping (optional)"
    )
    enum_detail: Optional[Dict[str, str]] = Field(
        None,
        alias="point_enum_detail",
        description="Enum detail mapping (optional)"
    )

    model_config = {
        "populate_by_name": True,
    }


class ConfigCreateRequest(BaseModel):
    """Config payload for a device."""
    site_id: int = Field(..., description="Site ID (4-digit number)")
    device_id: int = Field(..., description="Device ID (database primary key)")
    poll_kind: Literal["holding", "input", "coils"] = Field(..., description="Register type")
    poll_start_index: int = Field(..., ge=0, le=65535, description="Start index for polling")
    poll_count: int = Field(..., ge=1, description="Number of registers to read during polling")
    points: List[ConfigPoint] = Field(..., min_length=1, description="Point definitions")
    is_active: bool = Field(default=True, description="Whether the config is active")
    created_by: str = Field(..., min_length=1, max_length=255, description="Config creator identifier")




class ConfigUpdate(BaseModel):
    """Update payload for a config."""
    poll_kind: Optional[Literal["holding", "input", "coils"]] = Field(None, description="Register type")
    poll_start_index: Optional[int] = Field(None, ge=0, le=65535, description="Start index for polling")
    poll_count: Optional[int] = Field(None, ge=1, description="Number of registers to read during polling")
    points: Optional[List[ConfigPoint]] = Field(None, min_length=1, description="Point definitions")
    is_active: Optional[bool] = Field(None, description="Whether the config is active")
    created_by: Optional[str] = Field(None, min_length=1, max_length=255, description="Config creator identifier")


class ConfigResponse(BaseModel):
    """Response model for config."""
    config_id: str = Field(..., description="Config ID")
    site_id: int = Field(..., description="Site ID (4-digit number)")
    device_id: int = Field(..., description="Device ID (database primary key)")
    poll_kind: Literal["holding", "input", "coils"] = Field(..., description="Register type")
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

    model_config = {
        "from_attributes": True,
    }


__all__ = ["DeviceCreateRequest", "DeviceUpdate", "DeviceListItem", "DeviceResponse",
           "DeviceDeleteResponse", "DeviceWithConfigs", "SiteComprehensiveResponse",
           "Coordinates", "Location", "SiteCreateRequest", "SiteUpdate", "SiteResponse", "SiteDeleteResponse",
           "ConfigPoint", "ConfigCreateRequest", "ConfigUpdate", "ConfigResponse", "ConfigDeleteResponse",
           "DevicePointResponse"]
