"""Pydantic models for the modbus raw registers live data streaming feature."""

from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, model_validator


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
    labels: Optional[Dict[str, str]] = Field(
        None,
        description="Optional label per address, e.g. {\"1400\": \"voltage\", \"1401\": \"current\"}",
    )

    @model_validator(mode="after")
    def _validate_range(self) -> "RawRegistersLiveParams":
        if self.end_address < self.start_address:
            raise ValueError("end_address must be >= start_address")
        if (self.end_address - self.start_address + 1) > 125:
            raise ValueError("Address range must be <= 125 registers (single Modbus frame limit)")
        return self

    def int_labels(self) -> dict[int, str]:
        if not self.labels:
            return {}
        return {int(k): v for k, v in self.labels.items()}


class RawRegistersLiveRegister(BaseModel):
    value: int
    label: Optional[str] = None


class RawRegistersLiveEvent(BaseModel):
    timestamp: datetime
    poll: int
    registers: Dict[str, RawRegistersLiveRegister]


class RawRegistersLiveErrorEvent(BaseModel):
    error: str
    poll: int


class RawRegistersLiveDoneEvent(BaseModel):
    total_polls: int
    duration_s: int


class RawRegistersLiveConnectedEvent(BaseModel):
    session_id: str
