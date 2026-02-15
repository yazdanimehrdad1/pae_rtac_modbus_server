"""Device point data types."""

from typing import Optional, TypedDict


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
