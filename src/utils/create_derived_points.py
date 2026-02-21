# Description: This file should contain the higher level function that calls on other 
# helper functions (if needed) to create derived points which is sent in the routers/readings_registers.py
# and routers/readings_device.py.
# This is how it should derive the logical points that should be returned in the above routes:

# contition-1: If the point is a bitfield, then the derived point should be the bitfield value.

# contition-2: If the point is an enum, then the derived point should be the enum value.

# contition-3: If the point is a scaled value, then the derived point should be the scaled value.
