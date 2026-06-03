"""Modbus register map models."""

from typing import List
from pydantic import BaseModel, Field

from schemas.modbus_models.points import RegisterPoint


class RegisterMap(BaseModel):
    """Collection of register points defining a device's register layout."""
    points: List[RegisterPoint] = Field(default_factory=list)
