from lib.constants import ControlModuleIdentifier, FlashInfo
from lib.crypto import aes

dsg_control_module_identifier = ControlModuleIdentifier(0x7E9, 0x7E1)

block_transfer_sizes_dsg = {1: 0xF0, 2: 0xF0, 3: 0xF0}

software_version_location_dsg = {
    1: [0x0, 0x0],
    2: [0x0, 0x0],
    3: [0x0, 0x0],
}

block_base_address_dsg = {
    1: 0x010200,
    2: 0x030200,
    3: 0x140200,
}

box_code_location_dsg = {1: [0x0, 0x0], 2: [0x0, 0x0], 3: [0x0, 0x0]}

block_identifiers_dsg = {1: 1, 2: 2, 3: 3}

block_lengths_dsg = {
    1: 0x1FE00,  # BOOT
    2: 0x10FE00,  # ASW
    3: 0x3FE00,  # CAL
}

dsg_sa2_script = bytes.fromhex("6806814A05876B5F7DD5494C")
block_names_frf_dsg = {1: "FD_01DATA", 2: "FD_02DATA", 3: "FD_03DATA"}

dsg_binfile_offsets = {
    1: 0x010200,  # BOOT
    2: 0x030200,  # ASW
    3: 0x140200,  # CAL
}

dsg_binfile_size = 0x180000

dsg_project_name = "F"

dsg_crypto = aes.AES(
    bytes.fromhex("00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F"),
    bytes.fromhex("10 11 12 13 14 15 16 17 18 19 1A 1B 1C 1D 1E 1F"),
)

# Conversion dict for block name to number
block_name_to_int = {"BOOT": 1, "ASW": 2, "CAL": 3}

dsg_flash_info = FlashInfo(
    None,
    block_lengths_dsg,
    dsg_sa2_script,
    block_names_frf_dsg,
    block_identifiers_dsg,
    None,
    dsg_control_module_identifier,
    software_version_location_dsg,
    box_code_location_dsg,
    block_transfer_sizes_dsg,
    dsg_binfile_offsets,
    dsg_binfile_size,
    dsg_project_name,
    dsg_crypto,
    block_name_to_int,
    None,
    None,
)
