from lib.constants import ControlModuleIdentifier, FlashInfo
from lib.crypto import aes

dsg_control_module_identifier = ControlModuleIdentifier(0x7E9, 0x7E1)

block_transfer_sizes_dsg = {2: 0x800, 3: 0x800, 4: 0x800}

software_version_location_dsg = {
    2: [0x0, 0x0],
    3: [0x3FFE0, 0x3FFE4],
    4: [0x1FFE0, 0x1FFE4],
}

box_code_location_dsg = {2: [0x0, 0x0], 3: [0x0, 0x0], 4: [0x1FFC0, 0x1FFD3]}

block_identifiers_dsg = {2: 0x30, 3: 0x50, 4: 0x51}

# DSG uses external UDS checksum only for the Driver block, the other blocks are internally checksummed.
# See dsg_checksum.py for an implementation.
block_checksums_dsg = {
    1: bytes.fromhex("F974176E"),
    2: bytes.fromhex("FFFFFFFF"),
    3: bytes.fromhex("FFFFFFFF"),
}

block_lengths_dsg = {
    1: 0x1FE00,  # BOOT
    2: 0x10FE00,  # ASW
    3: 0x3FE00,  # CAL
}

dsg_sa2_script = bytes.fromhex(
    "6806814A05876B5F7DD5494C"
)
block_names_frf_dsg = {1: "FD_01DATA", 2: "FD_02DATA", 3: "FD_03DATA"}

dsg_binfile_offsets = {
    1: 0x0,  # DRIVER
    2: 0x1FE00,  # ASW
    3: 0x300000,  # CAL
}

dsg_binfile_size = 1572864

dsg_project_name = "F"

dsg_crypto = aes.AES(bytes.fromhex("00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F"), bytes.fromhex("10 11 12 13 14 15 16 17 18 19 1A 1B 1C 1D 1E 1F"))

# Conversion dict for block name to number
block_name_to_int = {"BOOT": 1, "ASW": 2, "CAL": 3}

dsg_flash_info = FlashInfo(
    None,
    block_lengths_dsg,
    dsg_sa2_script,
    block_names_frf_dsg,
    block_identifiers_dsg,
    block_checksums_dsg,
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
