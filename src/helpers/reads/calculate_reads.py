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


def translate_enum_value(derived_value: float, enum_detail: EnumDetailMap) -> Optional[str]:
    """
    Return the human-readable label for derived_value from an enum_detail map.

    Supports two formats:
    - Simple: {"0": "OFF", "1": "ON"}  — key is the register value
    - Embedded: {"s1": "1:OFF", "s2": "2:ON"}  — value encodes register value and label
    """
    target = int(derived_value)

    # Direct key lookup (most common format)
    direct = enum_detail.get(str(target))
    if direct is not None:
        # Value might itself be "label" or "value:label"; return the label part
        _, label = _parse_enum_detail(direct)
        return label if label else direct

    # Fallback: scan values for embedded "value:label" pairs
    for raw in enum_detail.values():
        parsed_value, parsed_label = _parse_enum_detail(raw)
        if parsed_value == target and parsed_label:
            return parsed_label

    return "UNKNOWN"


def translate_bitfield_to_named_map(
    derived_value: float,
    bitfield_detail: BitfieldDetailMap,
) -> Dict[str, int]:
    """
    Returns {label: 0|1} for every named bit in bitfield_detail, ordered by bit position.
    Iterates only the named entries — no need to know total bit count.
    """
    int_value = int(derived_value)
    details = normalize_detail_keys(bitfield_detail, "bit-")
    result: Dict[str, int] = {}
    for key, label in sorted(details.items()):
        try:
            bit_index = int(key.split("-", 1)[1])
            result[label] = (int_value >> bit_index) & 1
        except (IndexError, ValueError):
            continue
    return result


def translate_reading(
    derived_value: Optional[float],
    bitfield_detail: Optional[BitfieldDetailMap],
    enum_detail: Optional[EnumDetailMap],
) -> "Optional[Dict[str, int] | str]":
    """
    Translate a raw derived_value to a human-readable form using the point's detail maps.

    Returns {label: 0|1} for bitfield points, a label string for enum points,
    or None for numeric-only points or when derived_value is None.
    """
    if derived_value is None:
        return None
    if bitfield_detail:
        return translate_bitfield_to_named_map(derived_value, bitfield_detail)
    if enum_detail:
        return translate_enum_value(derived_value, enum_detail)
    return None


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


