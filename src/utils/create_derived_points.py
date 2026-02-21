# Description: This file should contain the higher level function that calls on other 
# helper functions (if needed) to create derived points which is sent in the routers/readings_registers.py
# and routers/readings_device.py.
# This is how it should derive the logical points that should be returned in the above routes:

# The input to the function is a joint of DevicePoint and DevicePointsReading.
# The output should be a list of DevicePointResponse.
# The function should be called create_derived_points(device_point: DevicePoint, device_points_reading: DevicePointsReading) -> List[MERGED_POINT_METADATE_TO_READING]:
# where MERGED_POINT_METADATE_TO_READING ( to be defined as a new type)is a dictionary that contains the dollowing
#             {
#                 'device_point_id': row.device_point_id,
#                 'register_address': row.address,
#                 'name': row.name,
#                 'data_type': row.data_type,
#                 'unit': row.unit,
#                 'scale_factor': row.scale_factor,
#                 'is_derived': row.is_derived,
#                 'timestamp': row.timestamp,
#                 'derived_value': row.derived_value,
#                 calculated_value: calculated_value the calculated based on the following conditions
#             }

# Conditions to be used to calculate the calculated_value:
# contition-1: If the point is a bitfield, then the derived point should be the bitfield value.
# there should be a helper function called get_bitfield_value that takes a value and return what bits of a 16 or 32 bit is 0 or 1 ( maybe an array?)
# bitefield_value = get_bitfield_value(derived_value)
# the value = {
#     "bitfield": bitefield_value,
#     "bit-00": bitfield_detail,
#     "bit-01": bitfield_detail,
#     "bit-02": bitfield_detail,
#     "bit-03": bitfield_detail,
#     "bit-04": bitfield_detail,
#     "bit-05": bitfield_detail,
#     "bit-06": bitfield_detail,
#     "bit-07": bitfield_detail,
#     "bit-08": bitfield_detail,
#     "bit-09": bitfield_detail,
#     "bit-10": bitfield_detail,
#     "bit-11": bitfield_detail,
#     "bit-12": bitfield_detail,
#     "bit-13": bitfield_detail,
#     "bit-14": bitfield_detail,
#     "bit-15": bitfield_detail,
#     "bit-16": bitfield_detail,
#     "bit-17": bitfield_detail,
#     "bit-18": bitfield_detail,
#     "bit-19": bitfield_detail,
#     "bit-20": bitfield_detail,
#     "bit-21": bitfield_detail,
#     "bit-22": bitfield_detail,
#     "bit-23": bitfield_detail,
#     "bit-24": bitfield_detail,
#     "bit-25": bitfield_detail,
#     "bit-26": bitfield_detail,
#     "bit-27": bitfield_detail,
#     "bit-28": bitfield_detail,
#     "bit-29": bitfield_detail,
#     "bit-30": bitfield_detail,
#     "bit-31": bitfield_detail,
#     "bit-32": bitfield_detail
# }
# contition-2: If the point is an enum, then the derived point should be the enum value.
# the value = {
#     "enum": enum_value,
#     "enum-00": enum_detail,
#     "enum-01": enum_detail,
#     "enum-02": enum_detail,
#     "enum-03": enum_detail,
#     "enum-04": enum_detail,
#     "enum-05": enum_detail,
#     "enum-06": enum_detail,
#     "enum-07": enum_detail,
# }
# contition-3: If the point is a scaled value, then the derived point should be: 
# the value = derived_value * scale_factor.
# the value = {
#     "scaled": derived_value * scale_factor,
#     "scale_factor": scale_factor,
# }
