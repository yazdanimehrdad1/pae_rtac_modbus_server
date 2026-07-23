"""API mapper models shared across endpoints."""

from typing import Union
from pydantic import BaseModel, Field


class RegisterValue(BaseModel):
    """Simple register value pair for POST /read endpoint."""
    register_number: int = Field(..., description="Register address number", alias="register")
    value: Union[int, bool] = Field(..., description="Register value")

    model_config = {"populate_by_name": True}
