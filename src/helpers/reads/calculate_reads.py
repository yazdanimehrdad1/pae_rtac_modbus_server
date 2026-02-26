"""Helpers for calculating derived read values."""

from typing import Any, Dict, List, Optional, Tuple

from schemas.api_models.types import (
    BitfieldDetailMap,
    BitfieldEntry,
    BitfieldPayload,
    EnumDetailMap,
    EnumEntry,
    EnumPayload,
)


def get_bitfield_value(value: Optional[float], bit_count: int) -> List[int]:
    """
    Convert an integer-like value into a list of bits (LSB -> MSB).

    Example:
    value=5, bit_count=4 -> [1, 0, 1, 0]
    """
    if value is None:
        return []
    int_value = int(value)
    return [(int_value >> bit) & 1 for bit in range(bit_count)]


def normalize_detail_keys(detail: Optional[BitfieldDetailMap | EnumDetailMap], prefix: str) -> Dict[str, Any]:
    """
    Normalize detail keys to include a prefix like "bit-" or "enum-".

    Example:
    {"01": "Trip"} -> {"enum-01": "Trip"}
    {"bit-01": "Closed"} -> {"bit-01": "Closed"}
    """
    if not detail:
        return {}
    normalized: Dict[str, Any] = {}
    for key, value in detail.items():
        normalized[key if key.startswith(prefix) else f"{prefix}{key}"] = value
    return normalized


def build_bitfield_payload(
    derived_value: float,
    bitfield_detail: BitfieldDetailMap,
    bit_count: int
) -> BitfieldPayload:
    """
    Build a bitfield payload with values and optional detail metadata.

    Example:
    {
      "bit-00": {"value": 1, "detail": "Closed"},
      "bit-01": {"value": 0, "detail": "Open"},
      "bit-02": {"value": 1, "detail": "Trip"},
      "bit-03": {"value": 0, "detail": "Trip-OFF"}
    }
    """
    bits = get_bitfield_value(derived_value, bit_count)
    details = normalize_detail_keys(bitfield_detail, "bit-")
    payload: BitfieldPayload = {}
    for bit_index, bit_value in enumerate(bits):
        key = f"bit-{bit_index:02d}"
        entry: BitfieldEntry = {"value": bit_value}
        if key in details:
            entry["detail"] = details[key]
        payload[key] = entry
    return payload


def _parse_enum_detail(raw: str) -> Tuple[Optional[int], Optional[str]]:
    for separator in (":", "|", ","):
        if separator in raw:
            value_str, detail = raw.split(separator, 1)
            value_str = value_str.strip()
            detail = detail.strip()
            if value_str.isdigit():
                return int(value_str), detail or None
            return None, raw
    if raw.strip().isdigit():
        return int(raw.strip()), None
    return None, raw


def build_enum_payload(
    derived_value: float,
    enum_detail: EnumDetailMap
) -> EnumPayload:
    """
    Build an enum payload, merging any enum detail mapping.

    Example:
    {
      "enum-01": {"value": 99, "detail": "Off"},
      "enum-02": {"value": 110, "detail": "Trip"}
    }
    """
    details = normalize_detail_keys(enum_detail, "enum-")
    payload: EnumPayload = {}
    for key, raw in details.items():
        try:
            enum_index = int(key.split("-", 1)[1])
        except (IndexError, ValueError):
            enum_index = None

        entry: EnumEntry = {}
        if isinstance(raw, dict):
            if "value" in raw and raw["value"] is not None:
                entry["value"] = int(raw["value"])
            if "detail" in raw and raw["detail"] is not None:
                entry["detail"] = str(raw["detail"])
        elif isinstance(raw, (int, float)):
            entry["value"] = int(raw)
        elif isinstance(raw, str):
            parsed_value, parsed_detail = _parse_enum_detail(raw)
            if parsed_value is not None:
                entry["value"] = parsed_value
            if parsed_detail:
                entry["detail"] = parsed_detail

        if "value" not in entry:
            if enum_index is not None:
                entry["value"] = enum_index
            else:
                entry["value"] = int(derived_value)

        payload[key] = entry
    return payload


def build_scaled_payload(
    derived_value: Optional[float],
    scale_factor: Optional[float]
) -> Optional[float]:
    """
    Apply scale factor to derived_value.

    Example:
    derived_value=599, scale_factor=0.1 -> 59.9
    """
    if derived_value is None:
        return None
    return derived_value * (scale_factor or 1.0)
