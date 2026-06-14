"""SSE generator for the modbus raw registers live data streaming feature."""

import asyncio
import time
from datetime import datetime, timezone
from typing import AsyncGenerator, Optional

from pydantic import BaseModel

from config import settings
from helpers.modbus.modbus_data_mapping import _decode_modbus_point_value
from schemas.api_models.raw_registers_live import (
    RawRegistersLiveConnectedEvent,
    RawRegistersLiveDoneEvent,
    RawRegistersLiveErrorEvent,
    RawRegistersLiveEvent,
    RawRegistersLiveParams,
    RawRegistersLiveRegister,
)
from services.server_sent_events import (
    RawRegistersLiveConnection,
    RawRegistersLiveConnectionError,
    translate_raw_registers_live_error,
)
from services.server_sent_events import session_store


def _sse(event: str, payload: BaseModel) -> str:
    return f"event: {event}\ndata: {payload.model_dump_json()}\n\n"


def _register_size(data_type: str) -> int:
    if data_type in ("uint32", "int32", "float32"):
        return 2
    if data_type in ("uint64", "int64", "float64"):
        return 4
    return 1


def _build_registers(
    registers_raw: list[int],
    params: RawRegistersLiveParams,
) -> dict[str, Optional[RawRegistersLiveRegister]]:
    configs = params.int_register_configs()
    count = params.end_address - params.start_address + 1

    consumed: set[int] = set()
    for addr, cfg in configs.items():
        for j in range(1, _register_size(cfg.data_type)):
            consumed.add(addr + j)

    registers: dict[str, Optional[RawRegistersLiveRegister]] = {}
    i = 0
    while i < count:
        addr = params.start_address + i
        cfg = configs.get(addr)

        if addr in consumed:
            i += 1
            continue

        data_type = cfg.data_type if cfg else "int16"
        size = _register_size(data_type)
        raw_vals = registers_raw[i:i + size]

        effective_byte_order = (cfg.byte_order if cfg and cfg.byte_order else None) or params.byte_order
        effective_word_order = (cfg.word_order if cfg and cfg.word_order else None) or params.word_order
        result = _decode_modbus_point_value(
            register_values=raw_vals,
            data_type=data_type,
            byte_order=effective_byte_order,
            word_order=effective_word_order,
        )
        value = result.value if result.success else None

        registers[str(addr)] = RawRegistersLiveRegister(
            value=value,
            label=(cfg.label if cfg else None) or "unknown",
            data_type=data_type,
        )
        i += size

    return registers


async def raw_registers_live_generator(params: RawRegistersLiveParams) -> AsyncGenerator[str, None]:
    session_id, cancel_event = session_store.register()
    yield _sse("connected", RawRegistersLiveConnectedEvent(session_id=session_id))

    offset = -1 if params.modbus_address_mode == "one_based" else 0
    count = params.end_address - params.start_address + 1
    modbus_start = params.start_address + offset

    connection = RawRegistersLiveConnection(
        host=params.host,
        port=params.port,
        timeout=settings.modbus_timeout_s,
    )
    deadline = time.monotonic() + params.duration
    poll_count = 0

    try:
        try:
            await connection.connect()
        except RawRegistersLiveConnectionError as exc:
            yield _sse("error", RawRegistersLiveErrorEvent(error=str(exc), poll=0))
            return

        while time.monotonic() < deadline and not cancel_event.is_set():
            t0 = time.monotonic()
            try:
                registers_raw = await connection.read(
                    kind=params.kind,
                    address=modbus_start,
                    count=count,
                    device_id=params.server_address,
                )
                poll_count += 1
                registers = _build_registers(registers_raw, params)
                yield _sse("poll", RawRegistersLiveEvent(
                    timestamp=datetime.now(timezone.utc),
                    poll=poll_count,
                    registers=registers,
                ))

            except Exception as exc:
                msg = translate_raw_registers_live_error(exc, params.host, params.port)
                yield _sse("error", RawRegistersLiveErrorEvent(error=msg, poll=poll_count))

            elapsed = time.monotonic() - t0
            remaining = max(0.0, params.interval - elapsed)
            try:
                await asyncio.wait_for(cancel_event.wait(), timeout=remaining)
                break  # cancel was set during sleep
            except asyncio.TimeoutError:
                pass   # normal interval expiry

    finally:
        session_store.unregister(session_id)
        await connection.close()
        yield _sse("done", RawRegistersLiveDoneEvent(total_polls=poll_count, duration_s=params.duration))
