import csv
import os
import struct
import logging
import sys

from . import fastcrc
from . import constants

logger = logging.getLogger("Checksum")


def validate(
    flash_info: constants.FlashInfo,
    data_binary: bytes,
    blocknum: int = 5,
    should_fix=False,
):

    checksum_location = constants.checksum_block_location[blocknum]

    current_checksum = struct.unpack(
        "<I", data_binary[checksum_location + 4 : checksum_location + 8]
    )[0]
    checksum_area_count = data_binary[checksum_location + 8]
    base_address = flash_info.base_addresses[blocknum]

    addresses = []
    for i in range(0, checksum_area_count * 2):
        address = struct.unpack(
            "<I",
            data_binary[
                checksum_location + 12 + (i * 4) : checksum_location + 16 + (i * 4)
            ],
        )
        offset = address[0] - base_address
        addresses.append(offset)
    checksum_data = bytearray()
    for i in range(0, len(addresses), 2):
        start_address = int(addresses[i])
        end_address = int(addresses[i + 1])
        logger.debug("Adding " + hex(start_address) + ":" + hex(end_address))
        checksum_data += data_binary[start_address : end_address + 1]

    # The CRC checksum algorithm used in Simos is 32-bit, 0x4C11DB7 polynomial, 0x0 initial value, 0x0 ending xor.
    # Please see fastcrc.py for a reference bitwise reference implementation as well as the generated fast tabular implementation.

    checksum = fastcrc.crc_32_fast(checksum_data)
    logger.debug("Checksum = " + hex(checksum))

    if checksum == current_checksum:
        logger.info("File is valid!")
        return (constants.ChecksumState.VALID_CHECKSUM, data_binary)
    else:
        logger.warning(
            "File is invalid! File's embedded checksum: "
            + hex(current_checksum)
            + " does not match calculated: "
            + hex(checksum)
        )
        if should_fix:
            return fix(data_binary, checksum, checksum_location)
        else:
            return (constants.ChecksumState.INVALID_CHECKSUM, data_binary)


def fix(data_binary, checksum, checksum_location):
    data_binary = bytearray(data_binary)
    data_binary[checksum_location + 4 : checksum_location + 8] = struct.pack(
        "<I", checksum
    )
    logger.info("Fixed checksum in binary -> " + hex(checksum))
    return (constants.ChecksumState.FIXED_CHECKSUM, data_binary)


def load_ecm3_from_csv(cal_version):
    csv_path = constants.internal_path("data", "box_codes.csv")

    with open(csv_path, "r") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            if row["cal_version"] == cal_version:
                return [row["ecm3_address_start"], row["ecm3_address_end"]]
    logger.error("Could not find ECM3 location for " + cal_version)


def load_ecm3_location(data_binary_cal):
    version_start_address = constants.software_version_location[5][0]
    version_end_address = constants.software_version_location[5][1]
    cal_version = data_binary_cal[version_start_address:version_end_address].decode(
        "US-ASCII"
    )
    return load_ecm3_from_csv(cal_version)


def locate_ecm3_with_asw1(
    flash_info: constants.FlashInfo, data_binary_asw1, is_early=False
):
    addresses = []
    checksum_address_location = (
        constants.ecm3_cal_monitor_addresses_early
        if is_early
        else constants.ecm3_cal_monitor_addresses
    )
    base_address = flash_info.base_addresses[constants.block_name_to_int["CAL"]]
    checksum_area_count = 1
    for i in range(0, checksum_area_count * 2):
        address = struct.unpack(
            "<I",
            data_binary_asw1[
                checksum_address_location
                + (i * 4) : checksum_address_location
                + 4
                + (i * 4)
            ],
        )

        offset = address[0] + constants.ecm3_cal_monitor_offset_uncached - base_address
        if offset < 0:
            offset = (
                address[0] + constants.ecm3_cal_monitor_offset_cached - base_address
            )

        addresses.append(offset)
    if addresses[0] < 0:
        return locate_ecm3_with_asw1(flash_info, data_binary_asw1, True)
    return addresses


def validate_ecm3(addresses, data_binary_cal: bytes, should_fix=False):
    checksum_location_cal = constants.ecm3_cal_monitor_checksum
    # Initial value
    checksum = (
        struct.unpack(
            "<I",
            data_binary_cal[checksum_location_cal + 8 : checksum_location_cal + 12],
        )[0]
        << 32
    )
    checksum += struct.unpack(
        "<I", data_binary_cal[checksum_location_cal + 12 : checksum_location_cal + 16]
    )[0]

    for i in range(0, len(addresses), 2):
        start_address = int(addresses[i])
        end_address = int(addresses[i + 1])
        logger.debug(
            "ECM3 checksum adding: " + hex(start_address) + ":" + hex(end_address)
        )
        for j in range(start_address, end_address, 4):
            add_value = struct.unpack("<I", data_binary_cal[j : j + 4])[0]
            checksum += add_value

    checksum_current = (
        struct.unpack(
            "<I", data_binary_cal[checksum_location_cal : checksum_location_cal + 4]
        )[0]
        << 32
    )
    checksum_current += struct.unpack(
        "<I", data_binary_cal[checksum_location_cal + 4 : checksum_location_cal + 8]
    )[0]

    logger.info(
        "ECM3 File Embedded Checksum: "
        + hex(checksum_current)
        + ", Calculated checksum : "
        + hex(checksum)
    )
    if checksum_current == checksum:
        logger.info("ECM3 was valid!")
        return (constants.ChecksumState.VALID_CHECKSUM, data_binary_cal)
    else:
        logger.warning("ECM3 Checksum did not match!")
        if should_fix:
            data_binary_cal = bytearray(data_binary_cal)
            data_binary_cal[
                checksum_location_cal : checksum_location_cal + 4
            ] = struct.pack("<I", checksum >> 32)
            data_binary_cal[
                checksum_location_cal + 4 : checksum_location_cal + 8
            ] = struct.pack("<I", checksum & 0xFFFFFFFF)
            return (constants.ChecksumState.FIXED_CHECKSUM, data_binary_cal)
        else:
            return (constants.ChecksumState.INVALID_CHECKSUM, data_binary_cal)
