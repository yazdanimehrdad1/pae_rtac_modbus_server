"""
Modbus helper functions.

Contains shared Modbus error translation logic for API and jobs.
"""

import os
from typing import Optional, Tuple

from dotenv import load_dotenv
from pymodbus.exceptions import ModbusException, ConnectionException
from pymodbus.pdu import ExceptionResponse

# Load environment variables from .env file
load_dotenv()

# Configuration from environment variables
AGGREGATOR_MODBUS_HOST = os.getenv("AGGREGATOR_MODBUS_HOST", "localhost")
AGGREGATOR_MODBUS_PORT = int(os.getenv("AGGREGATOR_MODBUS_PORT", "502"))
MODBUS_TIMEOUT_S = float(os.getenv("MODBUS_TIMEOUT_S", "5.0"))


def translate_modbus_error(
    error: Exception,
    host: Optional[str] = None,
    port: Optional[int] = None
) -> Tuple[int, str]:
    """
    Translate Modbus exceptions into appropriate HTTP status codes and messages.
    
    Args:
        error: The exception raised during Modbus operation
        host: Modbus server hostname or IP address (for error messages)
        port: Modbus server port (for error messages)
        
    Returns:
        Tuple of (HTTP status code, error message)
    """
    if isinstance(error, ConnectionException):
        error_host = host or AGGREGATOR_MODBUS_HOST
        error_port = port or AGGREGATOR_MODBUS_PORT
        return (
            503,  # HTTP_503_SERVICE_UNAVAILABLE
            f"Failed to connect to Modbus server at {error_host}:{error_port}"
        )
    elif isinstance(error, ExceptionResponse):
        # Modbus protocol errors (invalid address, illegal value, etc.)
        error_code = error.exception_code
        error_messages = {
            1: "Illegal function - The function code received is not supported",
            2: "Illegal data address - The data address received is not valid",
            3: "Illegal data value - The value in the request is not valid",
            4: "Server device failure - The server encountered an error processing the request",
        }
        message = error_messages.get(error_code, f"Modbus error code: {error_code}")
        return 400, message  # HTTP_400_BAD_REQUEST
    elif isinstance(error, ModbusException):
        return (
            400,  # HTTP_400_BAD_REQUEST
            f"Modbus error: {str(error)}"
        )
    elif isinstance(error, TimeoutError):
        return (
            504,  # HTTP_504_GATEWAY_TIMEOUT
            f"Request timed out after {MODBUS_TIMEOUT_S}s"
        )
    else:
        return (
            500,  # HTTP_500_INTERNAL_SERVER_ERROR
            f"Unexpected error: {str(error)}"
        )
