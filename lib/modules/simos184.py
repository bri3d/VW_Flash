from lib.constants import FlashInfo, internal_path, ecu_control_module_identifier
from .simos1810 import base_addresses_s1810, block_lengths_s1810
from .simosshared import (
    block_identifiers_simos,
    block_checksums_simos,
    box_code_location_simos,
    software_version_location_simos,
    block_transfer_sizes_simos,
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

s1841_flash_info = FlashInfo(
    base_addresses_s1810,
    block_lengths_s1810,
    sa2_script_s1841,
    s1841_key,
    s1841_iv,
    None,
    block_names_frf_s1841,
    None,
    None,
    None,
    block_identifiers_simos,
    block_checksums_simos,
    ecu_control_module_identifier,
    software_version_location_simos,
    box_code_location_simos,
    block_transfer_sizes_simos,
)
