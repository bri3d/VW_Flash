import logging
import zlib

from lib.workshop_code import WorkshopCode, crc8_hash

from . import lzss_helper as lzss
from . import dq381_checksum
from .modules import dq381
from . import constants as constants
from .constants import BlockData, FlashInfo, PreparedBlockData
from . import flash_uds

cliLogger = logging.getLogger("FlashUtils")


def checksum_and_patch_blocks(
    flash_info: constants.FlashInfo,
    input_blocks: dict,
    callback=None,
    should_patch_cboot=False,
):
    output_blocks = {}
    for filename in input_blocks:
        binary_data = input_blocks[filename].block_bytes
        blocknum = input_blocks[filename].block_number
        blockname = flash_info.number_to_block_name[blocknum]

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

        (result, corrected_file) = dq381_checksum.validate(
            flash_info=flash_info,
            data_binary=binary_data,
            blocknum=blocknum,
            should_fix=True,
        )
        if result == constants.ChecksumState.FAILED_ACTION:
            cliLogger.critical("Failure to checksum and/or save file CRC32!")
            continue
        cliLogger.info("File CRC32 checksum is valid.")

        output_blocks[filename] = BlockData(blocknum, corrected_file, blockname)
    return output_blocks


def prepare_blocks(
    flash_info: constants.FlashInfo,
    input_blocks: dict,
    callback=None,
    should_patch_cboot=False,
):
    blocks = checksum_and_patch_blocks(
        flash_info, input_blocks, callback, should_patch_cboot
    )
    output_blocks = {}
    for filename in blocks:
        block: BlockData = blocks[filename]
        binary_data = block.block_bytes
        blocknum = block.block_number
        block_checksum = zlib.crc32(binary_data).to_bytes(4, "big")
        try:
            boxcode = binary_data[
                flash_info.box_code_location[blocknum][
                    0
                ] : flash_info.box_code_location[blocknum][1]
            ].decode()

        except:
            boxcode = "-"

        if callback:
            callback(
                flasher_step="PREPARING",
                flasher_status="Compressing " + filename,
                flasher_progress=60,
            )

        cliLogger.info(
            "Compressing " + filename + " input size :" + str(len(binary_data))
        )
        compressed_binary = lzss.lzss_compress(binary_data, exact_padding=True)

        if callback:
            callback(
                flasher_step="PREPARING",
                flasher_status="Encrypting " + filename,
                flasher_progress=80,
            )

        cliLogger.info(
            "Encrypting "
            + filename
            + " compressed size :"
            + str(len(compressed_binary))
        )

        output_blocks[filename] = PreparedBlockData(
            blocknum,
            flash_info.crypto.encrypt(compressed_binary),
            boxcode,
            0xA,  # Compression
            0xA,  # Encryption
            True,  # Should Erase
            block_checksum,
            block.block_name,
        )

    return output_blocks


def checksum(flash_info, input_blocks):
    for filename in input_blocks:
        input_block = input_blocks[filename]
        binary_data = input_block.block_bytes
        blocknum = input_block.block_number

        cliLogger.info("Checksumming: " + filename + " as block: " + str(blocknum))

        (result, _) = dq381_checksum.validate(
            flash_info=flash_info, data_binary=binary_data, blocknum=blocknum
        )

        if result == constants.ChecksumState.VALID_CHECKSUM:
            cliLogger.info("Checksum on file was valid")
        elif result == constants.ChecksumState.INVALID_CHECKSUM:
            cliLogger.info("Checksum on file was invalid")
        else:
            cliLogger.info("Checksumming process failed.")


def checksum_fix(flash_info, input_blocks):
    output_blocks = {}
    for filename in input_blocks:
        input_block: BlockData = input_blocks[filename]
        binary_data = input_block.block_bytes
        blocknum = input_block.block_number
        blockname = flash_info.number_to_block_name[blocknum]

        cliLogger.info(
            "Fixing Checksum for: " + filename + " as block: " + str(blocknum)
        )

        (result, data) = dq381_checksum.validate(
            flash_info=flash_info,
            data_binary=binary_data,
            blocknum=blocknum,
            should_fix=True,
        )

        if result == constants.ChecksumState.FAILED_ACTION:
            cliLogger.info("Checksum correction failed")

        cliLogger.info("Checksum correction successful")
        output_blocks[filename] = BlockData(input_block.block_number, data, blockname)
    return output_blocks


def lzss_compress(input_blocks, outfile=None):
    for filename in input_blocks:

        if outfile:
            lzss.main(inputfile=filename, outputfile=filename + ".compressed")
        else:
            cliLogger.info("No outfile specified, skipping")


def encrypt_blocks(flash_info: FlashInfo, input_blocks_compressed):
    output_blocks = {}
    for filename in input_blocks_compressed:
        input_block: BlockData = input_blocks_compressed[filename]
        binary_data = input_block.block_bytes

        output_blocks[filename] = PreparedBlockData(
            input_block.block_number,
            flash_info.crypto.encrypt(binary_data),
            input_block.boxcode,
            0xA,  # Compression
            0xA,  # Encryption
            True,  # Should Erase
            input_block.uds_checksum,
            input_block.block_name,
        )

    return output_blocks


def flash_bin(
    flash_info: constants.FlashInfo,
    input_blocks: dict[str, BlockData],
    callback=None,
    interface: str = "CAN",
    patch_cboot=False,
    interface_path: str = None,
):
    asw_data = bytearray()
    cal_id = b"NONE"

    for blockname in input_blocks:
        block: BlockData = input_blocks[blockname]
        asw_blocks = [
            block_number
            for block_number in flash_info.block_name_to_number.keys()
            if block_number.startswith("ASW")
        ]
        if block.block_number in [
            flash_info.block_name_to_number[block_name] for block_name in asw_blocks
        ]:
            asw_data += block.block_bytes

    asw_checksum = crc8_hash(asw_data)

    workshop_code = WorkshopCode(asw_checksum=asw_checksum, cal_id=cal_id)

    prepared_blocks = prepare_blocks(
        flash_info, input_blocks, callback, should_patch_cboot=patch_cboot
    )
    flash_uds.flash_blocks(
        flash_info=flash_info,
        block_files=prepared_blocks,
        callback=callback,
        interface=interface,
        interface_path=interface_path,
        workshop_code=workshop_code.as_bytes(),
        stmin_override=300000,
        dq3xx_hack=True,
    )
