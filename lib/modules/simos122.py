from lib.constants import FlashInfo, ecu_control_module_identifier
from lib.crypto import aes
from .simosshared import (
    block_identifiers_simos,
    block_checksums_simos,
    box_code_location_simos,
    software_version_location_simos,
    block_transfer_sizes_simos,
    block_name_to_int,
    checksum_block_location,
)

# Simos12.2 Flash Info

# block sizes for S12.2
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

s12_binfile_offsets = {
    0: 0x0,  # SBOOT
    1: 0x20000,  # CBOOT
    2: 0xC0000,  # ASW1
    3: 0x180000,  # ASW2
    4: 0x240000,  # ASW3
    5: 0x40000,  # CAL
}

s12_iv = bytes.fromhex("70493465726345296470557333235379")
s12_key = bytes.fromhex("41326D3F50613D306C4C36616E346721")

s12_sa2_script = bytes.fromhex(
    "6803814A10680393290720094A05872212195482499309011953824A058730032009824A0181494C"
)

s12_binfile_size = 4194304

block_names_frf_s12 = {1: "FD_0", 2: "FD_1", 3: "FD_2", 4: "FD_3", 5: "FD_4"}

s12_project_name = "SC2"

s12_crypto = aes.AES(s12_key, s12_iv)

s122_flash_info = FlashInfo(
    base_addresses_s12,
    block_lengths_s12,
    s12_sa2_script,
    block_names_frf_s12,
    block_identifiers_simos,
    block_checksums_simos,
    ecu_control_module_identifier,
    software_version_location_simos,
    box_code_location_simos,
    block_transfer_sizes_simos,
    s12_binfile_offsets,
    s12_binfile_size,
    s12_project_name,
    s12_crypto,
    block_name_to_int,
    None,
    checksum_block_location,
)
