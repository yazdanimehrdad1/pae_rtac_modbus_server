"""Schema module - organized by domain."""

# Convenience imports for common schemas
from schemas.api_models import (
    ReadRequest,
    ReadResponse,
    HealthResponse,
)
from schemas.modbus_models import (
    RegisterPoint,
    RegisterMap,
)

__all__ = [
    # API models
    "ReadRequest",
    "ReadResponse",
    "HealthResponse",
    # Modbus models
    "RegisterPoint",
    "RegisterMap",
]

