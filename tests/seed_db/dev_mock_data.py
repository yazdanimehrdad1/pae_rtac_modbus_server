"""
Mock data for local development and DB seeding.

Organized as:
  SITES        — two site records
  DEVICES      — two devices per site (keyed to site by site_name)
  DEVICE_CONFIGS — one or two register-block configs per device
                   each config carries a `points` list that becomes
                   DevicePoint rows
"""

# ---------------------------------------------------------------------------
# Sites
# ---------------------------------------------------------------------------

SITES = [
    {
        "client_id": "alpha-corp",
        "name": "Alpha Solar Farm",
        "location": {"street": "100 Solar Way", "city": "San Diego", "state": "CA", "zip_code": 92101},
        "operator": "PAE",
        "capacity": "5MW",
        "description": "Alpha dev site — SEL relays + BESS",
        "coordinates": {"lat": 32.7157, "lng": -117.1611},
        "device_count": 0,
    },
    # {
    #     "client_id": "beta-energy",
    #     "name": "Beta Substation",
    #     "location": {"street": "200 Power Blvd", "city": "Los Angeles", "state": "CA", "zip_code": 90001},
    #     "operator": "PAE",
    #     "capacity": "10MW",
    #     "description": "Beta dev site — feeder relay + power meter",
    #     "coordinates": {"lat": 34.0522, "lng": -118.2437},
    #     "device_count": 0,
    # },
]

# ---------------------------------------------------------------------------
# Devices  (site_name is resolved to site.id by the seed script)
# ---------------------------------------------------------------------------

DEVICES = [
    # --- Alpha Solar Farm ---
    {
        "site_name": "Alpha Solar Farm",
        "name": "alpha-sel-751-main",
        "host": "192.168.10.1",
        "port": 502,
        "timeout": 5.0,
        "server_address": 1,
        "type": "relay",
        "vendor": "SEL",
        "model": "SEL-751",
        "protocol": "Modbus",
        "description": "Main feeder protection relay",
        "poll_enabled": True,
        "read_from_aggregator": True,
    },
    # {
    #     "site_name": "Alpha Solar Farm",
    #     "name": "alpha-eos-bess-1",
    #     "host": "192.168.10.5",
    #     "port": 502,
    #     "timeout": 5.0,
    #     "server_address": 1,
    #     "type": "bess",
    #     "vendor": "EOS",
    #     "model": "EOS-BESS-1000",
    #     "protocol": "Modbus",
    #     "description": "Battery Energy Storage System unit 1",
    #     "poll_enabled": True,
    #     "read_from_aggregator": True,
    # },
    # # --- Beta Substation ---
    # {
    #     "site_name": "Alpha Solar Farm",
    #     "name": "beta-sel-751-feeder",
    #     "host": "192.168.20.1",
    #     "port": 502,
    #     "timeout": 5.0,
    #     "server_address": 1,
    #     "type": "relay",
    #     "vendor": "SEL",
    #     "model": "SEL-751",
    #     "protocol": "Modbus",
    #     "description": "Feeder A protection relay",
    #     "poll_enabled": True,
    #     "read_from_aggregator": True,
    # },
    # {
    #     "site_name": "Beta Substation",
    #     "name": "beta-power-meter",
    #     "host": "192.168.20.10",
    #     "port": 502,
    #     "timeout": 5.0,
    #     "server_address": 1,
    #     "type": "meter",
    #     "vendor": "Schneider",
    #     "model": "ION7650",
    #     "protocol": "Modbus",
    #     "description": "Main revenue-grade power meter",
    #     "poll_enabled": True,
    #     "read_from_aggregator": True,
    # },
]

# ---------------------------------------------------------------------------
# Configs  (keyed by device name)
#
# Each entry in the list is one config block:
#   poll_kind   — "holding" | "input" | "coils" | "discretes"
#   created_by  — creator label
#   is_active   — bool
#   points      — list of point defs (→ DevicePoint rows)
#
# poll_start_index / poll_count are derived from the points list by the
# seed script so you don't have to keep them in sync manually.
# ---------------------------------------------------------------------------

DEVICE_CONFIGS: dict[str, list[dict]] = {

    # -----------------------------------------------------------------------
    # alpha-sel-751-main
    #   Two blocks: standard metering registers + status word block
    # -----------------------------------------------------------------------
    "alpha-sel-751-main": [
        {
            "poll_kind": "holding",
            "created_by": "seed-script",
            "is_active": True,
            "points": [
                {"address": 1400, "name": "M_FREQ",  "data_type": "uint16", "size": 1, "scale_factor": 0.01,  "unit": "Hz"},
                {"address": 1401, "name": "M_FREQS", "data_type": "uint16", "size": 1, "scale_factor": 0.01,  "unit": "Hz"},
                {"address": 1402, "name": "M_IA",    "data_type": "uint16", "size": 1, "scale_factor": 0.1,   "unit": "A"},
                {"address": 1403, "name": "M_IB",    "data_type": "uint16", "size": 1, "scale_factor": 0.1,   "unit": "A"},
                {"address": 1404, "name": "M_IC",    "data_type": "uint16", "size": 1, "scale_factor": 0.1,   "unit": "A"},
                {"address": 1405, "name": "M_IG",    "data_type": "uint16", "size": 1, "scale_factor": 0.1,   "unit": "A"},
                {"address": 1406, "name": "M_P",     "data_type": "uint16", "size": 1, "scale_factor": 0.001, "unit": "MW"},
                {"address": 1407, "name": "M_PF",    "data_type": "uint16", "size": 1, "scale_factor": 0.001, "unit": None},
                {"address": 1408, "name": "M_Q",     "data_type": "uint16", "size": 1, "scale_factor": 0.001, "unit": "MVAR"},
                {"address": 1409, "name": "M_S",     "data_type": "uint16", "size": 1, "scale_factor": 0.001, "unit": "MVA"},
                {"address": 1410, "name": "M_VAB",   "data_type": "uint16", "size": 1, "scale_factor": 0.1,   "unit": "kV"},
                {"address": 1411, "name": "M_VBC",   "data_type": "uint16", "size": 1, "scale_factor": 0.1,   "unit": "kV"},
                {"address": 1412, "name": "M_VCA",   "data_type": "uint16", "size": 1, "scale_factor": 0.1,   "unit": "kV"},
                {"address": 1413, "name": "M_VDC",   "data_type": "uint16", "size": 1, "scale_factor": 0.1,   "unit": "kV"},
                {"address": 1414, "name": "M_VS",    "data_type": "uint16", "size": 1, "scale_factor": 0.1,   "unit": "kV"},
            ],
        },
        {
            "poll_kind": "holding",
            "created_by": "seed-script",
            "is_active": True,
            "points": [
                {"address": 1415, "name": "M_STATUS", "data_type": "bitfield", "size": 1, "scale_factor": 1.0, "unit": None, "bitfield_detail": {"0": "Closed", "1": "Open", "2": "Fault", "3": "Alarm"}},
                {"address": 1416, "name": "M_FAULT", "data_type": "bitfield", "size": 1, "scale_factor": 1.0, "unit": None, "bitfield_detail": {"0": "No Fault", "1": "Fault"}}
            ],
        },
    ],

    # -----------------------------------------------------------------------
    # alpha-eos-bess-1
    #   Single block: SOC/SOH/power/charge-status + one float32 register
    # -----------------------------------------------------------------------
    # "alpha-eos-bess-1": [
    #     {
    #         "poll_kind": "holding",
    #         "created_by": "seed-script",
    #         "is_active": True,
    #         "points": [
    #             {"address": 1500, "name": "BESS_SOC",           "data_type": "uint16", "size": 1, "scale_factor": 0.1,  "unit": "%"},
    #             {"address": 1501, "name": "BESS_SOH",           "data_type": "uint16", "size": 1, "scale_factor": 0.1,  "unit": "%"},
    #             {"address": 1502, "name": "BESS_KW",            "data_type": "int16",  "size": 1, "scale_factor": 0.1,  "unit": "kW"},
    #             {"address": 1503, "name": "BESS_KVAR",          "data_type": "int16",  "size": 1, "scale_factor": 0.1,  "unit": "kVAR"},
    #             {"address": 1504, "name": "BESS_TEMP",          "data_type": "int16",  "size": 1, "scale_factor": 0.1,  "unit": "°C"},
    #             {
    #                 "address": 1505,
    #                 "name": "BESS_CHARGE_STATUS",
    #                 "data_type": "uint16",
    #                 "size": 1,
    #                 "scale_factor": 1.0,
    #                 "unit": None,
    #                 "enum_detail": {"0": "Idle", "1": "Charging", "2": "Discharging", "3": "Fault"},
    #             },
    #             # float32 occupies two consecutive registers (1506, 1507)
    #             {"address": 1506, "name": "BESS_VOLTAGE", "data_type": "float32", "size": 2, "scale_factor": 1.0, "unit": "V"},
    #         ],
    #     },
    # ],

    # -----------------------------------------------------------------------
    # beta-sel-751-feeder
    #   Single metering block (subset of SEL-751 registers)
    # -----------------------------------------------------------------------
    # "beta-sel-751-feeder": [
    #     {
    #         "poll_kind": "holding",
    #         "created_by": "seed-script",
    #         "is_active": True,
    #         "points": [
    #             {"address": 1400, "name": "M_FREQ", "data_type": "uint16", "size": 1, "scale_factor": 0.01,  "unit": "Hz"},
    #             {"address": 1401, "name": "M_IA",   "data_type": "uint16", "size": 1, "scale_factor": 0.1,   "unit": "A"},
    #             {"address": 1402, "name": "M_IB",   "data_type": "uint16", "size": 1, "scale_factor": 0.1,   "unit": "A"},
    #             {"address": 1403, "name": "M_IC",   "data_type": "uint16", "size": 1, "scale_factor": 0.1,   "unit": "A"},
    #             {"address": 1404, "name": "M_P",    "data_type": "uint16", "size": 1, "scale_factor": 0.001, "unit": "MW"},
    #             {"address": 1405, "name": "M_Q",    "data_type": "uint16", "size": 1, "scale_factor": 0.001, "unit": "MVAR"},
    #             {"address": 1406, "name": "M_PF",   "data_type": "uint16", "size": 1, "scale_factor": 0.001, "unit": None},
    #             {"address": 1407, "name": "M_VAB",  "data_type": "uint16", "size": 1, "scale_factor": 0.1,   "unit": "kV"},
    #             {"address": 1408, "name": "M_VBC",  "data_type": "uint16", "size": 1, "scale_factor": 0.1,   "unit": "kV"},
    #             {"address": 1409, "name": "M_VCA",  "data_type": "uint16", "size": 1, "scale_factor": 0.1,   "unit": "kV"},
    #         ],
    #     },
    # ],

    # -----------------------------------------------------------------------
    # beta-power-meter
    #   Input registers, all float32 (each occupies two registers)
    # -----------------------------------------------------------------------
#     "beta-power-meter": [
#         {
#             "poll_kind": "input",
#             "created_by": "seed-script",
#             "is_active": True,
#             "points": [
#                 {"address": 100, "name": "FREQ",  "data_type": "float32", "size": 2, "scale_factor": 1.0, "unit": "Hz"},
#                 {"address": 102, "name": "IA",    "data_type": "float32", "size": 2, "scale_factor": 1.0, "unit": "A"},
#                 {"address": 104, "name": "IB",    "data_type": "float32", "size": 2, "scale_factor": 1.0, "unit": "A"},
#                 {"address": 106, "name": "IC",    "data_type": "float32", "size": 2, "scale_factor": 1.0, "unit": "A"},
#                 {"address": 108, "name": "P_KW",  "data_type": "float32", "size": 2, "scale_factor": 1.0, "unit": "kW"},
#                 {"address": 110, "name": "Q_KVAR","data_type": "float32", "size": 2, "scale_factor": 1.0, "unit": "kVAR"},
#                 {"address": 112, "name": "PF",    "data_type": "float32", "size": 2, "scale_factor": 1.0, "unit": None},
#                 {"address": 114, "name": "VAB",   "data_type": "float32", "size": 2, "scale_factor": 1.0, "unit": "V"},
#             ],
#         },
#     ],
# 
}