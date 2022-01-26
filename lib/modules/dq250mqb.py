from lib.constants import ControlModuleIdentifier, FlashInfo
from lib.crypto import dsg

dsg_control_module_identifier = ControlModuleIdentifier(0x7E9, 0x7E1)

block_transfer_sizes_dsg = {2: 0x4B0, 3: 0x800, 4: 0x800}

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
    2: bytes.fromhex("F974176E"),
    3: bytes.fromhex("FFFFFFFF"),
    4: bytes.fromhex("FFFFFFFF"),
}

block_lengths_dsg = {
    2: 0x80E,  # DRIVER
    3: 0x130000,  # ASW
    4: 0x20000,  # CAL
}

dsg_sa2_script = bytes.fromhex(
    "68028149680593A55A55AA4A0587810595268249845AA5AA558703F780384C"
)
block_names_frf_dsg = {2: "FD_2", 3: "FD_3", 4: "FD_4"}

dsg_binfile_offsets = {
    2: 0x0,  # DRIVER
    3: 0x50000,  # ASW
    4: 0x30000,  # CAL
}

dsg_binfile_size = 1572864

dsg_project_name = "F"

dsg_crypto = dsg.DSG()

# Conversion dict for block name to number
block_name_to_int = {"DRIVER": 2, "ASW": 3, "CAL": 4}

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
