from lib.constants import (
    FlashInfo,
    PatchInfo,
    internal_path,
    ecu_control_module_identifier,
)
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


def s184_block_transfer_sizes_patch(block_number: int, address: int) -> int:
    if block_number != 2:
        print(
            "Only patching F__0008's Block 2 / ASW1 using a provided patch is supported at this time! If you have a patch for another block, please fill in its data areas here."
        )
        exit()
    if address < 0x68500:
        return 0x100
    if address >= 0x68500 and address < 0x68600:
        return 0x8
    if address >= 0x68600 and address < 0xCB000:
        return 0x100
    if address >= 0xCB000 and address < 0xCB100:
        return 0x8
    if address >= 0xCB100 and address < 0xDFB00:
        return 0x100
    return 0x8


s184_patch_info = PatchInfo(
    patch_box_code="80A906259F__0008",
    patch_block_index=2,
    patch_filename=internal_path("docs", "patch_1841.bin"),
    block_transfer_sizes_patch=s184_block_transfer_sizes_patch,
)

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
    s184_patch_info,
    checksum_block_location,
)
