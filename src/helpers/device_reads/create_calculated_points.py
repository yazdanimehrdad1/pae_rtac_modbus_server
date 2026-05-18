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
- Input: a merged point+reading dict (same shape as `LatestDevicePointReadingDict`).
- Output: `List[MergedPointMetadataToReading]` where each element is:
  {
    "device_point_id": row.device_point_id,
    "register_address": row.register_address,
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


from typing import Dict, Any

from schemas.api_models.types import (
    LatestDevicePointReadingModel,
    MergedPointMetadataToReadingModel,
)
from schemas.modbus_models import RegisterMap, RegisterPoint
from helpers.reads.calculate_reads import (
    build_bitfield_payload,
    build_enum_payload,
    build_scaled_payload,
)

from constants import BITS_PER_REGISTER_16_BIT, MAX_BITFIELD_BITS_32_BIT


def create_calculated_points(
    point_reading: LatestDevicePointReadingModel,
) -> MergedPointMetadataToReadingModel:
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
    derived_value = point_reading.derived_value
    bit_count = point_reading.bit_count or BITS_PER_REGISTER_16_BIT
    bit_count = min(bit_count, MAX_BITFIELD_BITS_32_BIT)

    if derived_value is None:
        calculated_value = None
    elif point_reading.data_type == "bitfield":
        calculated_value = build_bitfield_payload(
            derived_value=derived_value,
            bitfield_detail=point_reading.bitfield_detail or {},
            bit_count=bit_count
        )
    elif point_reading.data_type == "enum":
        calculated_value = build_enum_payload(
            derived_value=derived_value,
            enum_detail=point_reading.enum_detail or {}
        )
    else:
        calculated_value = build_scaled_payload(
            derived_value=derived_value,
            scale_factor=point_reading.scale_factor
        )

    return MergedPointMetadataToReadingModel(
        device_point_id=point_reading.device_point_id,
        register_address=point_reading.register_address,
        name=point_reading.name,
        data_type=point_reading.data_type,
        unit=point_reading.unit,
        scale_factor=point_reading.scale_factor,
        is_derived=point_reading.is_derived,
        timestamp=point_reading.timestamp,
        derived_value=derived_value,
        calculated_value=calculated_value,
    )


def json_to_register_map(json_data: Dict[str, Any]) -> RegisterMap:
    """
    Convert JSON structure (from map_csv_to_json) to RegisterMap object.

    Args:
        json_data: Dictionary with 'metadata' and 'registers' keys from map_csv_to_json

    Returns:
        RegisterMap object with RegisterPoint objects
    """
    registers = json_data.get("registers", [])
    points = []

    for reg in registers:
        point_data = {
            "name": (
                reg.get("name")
                or reg.get("register_name")
                or reg.get("point_name", "")
            ),
            "address": (
                reg.get("address")
                or reg.get("register_address")
                or reg.get("point_address")
            ),
            "data_type": reg.get("data_type", reg.get("point_data_type", "uint16")),
            "size": reg.get("size", reg.get("point_size", 1)),
            "scale_factor": reg.get("scale_factor", reg.get("point_scale_factor", 1.0)),
            "unit": reg.get("unit", reg.get("point_unit")),
            "bitfield_detail": reg.get("bitfield_detail", reg.get("point_bitfield_detail")),
            "enum_detail": reg.get("enum_detail", reg.get("point_enum_detail")),
        }
        points.append(RegisterPoint(**point_data))

    return RegisterMap(points=points)
