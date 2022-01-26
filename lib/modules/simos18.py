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

# When we're performing WriteWithoutErase, we need to write 8 bytes at a time in "patch areas" to allow the ECC operation to be performed correctly across the patched data.
# But, when we're just "writing" 0s (which we can't actually do), we can go faster and fill an entire 256-byte Assembly Page in the flash controller as ECC will not work anyway.
# Internally, we're basically stuffing the Assembly Page for the flash controller and the method return does not wait for controller readiness, so we will also need to resend data repeatedly.


def s18_block_transfer_sizes_patch(block_number: int, address: int) -> int:
    if block_number != 4:
        print(
            "Only patching H__0001's Block 4 / ASW3 using a provided patch is supported at this time! If you have a patch for another block, please fill in its data areas here."
        )
        exit()
    if address < 0x9600:
        return 0x100
    if address >= 0x9600 and address < 0x9800:
        return 0x8
    if address >= 0x9800 and address < 0x7DD00:
        return 0x100
    if address >= 0x7DD00 and address < 0x7E200:
        return 0x8
    if address >= 0x7E200 and address < 0x7F900:
        return 0x100
    return 0x8


block_names_frf_s18 = {1: "FD_0", 2: "FD_1", 3: "FD_2", 4: "FD_3", 5: "FD_4"}

# Simos18.1 / 18.6 Flash Info

# The base address of each block for S18.1
base_addresses_s18 = {
    0: 0x80000000,  # SBOOT
    1: 0x8001C000,  # CBOOT
    2: 0x80040000,  # ASW1
    3: 0x80140000,  # ASW2
    4: 0x80880000,  # ASW3
    5: 0xA0800000,  # CAL
    6: 0x80840000,  # CBOOT_temp
}

# The size of each block
block_lengths_s18 = {
    1: 0x23E00,  # CBOOT
    2: 0xFFC00,  # ASW1
    3: 0xBFC00,  # ASW2
    4: 0x7FC00,  # ASW3
    5: 0x7FC00,  # CAL
    6: 0x23E00,  # CBOOT_temp
}

s18_key = bytes.fromhex("98D31202E48E3854F2CA561545BA6F2F")
s18_iv = bytes.fromhex("E7861278C508532798BCA4FE451D20D1")

sa2_script_s18 = bytes.fromhex(
    "6802814A10680493080820094A05872212195482499307122011824A058703112010824A0181494C"
)

# These are the offsets used for a "full bin" as produced by many commercial tools.
s18_binfile_offsets = {
    0: 0x0,  # SBOOT
    1: 0x1C000,  # CBOOT
    2: 0x40000,  # ASW1
    3: 0x140000,  # ASW2
    4: 0x280000,  # ASW3
    5: 0x200000,  # CAL
}

s18_binfile_size = 4194304

s18_project_name = "SC8"

s18_crypto = aes.AES(s18_key, s18_iv)

s18_patch_info = PatchInfo(
    patch_box_code="8V0906259H__0001",
    patch_block_index=4,
    patch_filename=internal_path("docs", "patch.bin"),
    block_transfer_sizes_patch=s18_block_transfer_sizes_patch,
)

s18_flash_info = FlashInfo(
    base_addresses_s18,
    block_lengths_s18,
    sa2_script_s18,
    block_names_frf_s18,
    block_identifiers_simos,
    block_checksums_simos,
    ecu_control_module_identifier,
    software_version_location_simos,
    box_code_location_simos,
    block_transfer_sizes_simos,
    s18_binfile_offsets,
    s18_binfile_size,
    s18_project_name,
    s18_crypto,
    block_name_to_int,
    s18_patch_info,
    checksum_block_location,
)
