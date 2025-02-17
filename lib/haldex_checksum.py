import struct
import logging

from . import constants
from .modules import haldex4motion

logger = logging.getLogger("Checksum")


def validate(
    data_binary: bytes,
    blocknum: int = 3,
    should_fix=False,
):
    # Don't checksum the DRIVER
    if blocknum == 1:
        logger.debug("Ignoring DRIVER checksum")
        return (constants.ChecksumState.FIXED_CHECKSUM, data_binary)

    checksum_location = haldex4motion.checksum_block_location[blocknum]

    # We add 8 bytes to ignore the block address & length
    current_checksum = struct.unpack(
        "<H", data_binary[(checksum_location + 0x8) : (checksum_location + 0x8) + 2]
    )[0]

    # Grab the data before and after the checksum block
    checksum_data = data_binary[0:checksum_location] + (
        data_binary[checksum_location + 0xA :]
    )

    checksum = 0
    for i in range(0, len(checksum_data), 2):
        # Simple 16bit adder
        checksum = (
            checksum + struct.unpack("<H", checksum_data[i : i + 2])[0]
        ) & 0xFFFF

    # NOT the result
    checksum = 0xFFFF - checksum

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
            return fix(data_binary, checksum, (checksum_location + 0x8))
        else:
            return (constants.ChecksumState.INVALID_CHECKSUM, data_binary)


def fix(data_binary, checksum, checksum_location):
    data_binary = bytearray(data_binary)
    data_binary[checksum_location : checksum_location + 2] = struct.pack("<H", checksum)
    logger.info("Fixed checksum in binary -> " + hex(checksum))
    return (constants.ChecksumState.FIXED_CHECKSUM, bytes(data_binary))
