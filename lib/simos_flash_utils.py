import logging
import base64

from . import lzssHelper as lzss
from . import checksum as simos_checksum
from . import encrypt as encrypt
from . import constants as constants
from . import simos_uds as simos_uds

cliLogger = logging.getLogger("FlashUtils")


def read_from_file(infile=None):
    f = open(infile, "rb")
    return f.read()


def write_to_file(outfile=None, data_binary=None):
    if outfile and data_binary:
        with open(outfile, "wb") as fullDataFile:
            fullDataFile.write(data_binary)


def decodeBlocks(base64_blocks):
    blocks_infile = {}

    for filename in base64_blocks:
        base64_data = base64_blocks[filename]["base64_data"]
        blocknum = base64_blocks[filename]["blocknum"]

        blocks_infile[filename] = {
            "binary_data": base64.b64decode(str(base64_data)),
            "blocknum": blocknum,
        }

    return blocks_infile


def prepareBlocks(blocks_infile, callback=None):
    for filename in blocks_infile:
        binary_data = blocks_infile[filename]["binary_data"]
        blocknum = blocks_infile[filename]["blocknum"]
        swversion = binary_data[
            constants.box_code_location[blocknum][0] : constants.box_code_location[
                blocknum
            ][1]
        ].decode()
        blocks_infile[filename]["boxcode"] = swversion

        if callback:
            callback(
                flasher_step="PREPARING",
                flasher_status="Preparing "
                + filename
                + " for flashing as block "
                + str(blocknum),
                flasher_progress=20,
            )

        cliLogger.info(
            "Preparing " + filename + " for flashing as block " + str(blocknum)
        )

        if callback:
            callback(
                flasher_step="PREPARING",
                flasher_status="Checksumming "
                + filename
                + " as block "
                + str(blocknum),
                flasher_progress=40,
            )

        corrected_file = (
            simos_checksum.validate(
                data_binary=binary_data, blocknum=blocknum, should_fix=True
            )
            if blocknum < 6
            else binary_data
        )

        if corrected_file == constants.ChecksumState.FAILED_ACTION:
            cliLogger.critical("Failure to checksum and/or save file!")
            continue
        else:
            cliLogger.info("File checksum is valid.")

        if callback:
            callback(
                flasher_step="PREPARING",
                flasher_status="Compressing " + filename,
                flasher_progress=60,
            )

        cliLogger.info(
            "Compressing " + filename + " input size :" + str(len(binary_data))
        )
        compressed_binary = (
            lzss.lzss_compress(corrected_file) if blocknum < 6 else binary_data
        )

        if callback:
            callback(
                flasher_step="PREPARING",
                flasher_status="Encrypting " + filename,
                flasher_progress=80,
            )

        blocks_infile[filename]["binary_data"] = encrypt.encrypt(
            data_binary=compressed_binary
        )

    return blocks_infile


def checksum(blocks_infile):
    for filename in blocks_infile:
        binary_data = blocks_infile[filename]["binary_data"]
        blocknum = blocks_infile[filename]["blocknum"]

        cliLogger.info("Checksumming: " + filename + " as block: " + str(blocknum))

        result = simos_checksum.validate(data_binary=binary_data, blocknum=blocknum)

        if result == constants.ChecksumState.VALID_CHECKSUM:
            cliLogger.info("Checksum on file was valid")
        elif result == constants.ChecksumState.INVALID_CHECKSUM:
            cliLogger.info("Checksum on file was invalid")


def checksum_fix(blocks_infile):
    for filename in blocks_infile:
        binary_data = blocks_infile[filename]["binary_data"]
        blocknum = blocks_infile[filename]["blocknum"]

        cliLogger.info(
            "Fixing Checksum for: " + filename + " as block: " + str(blocknum)
        )

        result = simos_checksum.validate(
            data_binary=binary_data, blocknum=blocknum, should_fix=True
        )

        if result == constants.ChecksumState.FAILED_ACTION:
            cliLogger.info("Checksum correction failed")

        cliLogger.info("Checksum correction successful")
        blocks_infile[filename]["binary_data"] = result

    return blocks_infile


def checksum_ecm3(blocks_infile, should_fix=False, is_early=False):
    blocks_available = {}
    for filename in blocks_infile:
        blocknum = blocks_infile[filename]["blocknum"]
        blocks_available[blocknum] = filename
    asw1_block_number = constants.block_name_to_int["ASW1"]
    cal_block_number = constants.block_name_to_int["CAL"]
    if asw1_block_number in blocks_available and cal_block_number in blocks_available:
        result = simos_checksum.validate_ecm3(
            blocks_infile[blocks_available[asw1_block_number]]["binary_data"],
            blocks_infile[blocks_available[cal_block_number]]["binary_data"],
            should_fix,
            is_early,
        )
        if result == constants.ChecksumState.VALID_CHECKSUM:
            cliLogger.info("Checksum on file was valid")
        elif result == constants.ChecksumState.INVALID_CHECKSUM:
            cliLogger.info("Checksum on file was invalid")
        else:
            cliLogger.info("Checksum on file was corrected!")
            blocks_infile[blocks_available[cal_block_number]]["binary_data"] = result

            return blocks_infile

    else:
        cliLogger.error(
            "Validing ECM3 checksum requires ASW1 and CAL blocks to be provided!"
        )


def lzss_compress(blocks_infile, outfile=None):
    for filename in blocks_infile:

        if outfile:
            lzss.main(inputfile=filename, outputfile=filename + ".compressed")
        else:
            cliLogger.info("No outfile specified, skipping")


def encrypt_blocks(blocks_infile):
    for filename in blocks_infile:
        binary_data = blocks_infile[filename]["binary_data"]
        blocks_infile[filename]["binary_data"] = encrypt.encrypt(
            data_binary=binary_data
        )

    return blocks_infile


def flash_bin(blocks_infile, callback=None, interface="CAN"):
    blocks_infile = prepareBlocks(blocks_infile, callback)
    simos_uds.flash_blocks(
        block_files=blocks_infile, callback=callback, interface=interface
    )


def flash_base64(base64_infile, callback=None):
    if callback:
        callback(
            flasher_step="DECODING",
            flasher_status="Preparing to Base64 decode the block(s)",
            flasher_progress=0,
        )
    blocks_infile = decodeBlocks(base64_infile)
    flash_bin(blocks_infile, callback)


def flash_prepared(blocks_infile, callback=None):
    simos_uds.flash_blocks(blocks_infile, callback=callback)
