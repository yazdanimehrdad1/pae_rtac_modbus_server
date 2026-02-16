"""API mapper models shared across endpoints."""

from typing import Optional, Union
from pydantic import BaseModel, Field


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
