"""API request/response models."""

from typing import Optional, Literal, List, Union
from pydantic import BaseModel, Field


class ReadRequest(BaseModel):
    """Request model for reading Modbus registers."""
    kind: Literal["holding", "input", "coils", "discretes"] = Field(
        ..., description="Type of register to read"
    )
    address: int = Field(..., ge=0, le=65535, description="Starting address")
    count: int = Field(..., ge=1, le=2000, description="Number of registers/bits to read")
    unit_id: Optional[int] = Field(None, ge=1, le=255, description="Modbus unit ID (optional)")


class RegisterData(BaseModel):
    """Individual register data item with name, value, and type."""
    name: str = Field(..., description="Register name from register map")
    value: Union[int, bool] = Field(..., description="Register value")
    Type: Optional[str] = Field(None, description="Data type of the register")
    scale_factor: Optional[float] = Field(None, description="Scale factor to apply to raw value")
    unit: Optional[str] = Field(None, description="Physical unit (e.g., 'V', 'A', 'kW')")
    
    model_config = {
        "populate_by_name": True,
        "json_encoders": {},
    }


class RegisterValue(BaseModel):
    """Simple register value pair for POST /read endpoint."""
    register_number: int = Field(..., description="Register address number", alias="register")
    value: Union[int, bool] = Field(..., description="Register value")
    
    model_config = {"populate_by_name": True}


class ReadResponse(BaseModel):
    """Response model for read operations."""
    ok: bool
    timestamp: str = Field(..., description="ISO format timestamp of when the read operation completed")
    kind: str
    address: int
    count: int
    unit_id: int
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
    unit_id: int
    data: List[RegisterValue] = Field(
        default_factory=list, description="Array of register number and value pairs"
    )


class HealthResponse(BaseModel):
    """Response model for health check."""
    ok: bool
    host: str
    port: int
    unit_id: int
    detail: Optional[str] = None
