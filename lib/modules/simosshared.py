# In Simos, we can send the maximum allowable size worth of compressed data in an ISO-TP request when we are using the "normal" TransferData system.

block_transfer_sizes_simos = {1: 0xFFD, 2: 0xFFD, 3: 0xFFD, 4: 0xFFD, 5: 0xFFD}

software_version_location_simos = {
    1: [0x437, 0x43F],
    2: [0x627, 0x62F],
    3: [0x203, 0x20B],
    4: [0x203, 0x20B],
    5: [0x23, 0x2B],
    7: [0, 0],
    9: [0, 0],
}

box_code_location_simos = {
    1: [0x0, 0x0],
    2: [0x0, 0x0],
    3: [0x0, 0x0],
    4: [0x0, 0x0],
    5: [0x60, 0x6B],
    7: [0, 0],
    9: [0x0, 0x0],
}

# Unused box code data used for fingerprinting
vw_flash_fingerprint_simos = [0x7A, 0x7E]

block_identifiers_simos = {1: 1, 2: 2, 3: 3, 4: 4, 5: 5}

# Simos does not use block checksums sent over UDS but rather checksums internally. See checksum.py for the internal checksum implementation.
block_checksums_simos = {
    1: bytes.fromhex("00000000"),
    2: bytes.fromhex("00000000"),
    3: bytes.fromhex("00000000"),
    4: bytes.fromhex("00000000"),
    5: bytes.fromhex("00000000"),
    7: bytes.fromhex("00000000"),
    9: bytes.fromhex("00000000"),
}

# The location of each checksum in the bin
checksum_block_location = {
    0: 0x300,  # SBOOT
    1: 0x300,  # CBOOT
    2: 0x300,  # ASW1
    3: 0x0,  # ASW2
    4: 0x0,  # ASW3
    5: 0x300,  # CAL
    6: 0x340,  # CBOOT_temp
}

# The location of the addresses for ECM3 Level 2 CAL monitoring
# 'Early' cars seem to have a different version of the ECM3 module which looks in a different place for the ECM2 Calibration offsets to checksum
# 'Early' cars also calculate the offsets in a different way.

ecm3_cal_monitor_addresses_early = 0x540  # Offset into ASW1
ecm3_cal_monitor_addresses = 0x520  # Offset into ASW1
ecm3_cal_monitor_offset_uncached = 0
ecm3_cal_monitor_offset_cached = 0x20000000
ecm3_cal_monitor_checksum = 0x400  # Offset into CAL

# Conversion dict for block name to number
block_name_to_int = {
    "CBOOT": 1,
    "ASW1": 2,
    "ASW2": 3,
    "ASW3": 4,
    "CAL": 5,
    "CBOOT_TEMP": 6,
    "PATCH_ASW1": 7,
    "PATCH_ASW2": 8,
    "PATCH_ASW3": 9,
}
