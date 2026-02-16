"""Typed helpers for API models."""

from typing import Optional, TypedDict, TypeAlias


class DevicePointData(TypedDict, total=False):
    """Type definition for device point data dictionary."""
    site_id: int
    device_id: int
    config_id: str
    address: int
    name: str
    size: int
    data_type: str
    scale_factor: Optional[float]
    unit: Optional[str]
    enum_value: Optional[str]
    bitfield_value: Optional[str]
    is_derived: bool
    bitfield_detail: Optional[dict[str, str]]
    enum_detail: Optional[dict[str, str]]
    byte_order: str


class PollResult(TypedDict, total=False):
    """Result of polling a single device."""
    device_name: str
    success: bool
    cache_successful: int
    cache_failed: int
    db_successful: int
    db_failed: int
    error: Optional[str]


ModbusRegisterValues: TypeAlias = list[int | bool]
