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


class HealthResponse(BaseModel):
    """Response model for health check."""
    ok: bool
    host: str
    port: int
    unit_id: int
    detail: Optional[str] = None
