from pydantic import BaseModel, Field
from typing import List, Optional

class PointValidationError(BaseModel):
    """Detailed information about a point validation failure."""
    index: int
    message: Optional[str] = None
    field: Optional[str] = None
    address: Optional[int] = None
    size: Optional[int] = None
    max_address: Optional[int] = None
    error: Optional[str] = None

class PointAddressValidationResult(BaseModel):
    """Container for point address validation results."""
    missing_fields: List[PointValidationError] = Field(default_factory=list)
    invalid_registers: List[PointValidationError] = Field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return bool(self.missing_fields or self.invalid_registers)
