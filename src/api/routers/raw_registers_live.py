"""Modbus raw registers live data endpoint — streams register reads over SSE."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from helpers.raw_registers_live import raw_registers_live_generator
from schemas.api_models.raw_registers_live import RawRegistersLiveParams
from services.server_sent_events import session_store

router = APIRouter(prefix="/modbus-raw-registers-live", tags=["modbus-raw-registers-live"])


@router.post("/stream", response_class=StreamingResponse)
async def start_raw_registers_live_stream(params: RawRegistersLiveParams):
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
        raw_registers_live_generator(params),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.delete("/stream/{session_id}", status_code=200)
async def stop_raw_registers_live_stream(session_id: str):
    """Stop a running raw registers live session by session_id (from the connected event)."""
    if not session_store.cancel(session_id):
        raise HTTPException(status_code=404, detail="Session not found or already stopped")
    return {"stopped": session_id}
