"""
Modbus TCP Client Module

Handles all Modbus TCP communication logic, connection management,
and error translation. Separated from the FastAPI application layer.
"""

import os
from typing import Tuple, List, Optional, Union
from contextlib import contextmanager

from dotenv import load_dotenv
from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ConnectionException

from helpers.modbus import translate_modbus_error

# Load environment variables from .env file
load_dotenv()

# Configuration from environment variables
MODBUS_HOST = os.getenv("MODBUS_HOST", "localhost")
MODBUS_PORT = int(os.getenv("MODBUS_PORT", "502"))
MODBUS_DEVICE_ID = int(os.getenv("MODBUS_DEVICE_ID", "1"))
MODBUS_TIMEOUT_S = float(os.getenv("MODBUS_TIMEOUT_S", "5.0"))
MODBUS_RETRIES = int(os.getenv("MODBUS_RETRIES", "3"))

__all__ = ["ModbusClient"]


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


class ModbusClient:
    """Wrapper class for Modbus TCP operations."""
    
    def __init__(self):
        self.host = MODBUS_HOST
        self.port = MODBUS_PORT
        self.default_server_id = MODBUS_DEVICE_ID
        self.timeout = MODBUS_TIMEOUT_S
    
    def read_registers(
        self,
        kind: str,
        address: int,
        count: int,
        server_id: int,
        host: str,
        port: int
    ) -> List[Union[int, bool]]:
        """
        Read Modbus registers or coils/discrete inputs.
        
        Args:
            kind: Type of register to read (holding, input, coils, discretes)
            address: Starting address
            count: Number of registers/bits to read
            server_id: Modbus unit/slave ID
            host: Modbus server hostname or IP address
            port: Modbus server port
            
        Returns:
            List of register values or bits
            
        Raises:
            Exception: Various Modbus exceptions that should be translated
        """
        server_id = server_id
        connection_host = host
        connection_port = port
        
        with modbus_client(host=connection_host, port=connection_port) as client:
            if not client.connect():
                raise ConnectionException("Failed to connect to Modbus server")
            
            if kind == "holding":
                result = client.read_holding_registers(
                    address=address,
                    count=count,
                    device_id=server_id
                )
                if result.isError():
                    raise result
                return result.registers
                
            elif kind == "input":
                result = client.read_input_registers(
                    address=address,
                    count=count,
                    device_id=server_id
                )
                if result.isError():
                    raise result
                return result.registers
                
            elif kind == "coils":
                result = client.read_coils(
                    address=address,
                    count=count,
                    device_id=server_id
                )
                if result.isError():
                    raise result
                return result.bits
                
            elif kind == "discretes":
                result = client.read_discrete_inputs(
                    address=address,
                    count=count,
                    device_id=server_id
                )
                if result.isError():
                    raise result
                return result.bits
                
            else:
                raise ValueError(f"Invalid kind: {kind}")
    
    def modbus_server_health_check(self) -> Tuple[bool, str]:
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
                    device_id=self.default_server_id
                )
                
                if result.isError():
                    return False, f"Read test failed: {result}"
                
                return True, "Connection and read test successful"
                
        except Exception as e:
            _, message = translate_modbus_error(e)
            return False, message

