"""API mapper models shared across endpoints."""


from pydantic import BaseModel, Field


class RegisterValue(BaseModel):
    """Simple register value pair for POST /read endpoint."""
    register_number: int = Field(..., description="Register address number", alias="register")
    value: int | bool = Field(..., description="Register value")

    model_config = {"populate_by_name": True}
