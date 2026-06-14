"""SSE generator for the modbus raw registers live data streaming feature."""

import asyncio
import time
from datetime import datetime, timezone
from typing import AsyncGenerator

from pydantic import BaseModel

from config import settings
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
    return f"event: {event}\ndata: {payload.model_dump_json(exclude_none=True)}\n\n"


async def raw_registers_live_generator(params: RawRegistersLiveParams) -> AsyncGenerator[str, None]:
    session_id, cancel_event = session_store.register()
    yield _sse("connected", RawRegistersLiveConnectedEvent(session_id=session_id))

    labels = params.int_labels()
    offset = -1 if params.address_mode == "one_based" else 0
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
                registers = {
                    str(params.start_address + i): RawRegistersLiveRegister(
                        value=v,
                        label=labels.get(params.start_address + i),
                    )
                    for i, v in enumerate(registers_raw)
                }
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
