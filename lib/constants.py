from enum import Enum
from typing import Callable, List


class ChecksumState(Enum):
    VALID_CHECKSUM = 1
    INVALID_CHECKSUM = 2
    FIXED_CHECKSUM = 3
    FAILED_ACTION = 4


class DataRecord:
    address: int
    parse_type: int
    description: str

    def __init__(self, address, parse_type, description):
        self.address = address
        self.parse_type = parse_type
        self.description = description


class FlashInfo:
    base_addresses: dict
    block_lengths: dict
    sa2_script: bytearray
    key: bytes
    iv: bytes
    block_transfer_sizes_patch: Callable

    def __init__(
        self,
        base_addresses,
        block_lengths,
        sa2_script,
        key,
        iv,
        block_transfer_sizes_patch,
    ):
        self.base_addresses = base_addresses
        self.block_lengths = block_lengths
        self.sa2_script = sa2_script
        self.key = key
        self.iv = iv
        self.block_transfer_sizes_patch = block_transfer_sizes_patch


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


# Simos12 Flash Info

# block sizes for S12
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

s12_iv = bytes.fromhex("306e37426b6b536f316d4a6974366d34")
s12_key = bytes.fromhex("314d7536416e3047396a413252356f45")

s12_sa2_script = bytes.fromhex(
    "6803814A10680393290720094A05872212195482499309011953824A058730032009824A0181494C"
)

s12_flash_info = FlashInfo(
    base_addresses_s12,
    block_lengths_s12,
    s12_sa2_script,
    s12_key,
    s12_iv,
    s18_block_transfer_sizes_patch,
)

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

s18_flash_info = FlashInfo(
    base_addresses_s18,
    block_lengths_s18,
    sa2_script_s18,
    s18_key,
    s18_iv,
    s18_block_transfer_sizes_patch,
)

# Simos 18.10 Flash Info

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

s1810_flash_info = FlashInfo(
    base_addresses_s1810,
    block_lengths_s1810,
    sa2_script_s1810,
    s1810_key,
    s1810_iv,
    s1810_block_transfer_sizes_patch,
)


# The location of each checksum in the bin
checksum_block_location = {
    0: 0x300,  # SBOOT
    1: 0x300,  # CBOOT
    2: 0x300,  # ASW1
    3: 0x0,  # ASW2
    4: 0x0,  # ASW3
    5: 0x300,  # CAL
    6: 0x340,  # CBOOT_temp
}

# The location of the addresses for ECM3 Level 2 CAL monitoring
# 'Early' cars seem to have a different version of the ECM3 module which looks in a different place for the ECM2 Calibration offsets to checksum
# 'Early' cars also calculate the offsets in a different way.

ecm3_cal_monitor_addresses_early = 0x540  # Offset into ASW1
ecm3_cal_monitor_addresses = 0x520  # Offset into ASW1
ecm3_cal_monitor_offset_uncached = 0
ecm3_cal_monitor_offset_cached = 0x20000000
ecm3_cal_monitor_checksum = 0x400  # Offset into CAL

software_version_location = {
    1: [0x437, 0x43F],
    2: [0x627, 0x62F],
    3: [0x203, 0x20B],
    4: [0x203, 0x20B],
    5: [0x23, 0x2B],
    7: [0, 0],
    9: [0, 0],
}

box_code_location = {
    1: [0x0, 0x0],
    2: [0x0, 0x0],
    3: [0x0, 0x0],
    4: [0x0, 0x0],
    5: [0x60, 0x6B],
    7: [0, 0],
    9: [0x0, 0x0],
}

# Conversion dict for block name to number
block_name_to_int = {
    "CBOOT": 1,
    "ASW1": 2,
    "ASW2": 3,
    "ASW3": 4,
    "CAL": 5,
    "CBOOT_TEMP": 6,
    "PATCH_ASW1": 7,
    "PATCH_ASW2": 8,
    "PATCH_ASW3": 9,
}

# We can send the maximum allowable size worth of compressed data in an ISO-TP request when we are using the "normal" TransferData system.

block_transfer_sizes = {1: 0xFFD, 2: 0xFFD, 3: 0xFFD, 4: 0xFFD, 5: 0xFFD}

int_to_block_name = dict((reversed(item) for item in block_name_to_int.items()))


def block_to_number(blockname: str) -> int:
    if blockname.isdigit():
        return int(blockname)
    else:
        return block_name_to_int[blockname.upper()]


data_records: List[DataRecord] = [
    DataRecord(0xF190, 0, "VIN Vehicle Identification Number"),
    DataRecord(0xF19E, 0, "ASAM/ODX File Identifier"),
    DataRecord(0xF1A2, 0, "ASAM/ODX File Version"),
    DataRecord(0xF40D, 1, "Vehicle Speed"),
    DataRecord(0xF806, 1, "Calibration Verification Numbers"),
    DataRecord(0xF187, 0, "VW Spare Part Number"),
    DataRecord(0xF189, 0, "VW Application Software Version Number"),
    DataRecord(0xF191, 0, "VW ECU Hardware Number"),
    DataRecord(0xF1A3, 0, "VW ECU Hardware Version Number"),
    DataRecord(0xF197, 0, "VW System Name Or Engine Type"),
    DataRecord(0xF1AD, 0, "Engine Code Letters"),
    DataRecord(0xF1AA, 0, "VW Workshop System Name"),
    DataRecord(0x0405, 1, "State Of Flash Memory"),
    DataRecord(0x0407, 1, "VW Logical Software Block Counter Of Programming Attempts"),
    DataRecord(
        0x0408,
        1,
        "VW Logical Software Block Counter Of Successful Programming Attempts",
    ),
    DataRecord(0x0600, 1, "VW Coding Value"),
    DataRecord(0xF186, 1, "Active Diagnostic Session"),
    DataRecord(0xF18C, 0, "ECU Serial Number"),
    DataRecord(0xF17C, 0, "VW FAZIT Identification String"),
    DataRecord(0xF442, 1, "Control Module Voltage"),
    DataRecord(0xEF90, 1, "Immobilizer Status SHE"),
    DataRecord(0xF1F4, 0, "Boot Loader Identification"),
    DataRecord(0xF1DF, 1, "ECU Programming Information"),
    DataRecord(0xF1F1, 1, "Tuning Protection SO2"),
    DataRecord(0xF1E0, 1, ""),
    DataRecord(0x12FC, 1, ""),
    DataRecord(0x12FF, 1, ""),
    DataRecord(0xFD52, 1, ""),
    DataRecord(0xFD83, 1, ""),
    DataRecord(0xFDFA, 1, ""),
    DataRecord(0xFDFC, 1, ""),
    DataRecord(0x295A, 1, "Vehicle Mileage"),
    DataRecord(0x295B, 1, "Control Module Mileage"),
    DataRecord(0xF190, 0, "VIN Vehicle Identification Number"),
    DataRecord(0xF19E, 0, "ASAM/ODX File Identifier"),
    DataRecord(0xF1A2, 0, "ASAM/ODX File Version"),
    DataRecord(0xF15B, 1, "Fingerprint and Programming Date"),
    DataRecord(0xF191, 0, "VW ECU Hardware Number"),
    DataRecord(0xF1A3, 0, "VW ECU Hardware Version Number"),
    DataRecord(0xF187, 0, "VW Spare Part Number"),
    DataRecord(0xF189, 0, "VW Application Software Version Number"),
    DataRecord(0xF1F4, 0, "Boot Loader Identification"),
    DataRecord(0xF197, 0, "VW System Name Or Engine Type"),
    DataRecord(0xF1AD, 0, "Engine Code Letters"),
    DataRecord(0xF17C, 0, "VW FAZIT Identification String"),
    DataRecord(
        0xF1A5, 1, "VW Coding Repair Shop Code Or Serial Number (Coding Fingerprint),"
    ),
    DataRecord(0x0405, 1, "State Of Flash Memory"),
    DataRecord(0x0600, 1, "VW Coding Value"),
    DataRecord(0xF1AB, 0, "VW Logical Software Block Version"),
    DataRecord(0xF804, 0, "Calibration ID"),
    DataRecord(0xF17E, 0, "ECU Production Change Number"),
]

j2534DLL = (
    "C:/Program Files (x86)/OpenECU/OpenPort 2.0/drivers/openport 2.0/op20pt32.dll"
)


### test data for the FakeConnection

testdata = {
    b"\x10\x03": b"\x50\x03\x12\x23\x34\x45",
    b"\x22\xf1\x90": b"\x62\xf1\x903VW12345678912345",
    b"\x10\x4f": b"\x50\x4f\x12\x23\x34\x45",
    b"\x27\x03": b"\x67\x03\x12\x23\x34\x45",
    b"\x27\x04\x12\x23\xa1\x88": b"\x67\x04",
    b"\x2c\x03\xf2\x00": b"\x2c\x03\xf2\x00",
    b"\x2c\x02\xf2\x00\x14\xd0\x01\xb3\xaa\x01\xd0\x01\x20\x22\x02\xd0\x01\x24\x00\x02\xd0\x00\xc3\x6e\x01\xd0\x00\xf3\x9a\x01\xd0\x01\x3f\xae\x02\xd0\x01\x1e\xee\x02\xd0\x01\x20\xc6\x02\xd0\x01\x43\xf6\x02\xd0\x01\x43\x1a\x02\xd0\x01\x3c\x76\x02\xd0\x01\x38\x24\x02\xd0\x01\x1b\x26\x02\xd0\x01\x36\x12\x02\xd0\x01\x1d\x8a\x02\xd0\x01\x1d\x96\x02\xd0\x01\x1e\x08\x02\xd0\x01\x1e\x04\x02\xd0\x01\x5c\x2c\x02\xd0\x01\x5c\x34\x02\xd0\x00\xc1\x77\x01\xd0\x00\xe6\x83\x01\xd0\x01\xde\x90\x01\xd0\x01\xde\x8e\x01\xd0\x01\xde\x8a\x01\xd0\x01\xde\x89\x01\xd0\x01\xde\x8d\x01\xd0\x00\xef\xb1\x01\xd0\x00\xef\xb2\x01\xd0\x00\xef\xb3\x01\xd0\x00\xef\xb4\x01\xd0\x00\xe5\x65\x01\xd0\x00\xe5\x66\x01\xd0\x00\xe5\x67\x01\xd0\x00\xe5\x68\x01\xd0\x01\x3e\x42\x02\xd0\x01\x1e\xfc\x02\xd0\x00\xc1\x79\x01\xd0\x01\x52\x2e\x02\xd0\x01\x51\x5c\x02\xd0\x01\x54\x44\x02\xd0\x01\x36\x00\x02\xd0\x01\x1d\xb2\x02\xd0\x01\x1e\xc0\x02\xd0\x00\x97\xe4\x04\xd0\x00\x98\x00\x04": b"\x62\xf2\x00",
    b"\x22\xf2\x00": b"\x62\xf2\x00\x01\xd0\x01\xb3\xaa\x01\xd0\x01\x20\x22\x02\xd0\x01\x24\x00\x02\xd0\x00\xc3\x6e\x01\xd0\x00\xf3\x9a\x01\xd0\x01\x3f\xae\x02\xd0\x01\x1e\xee\x02\xd0\x01\x20\xc6\x02\xd0\x01\x43\xf6\x02\xd0\x01\x43\x1a\x02\xd0\x01\x3c\x76\x02\xd0\x01\x38\x24\x02\xd0\x01\x1b\x26\x02\xd0\x01\x36\x12\x02\xd0\x01\x1d\x8a\x02\xd0\x01\x1d\x96\x02\xd0\x01\x1e\x08\x02\xd0\x01\x1e\x04\x02\xd0\x01\x5c\x2c\x02",
    b"\x22\xf1\x9e": b"\x62\xf1\x9e\x45\x56\x5f\x45\x43\x4d\x31\x38\x54\x46\x53\x30\x32\x30\x38\x56\x30\x39\x30\x36\x32\x36\x34\x4c\x00",
    b"\x22\xf1\xa2": b"\x62\xf1\xa2\x30\x30\x31\x30\x30\x34",
    b"\x22\xf1\x5b": b"\x62\xf1\x5b\x20\x10\x08\x00\x00\x03\x78\x1f\xd7\x00\x20\x10\x08\x00\x00\x03\x78\x1f\xd7\x00\x20\x10\x08\x00\x00\x03\x78\x1f\xd7\x00\x20\x10\x08\x00\x00\x03\x78\x1f\xd7\x00\x20\x10\x08\x00\x00\x03\x78\x1f\xd7\x00",
    b"\x22\xf1\x91": b"\x62\xf1\x91\x30\x36\x4c\x39\x30\x37\x33\x30\x39\x42\x20",
    b"\x22\xf1\xa3": b"\x62\xf1\xa3\x48\x33\x31",
    b"\x22\xf1\x87": b"\x62\xf1\x87\x38\x56\x30\x39\x30\x36\x32\x36\x34\x4d\x20",
    b"\x22\xf1\x89": b"\x62\xf1\x89\x30\x30\x30\x34",
    b"\x22\xf1\xf4": b"\x62\xf1\xf4\x4d\x44\x47\x31\x20\x20\x43\x42\x2e\x30\x36\x2e\x30\x33\x31\x2e\x35\x20\x30\x31\x33\x2e\x30\x30\x20\x20\x20\x20\x20",
    b"\x22\xf1\x97": b"\x62\xf1\x97\x52\x34\x20\x32\x2e\x30\x6c\x20\x54\x46\x53\x49\x20",
    b"\x22\xf1\xad": b"\x62\xf1\xad\x44\x47\x55\x41",
    b"\x22\xf1\x7c": b"\x62\xf1\x7c\x5a\x53\x43\x2d\x38\x36\x34\x31\x35\x2e\x30\x37\x2e\x31\x38\x37\x38\x34\x33\x30\x33\x32\x30",
    b"\x22\xf1\xa5": b"\x62\xf1\xa5\x00\x00\x03\x78\x1f\xd7",
    b"\x22\x04\x05": b"\x62\x04\x05\x00",
    b"\x04": b"\x04",
}
