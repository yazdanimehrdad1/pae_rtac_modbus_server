"""Modbus register map models."""

from typing import Optional
from pydantic import BaseModel, Field

from schemas.modbus_models.points import RegisterPoint


class RegisterMap(BaseModel):
    """Container for a collection of register points."""
    points: list[RegisterPoint] = Field(..., description="List of register points to read")

    def get_point_by_name(self, name: str) -> Optional[RegisterPoint]:
        """Get a point by its register_name."""
        for p in self.points:
            if p.register_name == name:
                return p
        return None
