from lib.constants import ControlModuleIdentifier, FlashInfo

haldex_control_module_identifier = ControlModuleIdentifier(0x779, 0x70F)

block_transfer_sizes_haldex = {1: 0x100, 2: 0x100, 3: 0x100, 4: 0x100}

software_version_location_haldex = {
    1: [0x0, 0x0],
    2: [0x0, 0x4],
    3: [0x3DB7C, 0x3DB80],
    4: [0xA, 0xE],
}

box_code_location_haldex = {1: [0x0, 0x0], 2: [0x4, 0xF], 3: [0x0, 0x0], 4: [0x0, 0x0]}

block_identifiers_haldex = {1: 0x30, 2: 0x02, 3: 0x01, 4: 0x03}

block_lengths_haldex = {
    1: 0x434,  # DRIVER
    2: 0x333E,  # CAL
    3: 0x3DB80,  # ASW
    4: 0xE,  # Version
}

haldex_sa2_script = bytes.fromhex("6805814A05870A221289494C")
block_names_frf_haldex = {1: "FD_0DRIVE", 2: "FD_1DATA", 3: "FD_2DATA", 4: "FD_3DATA"}

haldex_binfile_offsets = {
    1: 0x0,  # DRIVER
    2: 0xB400,  # CAL
    3: 0x10000,  # ASW
    4: 0x4DC01,  # VERSION
}

haldex_binfile_size = 327680

haldex_project_name = "F"

# Conversion dict for block name to number
block_name_to_int = {"DRIVER": 1, "CAL": 2, "ASW": 3, "VERSION": 4}

haldex_flash_info = FlashInfo(
    None,
    block_lengths_haldex,
    haldex_sa2_script,
    block_names_frf_haldex,
    block_identifiers_haldex,
    None,
    haldex_control_module_identifier,
    software_version_location_haldex,
    box_code_location_haldex,
    block_transfer_sizes_haldex,
    haldex_binfile_offsets,
    haldex_binfile_size,
    haldex_project_name,
    None,
    block_name_to_int,
    None,
    None,
)
