from enum import Enum
import os
import sys
from typing import Callable, List
from lib.crypto.crypto_interface import CryptoInterface


class BlockData:
    block_number: int
    block_bytes: bytes
    block_name: str

    def __init__(self, block_number, block_bytes, block_name=None):
        self.block_number = block_number
        self.block_bytes = block_bytes
        self.block_name = block_name


class PreparedBlockData:
    block_number: int
    block_encrypted_bytes: bytes
    boxcode: str
    encryption_type: int
    compression_type: int
    should_erase: bool
    uds_checksum: bytes
    block_name: str

    def __init__(
        self,
        block_number: int,
        block_bytes: bytes,
        boxcode: str,
        encryption_type: int,
        compression_type: int,
        should_erase: bool,
        uds_checksum: bytes,
        block_name: str,
    ):
        self.block_number = block_number
        self.block_encrypted_bytes = block_bytes
        self.boxcode = boxcode
        self.encryption_type = encryption_type
        self.compression_type = compression_type
        self.should_erase = should_erase
        self.uds_checksum = uds_checksum
        self.block_name = block_name


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


class ControlModuleIdentifier:
    rxid: int
    txid: int

    def __init__(self, rxid, txid):
        self.rxid = rxid
        self.txid = txid


ecu_control_module_identifier = ControlModuleIdentifier(0x7E8, 0x7E0)


class PatchInfo:
    patch_box_code: str
    patch_block_index: int
    patch_filename: str
    block_transfer_sizes_patch: Callable

    def __init__(
        self,
        patch_box_code,
        patch_block_index,
        patch_filename,
        block_transfer_sizes_patch,
    ):
        self.patch_box_code = patch_box_code
        self.patch_block_index = patch_block_index
        self.patch_filename = patch_filename
        self.block_transfer_sizes_patch = block_transfer_sizes_patch


class FlashInfo:
    base_addresses: dict
    block_lengths: dict
    sa2_script: bytearray
    block_names_frf: dict
    block_identifiers: dict
    block_checksums: dict
    control_module_identifier: ControlModuleIdentifier
    software_version_location: dict
    box_code_location: dict
    block_transfer_sizes: dict
    binfile_layout: dict
    binfile_size: int
    project_name: str
    crypto: CryptoInterface
    block_name_to_number: dict[str, int]
    number_to_block_name: dict[int, str]
    patch_info: PatchInfo
    checksum_block_location: dict[int, int]

    def __init__(
        self,
        base_addresses,
        block_lengths,
        sa2_script,
        block_names_frf,
        block_identifiers,
        block_checksums,
        control_module_identifier,
        software_version_location,
        box_code_location,
        block_transfer_sizes,
        binfile_layout,
        binfile_size,
        project_name,
        crypto,
        block_name_to_number,
        patch_info,
        checksum_block_location,
    ):
        self.base_addresses = base_addresses
        self.block_lengths = block_lengths
        self.sa2_script = sa2_script
        self.block_names_frf = block_names_frf
        self.block_identifiers = block_identifiers
        self.block_checksums = block_checksums
        self.control_module_identifier = control_module_identifier
        self.software_version_location = software_version_location
        self.box_code_location = box_code_location
        self.block_transfer_sizes = block_transfer_sizes
        self.binfile_layout = binfile_layout
        self.binfile_size = binfile_size
        self.project_name = project_name
        self.crypto = crypto
        self.block_name_to_number = block_name_to_number
        self.number_to_block_name = dict(
            (reversed(item) for item in self.block_name_to_number.items())
        )
        self.patch_info = patch_info
        self.checksum_block_location = checksum_block_location

    def block_to_number(self, blockname: str) -> int:
        if blockname.isdigit():
            return int(blockname)
        else:
            return self.block_name_to_number[blockname.upper()]


def internal_path(*path_parts) -> str:
    if sys.platform == "win32":
        __location__ = os.path.dirname(os.path.abspath(sys.argv[0]))
        return os.path.join(__location__, *path_parts)
    else:
        __location__ = os.path.realpath(
            os.path.join(os.getcwd(), os.path.dirname(__file__))
        )
        return os.path.join(__location__, os.path.pardir, *path_parts)


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
    DataRecord(0xF15B, 2, "Fingerprint and Programming Date"),
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
    b"\x22\xf1\x5b": bytes.fromhex(
        "62f15b20071742042042b13d0020071742042042b13d0020071742042042b13d0020071742042042b13d0020071742042042b13d00"
    ),
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

BLE_SERVICE_IDENTIFIER = "0000abf0-0000-1000-8000-00805f9b34fb"
