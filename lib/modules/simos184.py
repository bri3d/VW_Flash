from lib.constants import FlashInfo, internal_path, ecu_control_module_identifier
from lib.crypto import aes
from .simos1810 import base_addresses_s1810, block_lengths_s1810
from .simosshared import (
    block_identifiers_simos,
    block_checksums_simos,
    box_code_location_simos,
    software_version_location_simos,
    block_transfer_sizes_simos,
    block_name_to_int,
    checksum_block_location,
)


# Simos 18.41 Flash Info

block_names_frf_s1841 = {
    1: "FD_01FLASHDATA",
    2: "FD_02FLASHDATA",
    3: "FD_03FLASHDATA",
    4: "FD_04FLASHDATA",
    5: "FD_05FLASHDATA",
}

s1841_key = bytes.fromhex("6E3FE03619F138798CB4ECDCC762005F")
s1841_iv = bytes.fromhex("000102030405060708090A0B0C0D0E0F")

sa2_script_s1841 = bytes.fromhex(
    "6802814A10680493C1387FA34A05872212195482499318102012824A058728051977824A0181494C"
)

s184_binfile_offsets = {
    0: 0x0,  # SBOOT
    1: 0x200000,  # CBOOT
    2: 0x20000,  # ASW1
    3: 0x100000,  # ASW2
    4: 0x2C0000,  # ASW3
    5: 0x220000,  # CAL
}

s184_binfile_size = 4194304

s184_project_name = "SCB"

s184_crypto = aes.AES(s1841_key, s1841_iv)

s1841_flash_info = FlashInfo(
    base_addresses_s1810,
    block_lengths_s1810,
    sa2_script_s1841,
    block_names_frf_s1841,
    block_identifiers_simos,
    block_checksums_simos,
    ecu_control_module_identifier,
    software_version_location_simos,
    box_code_location_simos,
    block_transfer_sizes_simos,
    s184_binfile_offsets,
    s184_binfile_size,
    s184_project_name,
    s184_crypto,
    block_name_to_int,
    None,
    checksum_block_location,
)
