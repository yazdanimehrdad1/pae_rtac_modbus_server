"""
Derived point helpers (do not call yet).

Notes:
- Type definitions live in `schemas/api_models/types.py`.
- Read-calculation helpers live in `helpers/reads/calculate_reads.py`.
- Do not call these functions from elsewhere yet; we will wire them later.
- This module is intended for use by:
  - `routers/readings_registers.py`
  - `routers/readings_device.py`

High-level contract:
- Input: a `DevicePoint` + `DevicePointsReading` (joined by device_point_id).
- Output: `List[MergedPointMetadataToReading]` where each element is:
  {
    "device_point_id": row.device_point_id,
    "register_address": row.address,
    "name": row.name,
    "data_type": row.data_type,
    "unit": row.unit,
    "scale_factor": row.scale_factor,
    "is_derived": row.is_derived,
    "timestamp": row.timestamp,
    "derived_value": row.derived_value,
    "calculated_value": <computed by rules below>
  }

Rules for calculated_value:
1) Bitfield: expand bits of derived_value, attach optional bit detail.
2) Enum: expose the enum value and optional enum detail.
3) Scaled: derived_value * scale_factor.

Examples:
- Bitfield (derived_value=5 -> 0b0101):
  calculated_value = {
    "bit-00": {"value": 1, "detail": "..."},
    "bit-01": {"value": 0},
    ...
  }
- Enum:
  calculated_value = {"enum-02": {"value": 1, "detail": "Trip"}}
- Scaled:
  calculated_value = 123.4
"""

from typing import List, Optional

from schemas.db_models.orm_models import DevicePoint, DevicePointsReading
from schemas.api_models.types import MergedPointMetadataToReading
from helpers.reads.calculate_reads import (
    build_bitfield_payload,
    build_enum_payload,
    build_scaled_payload,
)

BITS_PER_REGISTER_16_BIT = 16
MAX_BITFIELD_BITS_32_BIT = 32


def create_calculated_points(
    device_point: DevicePoint,
    device_point_reading: DevicePointsReading
) -> List[MergedPointMetadataToReading]:
    """
    Create derived point payload for a single DevicePoint + DevicePointsReading.

    Example return shape:
    {
      "device_point_id": 10,
      "register_address": 1400,
      "name": "M_FREQ",
      "data_type": "bitfield",
      "unit": "Hz",
      "scale_factor": 0.1,
      "is_derived": false,
      "timestamp": "2026-02-19T12:00:00Z",
      "derived_value": 5,
      "calculated_value": {
        "bit-00": {"value": 1, "detail": "Closed"},
        "bit-01": {"value": 0, "detail": "Open"}
      }
    }

    For enum:
    {
      "calculated_value": {
        "enum-01": {"value": 99, "detail": "Off"},
        "enum-02": {"value": 110, "detail": "Trip"}
      }
    }

    For scaled:
    {"calculated_value": 59.9}
    """
    derived_value = device_point_reading.derived_value
    bit_count = min(device_point.size * BITS_PER_REGISTER_16_BIT, MAX_BITFIELD_BITS_32_BIT)

    if derived_value is None:
        calculated_value = None
    elif device_point.data_type == "bitfield":
        calculated_value = build_bitfield_payload(
            derived_value=derived_value,
            bitfield_detail=device_point.bitfield_detail or {},
            bit_count=bit_count
        )
    elif device_point.data_type == "enum":
        calculated_value = build_enum_payload(
            derived_value=derived_value,
            enum_detail=device_point.enum_detail or {}
        )
    else:
        calculated_value = build_scaled_payload(
            derived_value=derived_value,
            scale_factor=device_point.scale_factor
        )

    merged: MergedPointMetadataToReading = {
        "device_point_id": device_point.id,
        "register_address": device_point.address,
        "name": device_point.name,
        "data_type": device_point.data_type,
        "unit": device_point.unit,
        "scale_factor": device_point.scale_factor,
        "is_derived": device_point.is_derived,
        "timestamp": device_point_reading.timestamp,
        "derived_value": derived_value,
        "calculated_value": calculated_value,
    }

    return [merged]
