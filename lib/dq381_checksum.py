import struct
import logging
import zlib

from .modules import dq381

from . import constants

logger = logging.getLogger("Checksum")


def validate(
    data_binary: bytes,
    blocknum: int = 3,
    flash_info: constants.FlashInfo = dq381.dsg_flash_info,
    should_fix=False,
):
    checksum_location = 0x44
    start_location = 0x38
    end_location = 0x3C

    current_checksum = struct.unpack(
        ">I", data_binary[checksum_location : checksum_location + 4]
    )[0]

    checksum_start = (
        struct.unpack(">I", data_binary[start_location : start_location + 4])[0]
        - dq381.block_base_address_dsg[blocknum]
    )

    checksum_end = (
        struct.unpack(">I", data_binary[end_location : end_location + 4])[0]
        - dq381.block_base_address_dsg[blocknum]
    )

    checksum_data = data_binary[checksum_start : checksum_end + 1]
    checksum = zlib.crc32(checksum_data)

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
    data_binary[checksum_location : checksum_location + 4] = struct.pack(">I", checksum)
    logger.info("Fixed checksum in binary -> " + hex(checksum))
    return (constants.ChecksumState.FIXED_CHECKSUM, data_binary)
