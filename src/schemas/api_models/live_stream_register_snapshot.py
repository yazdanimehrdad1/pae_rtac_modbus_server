"""Pydantic models for the live stream register snapshot debugging endpoint."""

from typing import List, Optional, Union

from pydantic import BaseModel


class LiveStreamRegisterSnapshotEntry(BaseModel):
    address: int
    values: List[Optional[Union[int, float]]]
    label: str = "unknown"
    data_type: str = "int16"


class LiveStreamRegisterSnapshotResponse(BaseModel):
    timestamps: List[str]
    registers: List[LiveStreamRegisterSnapshotEntry]
