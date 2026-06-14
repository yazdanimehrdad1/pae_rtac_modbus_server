"""Pydantic models for the modbus raw registers live data streaming feature."""

from datetime import datetime
from typing import Dict, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator


_VALID_DATA_TYPES: frozenset[str] = frozenset({
    "int16", "uint16", "bool", "raw",
    "int32", "uint32", "float32",
    "int64", "uint64", "float64",
})


class RawRegistersLiveRegisterConfig(BaseModel):
    label: Optional[str] = None
    data_type: str = "int16"
    byte_order: Optional[Literal["big", "little"]] = None
    word_order: Optional[Literal["msw_first", "lsw_first"]] = None

    @field_validator("data_type", mode="before")
    @classmethod
    def _coerce_data_type(cls, v: object) -> str:
        if v not in _VALID_DATA_TYPES:
            return "int16"
        return str(v)


class RawRegistersLiveParams(BaseModel):
    host: str = Field(..., description="Modbus device IP/hostname")
    port: int = Field(502, ge=1, le=65535)
    server_address: int = Field(1, ge=1, le=255, description="Modbus unit/slave ID")
    kind: Literal["holding", "input"] = Field("holding")
    start_address: int = Field(..., ge=0, le=65535)
    end_address: int = Field(..., ge=0, le=65535)
    address_mode: Literal["zero_based", "one_based"] = Field(
        "zero_based",
        description="zero_based: address sent as-is; one_based: subtract 1 before sending to device",
    )
    interval: float = Field(1.0, ge=0.5, le=60.0, description="Seconds between polls")
    duration: int = Field(3600, ge=1, le=3600, description="Session length in seconds, max 1 hour")
    byte_order: Literal["big", "little"] = Field("big")
    word_order: Literal["msw_first", "lsw_first"] = Field("msw_first")
    register_configs: Optional[Dict[str, RawRegistersLiveRegisterConfig]] = Field(
        None,
        description="Optional per-address config, e.g. {\"1400\": {\"label\": \"voltage\", \"data_type\": \"float32\"}}",
    )

    @model_validator(mode="after")
    def _validate_range(self) -> "RawRegistersLiveParams":
        if self.end_address < self.start_address:
            raise ValueError("end_address must be >= start_address")
        if (self.end_address - self.start_address + 1) > 125:
            raise ValueError("Address range must be <= 125 registers (single Modbus frame limit)")
        return self

    def int_register_configs(self) -> dict[int, RawRegistersLiveRegisterConfig]:
        if not self.register_configs:
            return {}
        return {int(k): v for k, v in self.register_configs.items()}


class RawRegistersLiveRegister(BaseModel):
    value: Optional[Union[int, float]] = None
    label: Optional[str] = None
    data_type: str = "int16"


class RawRegistersLiveEvent(BaseModel):
    timestamp: datetime
    poll: int
    registers: Dict[str, Optional[RawRegistersLiveRegister]]


class RawRegistersLiveErrorEvent(BaseModel):
    error: str
    poll: int


class RawRegistersLiveDoneEvent(BaseModel):
    total_polls: int
    duration_s: int


class RawRegistersLiveConnectedEvent(BaseModel):
    session_id: str
