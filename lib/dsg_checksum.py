import struct
import logging
import zlib

from . import constants

logger = logging.getLogger("Checksum")


def validate(
    data_binary: bytes,
    blocknum: int = 3,
    should_fix=False,
):
    checksum_location = len(data_binary) - 4

    current_checksum = struct.unpack(
        "<I", data_binary[checksum_location : checksum_location + 4]
    )[0]

    checksum_data = data_binary[:-4]

    # The CRC checksum algorithm used in DSG is JAMCRC - the "NOT" of CRC32
    # We can't use the normal ~ NOT operation because it will produce a signed int.

    checksum = int("0b" + "1" * 32, 2) - zlib.crc32(checksum_data)

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
    data_binary[checksum_location : checksum_location + 4] = struct.pack("<I", checksum)
    logger.info("Fixed checksum in binary -> " + hex(checksum))
    return (constants.ChecksumState.FIXED_CHECKSUM, data_binary)
