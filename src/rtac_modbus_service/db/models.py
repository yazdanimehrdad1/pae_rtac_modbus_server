"""Database models for TimescaleDB hypertables.

This module is kept for backward compatibility. 
New code should import from rtac_modbus_service.schemas.db_models
"""

# Import from schemas location
from rtac_modbus_service.schemas.db_models.models import *

# TODO: Define SQLAlchemy models in schemas/db_models/models.py:
# - Time-series point table (hypertable)
# - Metadata tables
# - TimescaleDB extension setup

