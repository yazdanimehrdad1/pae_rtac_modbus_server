"""Database models for TimescaleDB hypertables."""

from datetime import datetime
from typing import Optional, Dict, Any, List, Literal
from pydantic import BaseModel, Field

# TODO: Define SQLAlchemy models:
# - Time-series point table (hypertable)
# - Metadata tables
# - TimescaleDB extension setup


class DeviceCreate(BaseModel):
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
    """Device response with expanded device configs."""
    device_configs: List["DeviceConfigResponse"] = Field(
        default_factory=list,
        description="Expanded device configs"
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


class SiteCreate(BaseModel):
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


class DeviceConfigRegister(BaseModel):
    """Single register definition in a device config."""
    register_address: int = Field(..., ge=0, le=65535, description="Modbus register address")
    register_name: str = Field(..., description="Human-readable name/label for this register")
    data_type: Literal["int16", "uint16", "int32", "uint32", "float32", "int64", "uint64", "float64", "bool"] = Field(
        ...,
        description="Data type interpretation"
    )
    size: int = Field(..., ge=1, description="Number of registers/bits")
    scale_factor: Optional[float] = Field(default=None, description="Scale factor to apply to raw value")
    unit: Optional[str] = Field(default=None, description="Physical unit (e.g., 'V', 'A', 'kW')")
    bitfield_detail: Optional[Dict[str, str]] = Field(
        default=None,
        description="Bitfield detail mapping (optional)"
    )
    enum_detail: Optional[Dict[str, str]] = Field(
        default=None,
        description="Enum detail mapping (optional)"
    )


class DeviceConfigData(BaseModel):
    """Config payload for a device."""
    site_id: int = Field(..., alias="Site_id", description="Site ID (4-digit number)")
    device_id: int = Field(..., description="Device ID (database primary key)")
    poll_address: int = Field(..., ge=0, le=65535, description="Start address for polling Modbus registers")
    poll_count: int = Field(..., ge=1, description="Number of registers to read during polling")
    poll_kind: Literal["holding", "input", "coils", "discretes"] = Field(..., description="Register type")
    registers: List[DeviceConfigRegister] = Field(..., min_length=1, description="Register definitions")

    model_config = {
        "populate_by_name": True,
    }




class DeviceConfigResponse(BaseModel):
    """Response model for device config."""
    config_id: str = Field(..., alias="config_ID", description="Device config ID")
    site_id: int = Field(..., alias="Site_id", description="Site ID (4-digit number)")
    device_id: int = Field(..., description="Device ID (database primary key)")
    poll_address: int = Field(..., ge=0, le=65535, description="Start address for polling Modbus registers")
    poll_count: int = Field(..., ge=1, description="Number of registers to read during polling")
    poll_kind: Literal["holding", "input", "coils", "discretes"] = Field(..., description="Register type")
    registers: List[DeviceConfigRegister] = Field(..., min_length=1, description="Register definitions")
    created_at: datetime = Field(..., description="Timestamp when config was created")
    updated_at: datetime = Field(..., description="Timestamp when config was last updated")
    warnings: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional warnings about the config payload"
    )

    model_config = {
        "populate_by_name": True,
    }


class DeviceConfigDeleteResponse(BaseModel):
    """Response model for a deleted device config."""
    device_config_id: str = Field(..., description="Deleted device config ID")


__all__ = ["DeviceCreate", "DeviceUpdate", "DeviceListItem", "DeviceResponse",
           "DeviceDeleteResponse", "DeviceWithConfigs", "SiteComprehensiveResponse",
           "Coordinates", "Location", "SiteCreate", "SiteUpdate", "SiteResponse", "SiteDeleteResponse",
           "DeviceConfigRegister", "DeviceConfigData",
           "DeviceConfigUpdate", "DeviceConfigResponse", "DeviceConfigDeleteResponse"]
