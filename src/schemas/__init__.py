"""Schema module - organized by domain."""

# Convenience imports for common schemas
from schemas.api_models import (
    ReadRequest,
    HealthResponse,
)
from schemas.modbus_models import (
    RegisterPoint,
    RegisterMap,
)

__all__ = [
    # API models
    "ReadRequest",
    "HealthResponse",
    # Modbus models
    "RegisterPoint",
    "RegisterMap",
]

