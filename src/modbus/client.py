"""
Modbus TCP Client Module

Handles all Modbus TCP communication logic, connection management,
and error translation. Separated from the FastAPI application layer.
"""

import os
from typing import Literal, Tuple, List, Optional, Union
from contextlib import contextmanager

from dotenv import load_dotenv
from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException, ConnectionException
from pymodbus.pdu import ExceptionResponse

# Load environment variables from .env file
load_dotenv()

# Configuration from environment variables
MODBUS_HOST = os.getenv("MODBUS_HOST", "localhost")
MODBUS_PORT = int(os.getenv("MODBUS_PORT", "502"))
MODBUS_DEVICE_ID = int(os.getenv("MODBUS_DEVICE_ID", "1"))
MODBUS_TIMEOUT_S = float(os.getenv("MODBUS_TIMEOUT_S", "5.0"))
MODBUS_RETRIES = int(os.getenv("MODBUS_RETRIES", "3"))

__all__ = ["ModbusClient", "translate_modbus_error"]


@contextmanager
def modbus_client(host: Optional[str] = None, port: Optional[int] = None):
    """
    Context manager for Modbus TCP client connections.
    Ensures proper cleanup of sockets after use.
    
    Args:
        host: Modbus server hostname or IP address (defaults to MODBUS_HOST env var)
        port: Modbus server port (defaults to MODBUS_PORT env var)
    
    TODO: Replace with persistent pooled client for better performance
    in high-throughput scenarios. Consider using connection pooling
    from pymodbus or a custom pool manager.
    
    Yields:
        ModbusTcpClient: Configured Modbus TCP client instance
    """
    client = ModbusTcpClient(
        host=host or MODBUS_HOST,
        port=port or MODBUS_PORT,
        timeout=MODBUS_TIMEOUT_S,
        retries=MODBUS_RETRIES
    )
    try:
        yield client
    finally:
        client.close()


def translate_modbus_error(error: Exception, host: Optional[str] = None, port: Optional[int] = None) -> Tuple[int, str]:
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
        error_host = host or MODBUS_HOST
        error_port = port or MODBUS_PORT
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


class ModbusClient:
    """Wrapper class for Modbus TCP operations."""
    
    def __init__(self):
        self.host = MODBUS_HOST
        self.port = MODBUS_PORT
        self.default_device_id = MODBUS_DEVICE_ID
        self.timeout = MODBUS_TIMEOUT_S
    
    def read_registers(
        self,
        kind: Literal["holding", "input", "coils", "discretes"],
        address: int,
        count: int,
        device_id: Optional[int] = None,
        host: Optional[str] = None,
        port: Optional[int] = None
    ) -> List[Union[int, bool]]:
        """
        Read Modbus registers or coils/discrete inputs.
        
        Args:
            kind: Type of register to read (holding, input, coils, discretes)
            address: Starting address
            count: Number of registers/bits to read
            device_id: Modbus unit/slave ID (uses default if None)
            host: Modbus server hostname or IP address (uses default if None)
            port: Modbus server port (uses default if None)
            
        Returns:
            List of register values or bits
            
        Raises:
            Exception: Various Modbus exceptions that should be translated
        """
        device_id = device_id or self.default_device_id
        # Use provided host/port or fall back to instance defaults
        connection_host = host or self.host
        connection_port = port or self.port
        
        with modbus_client(host=connection_host, port=connection_port) as client:
            if not client.connect():
                raise ConnectionException("Failed to connect to Modbus server")
            
            if kind == "holding":
                result = client.read_holding_registers(
                    address=address,
                    count=count,
                    device_id=device_id
                )
                if result.isError():
                    raise result
                return result.registers
                
            elif kind == "input":
                result = client.read_input_registers(
                    address=address,
                    count=count,
                    device_id=device_id
                )
                if result.isError():
                    raise result
                return result.registers
                
            elif kind == "coils":
                result = client.read_coils(
                    address=address,
                    count=count,
                    device_id=device_id
                )
                if result.isError():
                    raise result
                return result.bits
                
            elif kind == "discretes":
                result = client.read_discrete_inputs(
                    address=address,
                    count=count,
                    device_id=device_id
                )
                if result.isError():
                    raise result
                return result.bits
                
            else:
                raise ValueError(f"Invalid kind: {kind}")
    
    def health_check(self) -> Tuple[bool, str]:
        """
        Perform a health check by connecting and reading a single holding register.
        
        Returns:
            Tuple of (success: bool, detail: str)
        """
        try:
            with modbus_client() as client:
                # Test connection
                if not client.connect():
                    return False, "Failed to establish connection"
                
                # Perform a small, safe read test (holding register at address 0, count 1)
                # This is a minimal read that should work on most Modbus devices
                # TODO: Consider making this configurable or device-specific
                result = client.read_holding_registers(
                    address=0,
                    count=1,
                    device_id=self.default_device_id
                )
                
                if result.isError():
                    return False, f"Read test failed: {result}"
                
                return True, "Connection and read test successful"
                
        except Exception as e:
            _, message = translate_modbus_error(e)
            return False, message

