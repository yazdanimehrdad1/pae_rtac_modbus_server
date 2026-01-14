"""Database models for TimescaleDB hypertables."""

from datetime import datetime
from typing import Optional, Dict, Any, List, Literal
from pydantic import BaseModel, Field
from uuid import UUID

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
    main_type: str = Field(..., min_length=1, max_length=255, description="Device main type (required)")
    sub_type: Optional[str] = Field(default=None, max_length=255, description="Device sub type (optional)")
    poll_address: Optional[int] = Field(None, description="Start address for polling Modbus registers")
    poll_count: Optional[int] = Field(None, description="Number of registers to read during polling")
    poll_kind: Optional[str] = Field(None, description="Register type: holding, input, coils, or discretes")
    poll_enabled: bool = Field(True, description="Whether polling is enabled for this device")
    site_id: Optional[str] = Field(default=None, description="Site ID (UUID) to associate this device with")


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
    main_type: Optional[str] = Field(None, min_length=1, max_length=255, description="Device main type")
    sub_type: Optional[str] = Field(None, max_length=255, description="Device sub type")
    poll_address: Optional[int] = Field(None, ge=0, le=65535, description="Start address for polling Modbus registers")
    poll_count: Optional[int] = Field(None, ge=1, description="Number of registers to read during polling")
    poll_kind: Optional[str] = Field(None, description="Register type: holding, input, coils, or discretes")
    poll_enabled: Optional[bool] = Field(None, description="Whether polling is enabled for this device")
    site_id: Optional[str] = Field(None, description="Site ID (UUID) to associate this device with. Set to null to remove association.")


class DeviceListItem(BaseModel):
    """Response model for device data in list views (without register_map for performance)."""
    id: int = Field(..., description="Device ID")
    name: str = Field(..., description="Device name")
    host: str = Field(..., description="Device hostname or IP address")
    port: int = Field(..., description="Modbus TCP port")
    device_id: int = Field(..., description="Modbus unit/slave ID")
    description: Optional[str] = Field(None, description="Device description")
    main_type: str = Field(..., description="Device main type")
    sub_type: Optional[str] = Field(None, description="Device sub type")
    poll_address: Optional[int] = Field(None, description="Start address for polling Modbus registers")
    poll_count: Optional[int] = Field(None, description="Number of registers to read during polling")
    poll_kind: Optional[str] = Field(None, description="Register type: holding, input, coils, or discretes")
    poll_enabled: bool = Field(True, description="Whether polling is enabled for this device")
    site_id: Optional[str] = Field(None, description="Site ID (UUID) this device is associated with")
    created_at: datetime = Field(..., description="Timestamp when device was created")
    updated_at: datetime = Field(..., description="Timestamp when device was last updated")
    
    model_config = {
        "from_attributes": True,
    }


class DeviceResponse(DeviceListItem):
    """Response model for device data with optional register map."""
    register_map: Optional[Dict[str, Any]] = Field(None, description="Device register map (loaded lazily from DB/CSV)")


class Coordinates(BaseModel):
    """Coordinates model for site location."""
    lat: float = Field(..., description="Latitude")
    lng: float = Field(..., description="Longitude")


class SiteCreate(BaseModel):
    """Request model for creating a new site."""
    owner: str = Field(..., min_length=1, max_length=255, description="Site owner")
    name: str = Field(..., min_length=1, max_length=255, description="Site name")
    location: str = Field(..., min_length=1, max_length=255, description="Site location")
    operator: str = Field(..., min_length=1, max_length=255, description="Site operator")
    capacity: str = Field(..., min_length=1, max_length=255, description="Site capacity")
    description: Optional[str] = Field(default=None, description="Optional site description")
    coordinates: Optional[Coordinates] = Field(default=None, description="Geographic coordinates")


class SiteUpdate(BaseModel):
    """Request model for updating a site."""
    owner: Optional[str] = Field(None, min_length=1, max_length=255, description="Site owner")
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Site name")
    location: Optional[str] = Field(None, min_length=1, max_length=255, description="Site location")
    operator: Optional[str] = Field(None, min_length=1, max_length=255, description="Site operator")
    capacity: Optional[str] = Field(None, min_length=1, max_length=255, description="Site capacity")
    description: Optional[str] = Field(None, description="Site description")
    coordinates: Optional[Coordinates] = Field(None, description="Geographic coordinates")


class SiteResponse(BaseModel):
    """Response model for site data."""
    id: str = Field(..., description="Site ID (UUID)")
    owner: str = Field(..., description="Site owner")
    name: str = Field(..., description="Site name")
    location: str = Field(..., description="Site location")
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


class RegisterMapMetadata(BaseModel):
    """Metadata for a register map."""
    ID: Optional[int] = Field(default=None, description="Register map ID")
    device_id: Optional[int] = Field(default=None, description="Device ID")
    start_register_address: int = Field(..., ge=0, le=65535, description="Starting register address")
    end_register_address: int = Field(..., ge=0, le=65535, description="Ending register address")
    type: Literal["holding", "input", "coil", "discrete"] = Field(..., description="Register type: holding, input, coil, or discrete")
    overflow: bool = Field(default=False, description="Whether overflow is enabled")
    expand: Optional[bool] = Field(default=None, description="Whether to expand the register map for bitfield and enum definitions")


class RegisterMapRegister(BaseModel):
    """Single register definition in a register map."""
    register_address: int = Field(..., ge=0, le=65535, description="Modbus register address")
    register_name: str = Field(..., description="Human-readable name/label for this register")
    size: int = Field(..., ge=1, description="Number of registers/bits")
    data_type: Literal["int16", "uint16", "int32", "uint32", "float32", "int64", "uint64", "float64", "bool", "bitfield32", "enum"] = Field(
        ..., 
        description="Data type interpretation. Can be standard types (int16, uint16, float32, etc.) or special types (bitfield32, enum)"
    )
    scale_factor: Optional[float] = Field(default=None, description="Scale factor to apply to raw value")
    unit: Optional[str] = Field(default=None, description="Physical unit (e.g., 'V', 'A', 'kW')")
    bitfield_definition: Optional[Dict[str, str]] = Field(
        default=None, 
        description="Bitfield definition: maps bit position (as string) to definition name. Example: {'0': 'alarm', '1': 'warning', '2': 'fault'}"
    )
    enum_definition: Optional[Dict[str, str]] = Field(
        default=None,
        description="Enum definition: maps register value (as string) to definition name. Example: {'0': 'Off', '1': 'On', '2': 'Standby'}"
    )


class RegisterMapCreate(BaseModel):
    """
    Request model for creating a register map.
    
    The register map structure:
    {
        "metadata": {
            "ID": int (optional),
            "device_id": int (optional),
            "start_register_address": int (required, 0-65535),
            "end_register_address": int (required, 0-65535, must be >= start_register_address),
            "type": str (required, one of: "holding", "input", "coil", "discrete"),
            "overflow": bool (optional, default: false),
            "expand": bool (optional, whether to expand the register map for bitfield and enum definitions)
        },
        "registers": [
            {
                "register_address": int (required, 0-65535),
                "register_name": str (required),
                "size": int (required, >= 1),
                "data_type": str (required, one of: "int16", "uint16", "int32", "uint32", "float32", "int64", "uint64", "float64", "bool", "bitfield32", "enum"),
                "scale_factor": float (optional),
                "unit": str (optional, e.g., "V", "A", "kW"),
                "bitfield_definition": object (optional, maps bit positions as strings to definition names, e.g., {"0": "definition_0", "1": "definition_1"}),
                "enum_definition": object (optional, maps values as strings to definition names, e.g., {"0": "enum_definition_0", "1": "enum_definition_1"})
            },
            ...
        ]
    }
    """
    metadata: RegisterMapMetadata = Field(..., description="Register map metadata")
    registers: List[RegisterMapRegister] = Field(..., min_length=1, description="List of register definitions")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for database storage."""
        return {
            "metadata": self.metadata.model_dump(exclude_none=True),
            "registers": [reg.model_dump(exclude_none=True) for reg in self.registers]
        }


__all__ = ["DeviceCreate", "DeviceUpdate", "DeviceListItem", "DeviceResponse", 
           "Coordinates", "SiteCreate", "SiteUpdate", "SiteResponse", 
           "RegisterMapMetadata", "RegisterMapRegister", "RegisterMapCreate"]
