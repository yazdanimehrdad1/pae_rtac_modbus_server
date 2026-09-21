"""Schema module - organized by domain."""

# Convenience imports for common schemas
from schemas.api_models import (
    HealthResponse,
)
from schemas.modbus_models import (
    RegisterMap,
    RegisterPoint,
)

__all__ = [
    # API models
    "HealthResponse",
    # Modbus models
    "RegisterPoint",
    "RegisterMap",
]

