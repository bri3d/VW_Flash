from lib.constants import FlashInfo, internal_path, ecu_control_module_identifier
from .simosshared import (
    block_identifiers_simos,
    block_checksums_simos,
    box_code_location_simos,
    software_version_location_simos,
    block_transfer_sizes_simos,
)

# Simos12 Flash Info

# block sizes for S12
block_lengths_s12 = {
    1: 0x1FE00,  # CBOOT
    2: 0xBFC00,  # ASW1
    3: 0xBFC00,  # ASW2
    4: 0xBFC00,  # ASW3
    5: 0x6FC00,  # CAL
    6: 0x1FE00,  # CBOOT_temp
}

# The base address of each block on simos12

base_addresses_s12 = {
    0: 0x80000000,  # SBOOT
    1: 0x80020000,  # CBOOT
    2: 0x800C0000,  # ASW1
    3: 0x80180000,  # ASW2
    4: 0x80240000,  # ASW3
    5: 0xA0040000,  # CAL
    6: 0x80080000,  # CBOOT_temp
}

s12_iv = bytes.fromhex("306e37426b6b536f316d4a6974366d34")
s12_key = bytes.fromhex("314d7536416e3047396a413252356f45")

s12_sa2_script = bytes.fromhex(
    "6803814A10680393290720094A05872212195482499309011953824A058730032009824A0181494C"
)

block_names_frf_s12 = {1: "FD_0", 2: "FD_1", 3: "FD_2", 4: "FD_3", 5: "FD_4"}

s12_flash_info = FlashInfo(
    base_addresses_s12,
    block_lengths_s12,
    s12_sa2_script,
    s12_key,
    s12_iv,
    None,
    block_names_frf_s12,
    "",
    0,
    "",
    block_identifiers_simos,
    block_checksums_simos,
    ecu_control_module_identifier,
    software_version_location_simos,
    box_code_location_simos,
    block_transfer_sizes_simos,
)
