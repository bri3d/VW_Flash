from lib.constants import FlashInfo, ecu_control_module_identifier
from lib.crypto import simos_xor

from .simosshared import (
    block_identifiers_simos,
    block_checksums_simos,
    block_transfer_sizes_simos,
)

# Simos10 Flash Info

# block sizes for s10
block_lengths_s10 = {
    1: 0x13E00,  # BOOT
    2: 0x19FA00,  # SOFTWARE
    3: 0x3C000,  # CALIBRATION
}

# The base address of each block on simos10

base_addresses_s10 = {
    1: 0x8000C000,  # BOOT
    2: 0x80020000,  # SOFTWARE
    3: 0xA01C0000,  # CALIBRATION
    6: 0xA01C0000,  # CBOOT_TEMP
}

s10_binfile_offsets = {
    1: 0xC000,  # BOOT
    2: 0x20000,  # SOFTWARE
    3: 0x1C0000,  # CALIBRATION
}

s10_sa2_script = bytes.fromhex(
    "6803824A10680284443932244A05872709200481499384251648824A058712082001824A0181494C"
)

block_name_to_int = {
    "CBOOT": 1,
    "ASW1": 2,
    "CAL": 3,
    "CBOOT_TEMP": 6,
}

s10_binfile_size = 2097152

block_names_frf_s10 = {1: "FD_1", 2: "FD_2", 3: "FD_3"}

s10_project_name = "SA"

s10_crypto = simos_xor.SimosXor()

checksum_block_location = {
    0: 0x300,  # SBOOT
    1: 0x300,  # CBOOT
    2: 0x300,  # ASW1
    3: 0x300,  # CAL
    6: 0x340,  # CBOOT_temp
}

software_version_location_s10 = {
    1: [0x41F, 0x424],
    2: [0x627, 0x62F],
    3: [0x23, 0x2B],
}

box_code_location_s10 = {
    1: [0x0, 0x0],
    2: [0x0, 0x0],
    3: [0x60, 0x6B],
}

s10_flash_info = FlashInfo(
    base_addresses_s10,
    block_lengths_s10,
    s10_sa2_script,
    block_names_frf_s10,
    block_identifiers_simos,
    block_checksums_simos,
    ecu_control_module_identifier,
    software_version_location_s10,
    box_code_location_s10,
    block_transfer_sizes_simos,
    s10_binfile_offsets,
    s10_binfile_size,
    s10_project_name,
    s10_crypto,
    block_name_to_int,
    None,
    checksum_block_location,
)
