from lib.constants import (
    FlashInfo,
    PatchInfo,
    internal_path,
    ecu_control_module_identifier,
)
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


def s1810_block_transfer_sizes_patch(block_number: int, address: int) -> int:
    if block_number != 2:
        print(
            "Only patching Q__0005's Block 2 / ASW1 using a provided patch is supported at this time! If you have a patch for another block, please fill in its data areas here."
        )
        exit()
    if address < 0x5CB00:
        return 0x100
    if address >= 0x5CB00 and address < 0x5CC00:
        return 0x8
    if address >= 0x5CC00 and address < 0xB3000:
        return 0x100
    if address >= 0xB3000 and address < 0xB3100:
        return 0x8
    if address >= 0xB3100 and address < 0xDFB00:
        return 0x100
    return 0x8


# Simos 18.10 Flash Info

block_names_frf_s1810 = {
    1: "FD_01DATA",
    2: "FD_02DATA",
    3: "FD_03DATA",
    4: "FD_04DATA",
    5: "FD_05DATA",
}

base_addresses_s1810 = {
    0: 0x80000000,  # SBOOT
    1: 0x80800000,  # CBOOT
    2: 0x80020000,  # ASW1
    3: 0x80100000,  # ASW2
    4: 0x808C0000,  # ASW3
    5: 0xA0820000,  # CAL
    6: 0x80880000,  # CBOOT_temp
}

# The size of each block
block_lengths_s1810 = {
    1: 0x1FE00,  # CBOOT
    2: 0xDFC00,  # ASW1
    3: 0xFFC00,  # ASW2
    4: 0x13FC00,  # ASW3
    5: 0x9FC00,  # CAL
    6: 0x1FE00,  # CBOOT_temp
}

s1810_key = bytes.fromhex("AE540502E48E3854DBCA1A1545BA6F33")
s1810_iv = bytes.fromhex("62F313FA5C08532798BCA452471D20D5")

sa2_script_s1810 = bytes.fromhex(
    "6803814A10680293050520154A058722121954824993F423BF7D824A05875A63FC5E824A0181494C"
)

s1810_binfile_offsets = {
    0: 0x0,  # SBOOT
    1: 0x200000,  # CBOOT
    2: 0x20000,  # ASW1
    3: 0x100000,  # ASW2
    4: 0x2C0000,  # ASW3
    5: 0x220000,  # CAL
}

s1810_binfile_size = 4194304

s1810_project_name = "SCG"

s1810_crypto = aes.AES(s1810_key, s1810_iv)

s1810_patch_info = PatchInfo(
    patch_box_code="5G0906259Q__0005",
    patch_block_index=2,
    patch_filename=internal_path("docs", "patch_1810.bin"),
    block_transfer_sizes_patch=s1810_block_transfer_sizes_patch,
)

s1810_flash_info = FlashInfo(
    base_addresses_s1810,
    block_lengths_s1810,
    sa2_script_s1810,
    block_names_frf_s1810,
    block_identifiers_simos,
    block_checksums_simos,
    ecu_control_module_identifier,
    software_version_location_simos,
    box_code_location_simos,
    block_transfer_sizes_simos,
    s1810_binfile_offsets,
    s1810_binfile_size,
    s1810_project_name,
    s1810_crypto,
    block_name_to_int,
    s1810_patch_info,
    checksum_block_location,
)
