"""API response models."""

from datetime import datetime
from typing import Optional, Dict, List, Union
from pydantic import AliasChoices, BaseModel, Field

from schemas.api_models.mappers import RegisterData, RegisterValue
from schemas.api_models.requests import Coordinates, Location, DeviceScanRanges


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
    scan_ranges: Optional[DeviceScanRanges] = Field(None, description="Auto-computed or manually locked scan ranges")
    scan_ranges_locked: bool = Field(False, description="Whether scan ranges are locked against auto-recompute")
    modbus_address_mode: str = Field("zero_based", description="zero_based or one_based — controls pymodbus address offset")
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



class DevicePointsCategoryGrouped(BaseModel):
    """Device points grouped by category."""
    standardized: List["DevicePointResponse"] = Field(default_factory=list)
    native: List["DevicePointResponse"] = Field(default_factory=list)
    virtual: List["DevicePointResponse"] = Field(default_factory=list)


# Backwards-compatible alias used by device endpoints that return both points and configs
DevicePoints = DevicePointsCategoryGrouped


class DeviceWithConfigs(DeviceListItem):
    """Device response with device points grouped by category."""
    points: DevicePointsCategoryGrouped = Field(default_factory=DevicePointsCategoryGrouped)


class DeviceWithPoints(DeviceListItem):
    """Device response with categorized device points (no configs)."""
    points: DevicePointsCategoryGrouped = Field(default_factory=DevicePointsCategoryGrouped)


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
    """Comprehensive site response with devices and their categorized points."""
    site_id: int = Field(..., alias="id", description="Site ID (4-digit number)")
    client_id: str = Field(..., description="Client identifier")
    name: str = Field(..., description="Site name")
    location: Location = Field(..., description="Site location details")
    operator: str = Field(..., description="Site operator")
    capacity: str = Field(..., description="Site capacity")
    deviceCount: int = Field(..., alias="device_count", description="Number of devices at this site")
    description: Optional[str] = Field(None, description="Site description")
    coordinates: Optional[Coordinates] = Field(None, description="Geographic coordinates")
    devices: List[DeviceWithPoints] = Field(default_factory=list, description="Devices with categorized points")
    createdAt: datetime = Field(..., alias="created_at", description="Timestamp when site was created")
    updatedAt: datetime = Field(..., alias="updated_at", description="Timestamp when site was last updated")
    lastUpdate: datetime = Field(..., alias="last_update", description="Timestamp of last update")

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
    }



class DevicePointResponse(BaseModel):
    """Response model for a device point."""
    id: int = Field(..., description="Primary key")
    site_id: int = Field(..., description="Site ID")
    device_id: int = Field(..., description="Device ID")
    name: str = Field(..., description="Point name")
    address: int = Field(..., description="Point address")
    size: int = Field(..., description="Point size")
    data_type: str = Field(..., description="Data type")
    scale_factor: Optional[float] = Field(None, description="Scale factor")
    unit: Optional[str] = Field(None, description="Unit")
    enum_detail: Optional[Dict[str, str]] = Field(None, description="Enum detail mapping")
    bitfield_detail: Optional[Dict[str, str]] = Field(None, description="Bitfield detail mapping")
    byte_order: str = Field("big-endian", description="Byte order for interpretation")
    word_order: str = Field("msw_first", description="Word order for multi-register types")
    register_offset: float = Field(0.0, description="Linear offset applied after scaling")
    poll_kind: Optional[str] = Field(None, description="Register type: holding, input, or coils")
    category: str = Field("NATIVE", description="Point category: NATIVE, STANDARDIZED, or VIRTUAL")
    deleted_at: Optional[datetime] = Field(None, description="Soft-delete timestamp; null means active")

    model_config = {
        "from_attributes": True,
    }


class TimeseriesPoint(BaseModel):
    time: datetime = Field(validation_alias=AliasChoices("time", "timestamp"))
    value: Optional[float] = Field(None, validation_alias=AliasChoices("value", "derived_value"))
    translated_value: Optional[Union[str, Dict[str, int]]] = None

    model_config = {"populate_by_name": True}


class PointTimeseries(BaseModel):
    id: int = Field(validation_alias=AliasChoices("id", "device_point_id"))
    name: str
    data_type: str
    unit: Optional[str] = None
    count: int = 0
    enum_map: Optional[Dict[str, str]] = None
    bit_labels: Optional[List[str]] = None
    timeseries: List[TimeseriesPoint] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class PointLatest(BaseModel):
    id: int = Field(validation_alias=AliasChoices("id", "device_point_id"))
    name: str
    data_type: str
    unit: Optional[str] = None
    time: Optional[datetime] = Field(None, validation_alias=AliasChoices("time", "timestamp"))
    value: Optional[float] = Field(None, validation_alias=AliasChoices("value", "derived_value"))
    translated_value: Optional[Union[str, Dict[str, int]]] = None

    model_config = {"populate_by_name": True}


class TimeseriesMeta(BaseModel):
    site_id: int
    device_id: int
    point_ids: Optional[List[int]]
    total_count: int
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class LatestMeta(BaseModel):
    site_id: int
    device_id: int
    point_ids: Optional[List[int]]
    total_count: int


class TimeseriesResponse(BaseModel):
    meta: TimeseriesMeta
    readings: Dict[str, PointTimeseries]


class LatestResponse(BaseModel):
    meta: LatestMeta
    readings: Dict[str, PointLatest]
