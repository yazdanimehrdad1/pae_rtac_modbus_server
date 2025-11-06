"""Schema module - organized by domain."""

# Convenience imports for common schemas
from rtac_modbus_service.schemas.api_models import (
    ReadRequest,
    ReadResponse,
    HealthResponse,
)
from rtac_modbus_service.schemas.modbus_models import (
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

