"""Typed helpers for API models."""

from datetime import datetime
from typing import Literal, Optional, TypeAlias, Union
from typing_extensions import TypedDict

from pydantic import BaseModel, Field


class DevicePointData(BaseModel):
    """Pydantic model for a device point row to be written to the database."""
    site_id: int
    device_id: int
    address: int
    name: str
    size: int
    data_type: str
    category: Literal["NATIVE", "STANDARDIZED", "VIRTUAL"] = "NATIVE"
    scale_factor: Optional[float] = None
    unit: Optional[str] = None
    bitfield_detail: Optional[dict[str, str]] = None
    enum_detail: Optional[dict[str, str]] = None
    byte_order: str = "big-endian"
    word_order: str = "msw_first"
    register_offset: float = 0.0


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


class BitfieldEntry(TypedDict, total=False):
    value: int
    detail: str


BitfieldDetailMap: TypeAlias = dict[str, str]
BitfieldPayload: TypeAlias = dict[str, BitfieldEntry]


class EnumEntry(TypedDict, total=False):
    value: int
    detail: str


EnumDetailMap: TypeAlias = dict[str, str]
EnumPayload: TypeAlias = dict[str, EnumEntry]


CalculatedValue: TypeAlias = Union[BitfieldPayload, EnumPayload, float]


class MergedPointMetadataToReading(TypedDict):
    device_point_id: int
    register_address: int
    name: str
    data_type: str
    unit: Optional[str]
    scale_factor: Optional[float]
    timestamp: datetime
    derived_value: Optional[float]
    calculated_value: Optional[CalculatedValue]


class LatestDevicePointReadingModel(BaseModel):
    device_point_id: int
    register_address: int
    name: str
    data_type: str
    unit: Optional[str]
    scale_factor: Optional[float]
    timestamp: datetime
    derived_value: Optional[float]
    bitfield_detail: Optional[BitfieldDetailMap] = None
    enum_detail: Optional[EnumDetailMap] = None
    bit_count: Optional[int] = None


class MergedPointMetadataToReadingModel(BaseModel):
    device_point_id: int
    register_address: int
    name: str
    data_type: str
    unit: Optional[str]
    scale_factor: Optional[float]
    timestamp: datetime
    derived_value: Optional[float]
    calculated_value: Optional[CalculatedValue]


class PointReadSeriesItemModel(BaseModel):
    timestamp: datetime
    raw_value: Optional[float] = None
    calculated_value: Optional[CalculatedValue]
