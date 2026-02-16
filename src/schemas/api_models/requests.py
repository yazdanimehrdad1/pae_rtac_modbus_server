"""API request models."""

from typing import Optional, List, Literal, Dict
from pydantic import BaseModel, Field


class Coordinates(BaseModel):
    """Coordinates model for site location."""
    lat: float = Field(..., description="Latitude")
    lng: float = Field(..., description="Longitude")


class Location(BaseModel):
    """Location model for site address details."""
    street: str = Field(..., min_length=1, max_length=255, description="Street address")
    city: str = Field(..., description="City")
    state: str = Field(..., description="State/province")
    zip_code: int = Field(..., ge=0, description="Zip/postal code")


class ConfigPoint(BaseModel):
    """Single point definition in a config."""
    name: str = Field(..., alias="point_name", description="Human-readable point name/label")
    address: int = Field(..., alias="point_address", ge=0, le=65535, description="Modbus point address")
    size: int = Field(..., alias="point_size", ge=1, description="Number of registers/bits")
    data_type: str = Field(..., alias="point_data_type", description="Data type interpretation")
    scale_factor: Optional[float] = Field(
        None, alias="point_scale_factor", description="Scale factor to apply to raw value"
    )
    unit: Optional[str] = Field(None, alias="point_unit", description="Physical unit (e.g., 'V', 'A', 'kW')")
    bitfield_detail: Optional[Dict[str, str]] = Field(
        None,
        alias="point_bitfield_detail",
        description="Bitfield detail mapping (optional)",
    )
    enum_detail: Optional[Dict[str, str]] = Field(
        None,
        alias="point_enum_detail",
        description="Enum detail mapping (optional)",
    )
    byte_order: str = Field(
        default="big-endian",
        alias="point_byte_order",
        description="Byte order for interpretation",
    )

    model_config = {
        "populate_by_name": True,
    }


class ReadRequest(BaseModel):
    """Request model for reading Modbus registers."""
    kind: Literal["holding", "input", "coils", "discretes"] = Field(
        ..., description="Type of register to read"
    )
    address: int = Field(..., ge=0, le=65535, description="Starting address")
    count: int = Field(..., ge=1, le=2000, description="Number of registers/bits to read")
    device_id: Optional[int] = Field(
        None, ge=1, le=255, description="Modbus unit/slave ID (optional)"
    )
    host: Optional[str] = Field(
        None,
        description="Modbus server hostname or IP address (optional, uses default if not provided)",
    )
    port: Optional[int] = Field(
        None, ge=1, le=65535, description="Modbus TCP port (optional, uses default if not provided)"
    )


class DeviceCreateRequest(BaseModel):
    """Request model for creating a new device."""
    name: str = Field(..., min_length=1, max_length=255, description="Unique device name/identifier")
    type: Literal["meter", "relay", "RTAC", "inverter", "BESS"] = Field(
        ..., description="Device type"
    )
    protocol: Literal["Modbus", "DNP"] = Field(
        default="Modbus", description="Communication protocol"
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
    protocol: Optional[Literal["Modbus", "DNP"]] = Field(
        None, description="Communication protocol"
    )
    vendor: Optional[str] = Field(None, max_length=255, description="Device vendor")
    model: Optional[str] = Field(None, description="Device model")
    host: Optional[str] = Field(
        None, min_length=1, max_length=255, description="Device hostname or IP address"
    )
    port: Optional[int] = Field(None, ge=1, le=65535, description="Device port")
    timeout: Optional[float] = Field(default=None, ge=0, description="Optional timeout (seconds)")
    server_address: Optional[int] = Field(None, ge=1, description="Server address")
    description: Optional[str] = Field(None, description="Device description")
    poll_enabled: Optional[bool] = Field(None, description="Whether polling is enabled for this device")
    read_from_aggregator: Optional[bool] = Field(
        None, description="Whether to read from edge aggregator"
    )


class SiteCreateRequest(BaseModel):
    """Request model for creating a new site."""
    client_id: str = Field(..., min_length=1, max_length=255, description="Client identifier")
    name: str = Field(..., min_length=1, max_length=255, description="Site name")
    location: Location = Field(..., description="Site location details")
    operator: str = Field(..., min_length=1, max_length=255, description="Site operator")
    capacity: str = Field(..., min_length=1, max_length=255, description="Site capacity")
    description: Optional[str] = Field(default=None, description="Optional site description")
    coordinates: Optional[Coordinates] = Field(
        default=None, description="Geographic coordinates"
    )


class SiteUpdateRequest(BaseModel):
    """Request model for updating a site."""
    client_id: Optional[str] = Field(
        None, min_length=1, max_length=255, description="Client identifier"
    )
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Site name")
    location: Optional[Location] = Field(None, description="Site location details")
    operator: Optional[str] = Field(None, description="Site operator")
    capacity: Optional[str] = Field(None, min_length=1, max_length=255, description="Site capacity")
    description: Optional[str] = Field(None, description="Site description")
    coordinates: Optional[Coordinates] = Field(None, description="Geographic coordinates")


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
    poll_kind: Optional[Literal["holding", "input", "coils"]] = Field(
        None, description="Register type"
    )
    poll_start_index: Optional[int] = Field(
        None, ge=0, le=65535, description="Start index for polling"
    )
    poll_count: Optional[int] = Field(None, ge=1, description="Number of registers to read during polling")
    points: Optional[List[ConfigPoint]] = Field(None, min_length=1, description="Point definitions")
    is_active: Optional[bool] = Field(None, description="Whether the config is active")
    created_by: Optional[str] = Field(
        None, min_length=1, max_length=255, description="Config creator identifier"
    )


class PollingConfig(BaseModel):
    """Polling configuration for Modbus reads."""
    poll_address: int = Field(..., ge=0, le=65535, description="Start register address")
    poll_count: int = Field(..., ge=1, description="Number of registers to read")
    poll_kind: Literal["holding", "input", "coils", "discretes"] = Field(
        ..., description="Register type to read"
    )
