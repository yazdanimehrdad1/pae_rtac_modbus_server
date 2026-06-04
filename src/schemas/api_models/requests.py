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
    scan_ranges: Optional["DeviceScanRanges"] = Field(None, description="Initial scan ranges (optional)")


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
    scan_ranges: Optional["DeviceScanRanges"] = Field(None, description="Updated scan ranges (does not lock)")


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



class PollingConfig(BaseModel):
    """Polling configuration for Modbus reads."""
    poll_address: int = Field(..., ge=0, le=65535, description="Start register address")
    poll_count: int = Field(..., ge=1, description="Number of registers to read")
    poll_kind: Literal["holding", "input", "coils", "discretes"] = Field(
        ..., description="Register type to read"
    )


class RegisterRange(BaseModel):
    """A single Modbus read window."""
    start_index: int = Field(..., ge=0, le=65535)
    count: int = Field(..., ge=1)


class DeviceScanRanges(BaseModel):
    """Scan ranges categorized by register type."""
    holding: List[RegisterRange] = Field(default_factory=list)
    input: List[RegisterRange] = Field(default_factory=list)
    coils: List[RegisterRange] = Field(default_factory=list)


class DevicePointCreateRequest(BaseModel):
    """Request model for creating a device point directly (Config-free)."""
    name: str = Field(..., min_length=1, max_length=255)
    poll_kind: Optional[Literal["holding", "input", "coils"]] = None
    address: Optional[int] = Field(None, ge=0, le=65535)
    size: int = Field(..., ge=1)
    data_type: str
    scale_factor: Optional[float] = None
    unit: Optional[str] = None
    byte_order: str = "big-endian"
    word_order: str = "msw_first"
    register_offset: float = 0.0
    bitfield_detail: Optional[Dict[str, str]] = None
    enum_detail: Optional[Dict[str, str]] = None
    category: Literal["NATIVE", "STANDARDIZED", "VIRTUAL"] = "NATIVE"


class DevicePointUpdateRequest(BaseModel):
    """Request model for updating a device point."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    poll_kind: Optional[Literal["holding", "input", "coils"]] = None
    address: Optional[int] = Field(None, ge=0, le=65535)
    size: Optional[int] = Field(None, ge=1)
    data_type: Optional[str] = None
    scale_factor: Optional[float] = None
    unit: Optional[str] = None
    byte_order: Optional[str] = None
    word_order: Optional[str] = None
    register_offset: Optional[float] = None
    bitfield_detail: Optional[Dict[str, str]] = None
    enum_detail: Optional[Dict[str, str]] = None


class DevicePointsBulkRequest(BaseModel):
    """Bulk upsert: create new points and update existing ones (matched by name) in one call."""
    points: List[DevicePointCreateRequest] = Field(..., min_length=1)
