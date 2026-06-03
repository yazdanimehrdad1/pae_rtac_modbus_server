"""
Fixed protocol and domain constants.

These values are not env-driven and should not be in config.py.
Runtime-configurable values (host, port, TTL, timeouts) belong in config.py.
"""

# Modbus Application Protocol spec: max registers per PDU read request
MODBUS_MAX_REGISTERS_PER_READ = 125

# Maximum number of polling configs allowed per device
CONFIG_INDEX_MIN = 1
CONFIG_INDEX_MAX = 10

# Bitfield register widths
BITS_PER_REGISTER_16_BIT = 16
MAX_BITFIELD_BITS_32_BIT = 32
