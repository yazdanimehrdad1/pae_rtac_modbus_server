"""Modbus live stream raw registers endpoint — streams register reads over SSE."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from helpers.live_stream_raw_registers import live_stream_raw_registers_generator
from schemas.api_models.live_stream_raw_registers import LiveStreamRawRegistersParams
from services.server_sent_events import session_store

router = APIRouter(prefix="/modbus-live-stream-raw-registers", tags=["modbus-live-stream-raw-registers"])


@router.post("/stream", response_class=StreamingResponse)
async def start_live_stream_raw_registers(params: LiveStreamRawRegistersParams):
    """
    Stream live Modbus raw register reads over Server-Sent Events.

    Connects to the target device, polls the specified register range at the given
    interval, and emits SSE events until duration expires or the client disconnects.

    Events:
    - connected: first event, contains session_id for use with the stop endpoint
    - poll: one reading per interval with all register values
    - error: Modbus or connection error (stream continues unless unrecoverable)
    - done: emitted once when the session ends
    """
    return StreamingResponse(
        live_stream_raw_registers_generator(params),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.delete("/stream/{session_id}", status_code=200)
async def stop_live_stream_raw_registers(session_id: str):
    """Stop a running live stream raw registers session by session_id (from the connected event)."""
    if not session_store.cancel(session_id):
        raise HTTPException(status_code=404, detail="Session not found or already stopped")
    return {"stopped": session_id}
