"""Error types and translator for SSE streaming connections."""

from pymodbus.exceptions import ConnectionException, ModbusException


class RawRegistersLiveConnectionError(Exception):
    """Raised when the TCP connection to the Modbus device cannot be established or is lost."""


class RawRegistersLiveReadError(Exception):
    """Raised when a Modbus read returns an error response."""


def translate_raw_registers_live_error(exc: Exception, host: str, port: int) -> str:
    """Return a human-readable message for any exception raised during a raw registers live session."""
    if isinstance(exc, RawRegistersLiveConnectionError):
        return str(exc)
    if isinstance(exc, RawRegistersLiveReadError):
        return str(exc)
    if isinstance(exc, ConnectionException):
        return f"Failed to connect to {host}:{port}"
    if isinstance(exc, ModbusException):
        return f"Modbus error: {exc}"
    if isinstance(exc, TimeoutError):
        return f"Connection to {host}:{port} timed out"
    return f"Unexpected error: {exc}"
