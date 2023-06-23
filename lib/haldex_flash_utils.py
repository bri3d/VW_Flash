import logging
import zlib

from . import constants as constants
from . import flash_uds
from .modules import haldex4motion
from .constants import BlockData, FlashInfo, PreparedBlockData
from . import haldex_checksum

from typing import Union

cliLogger = logging.getLogger("FlashUtils")


def prepare_blocks(flash_info: constants.FlashInfo, input_blocks: dict, callback=None):
    blocks = checksum_and_patch_blocks(
        flash_info, input_blocks, callback
    )
    output_blocks = {}
    for filename in blocks:
        block: BlockData = input_blocks[filename]
        binary_data = block.block_bytes
        blocknum = block.block_number
        try:
            boxcode = binary_data[
                haldex4motion.box_code_location_haldex[blocknum][
                    0
                ] : haldex4motion.box_code_location_haldex[blocknum][1]
            ].decode()

        except:
            boxcode = "-"

        if blocknum > 1:
            should_erase = True
        else:
            should_erase = False

        checksum = zlib.crc32(binary_data).to_bytes(4, "big")
        blockname = flash_info.number_to_block_name[blocknum]

        output_blocks[filename] = PreparedBlockData(
            blocknum,
            binary_data,
            boxcode,
            0x0,
            0x0,
            should_erase,
            checksum,
            blockname,
        )
    return output_blocks


def build_blocks(flash_info: FlashInfo, input_blocks: dict[str, BlockData]):
    output_blocks = {}
    for filename in input_blocks:
        input_block = input_blocks[filename]
        binary_data = input_block.block_bytes
        blocknum = input_block.block_number
        blockname = flash_info.number_to_block_name[blocknum]

        cliLogger.info(
            "Haldex block passed through "
            + filename
            + " as block: "
            + str(blocknum)
            + " with name "
            + blockname
        )
        output_blocks[filename] = BlockData(
            input_block.block_number, binary_data, blockname
        )
    return output_blocks


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

        (result, corrected_file) = haldex_checksum.validate(
            data_binary=binary_data,
            blocknum=blocknum,
            should_fix=True,
        )
        if result == constants.ChecksumState.FAILED_ACTION:
            cliLogger.critical("Failure to checksum and/or save file CS!")
            continue
        cliLogger.info("File checksum is valid.")

        output_blocks[filename] = BlockData(blocknum, corrected_file, blockname)
    return output_blocks

def checksum(flash_info, input_blocks):
    for filename in input_blocks:
        input_block = input_blocks[filename]
        binary_data = input_block.block_bytes
        blocknum = input_block.block_number

        cliLogger.info("Checksumming: " + filename + " as block: " + str(blocknum))

        (result, _) = haldex_checksum.validate(
            data_binary=binary_data, blocknum=blocknum
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

        (result, data) = haldex_checksum.validate(
            data_binary=binary_data,
            blocknum=blocknum,
            should_fix=True,
        )

        if result == constants.ChecksumState.FAILED_ACTION:
            cliLogger.info("Checksum correction failed")

        cliLogger.info("Checksum correction successful")
        output_blocks[filename] = BlockData(input_block.block_number, data, blockname)
    return output_blocks


def flash_bin(
    flash_info: constants.FlashInfo,
    input_blocks: dict[str, BlockData],
    callback=None,
    interface: str = "CAN",
    patch_cboot=False,
    interface_path: Union[str, None] = None,
    stmin_override: Union[int, None] = 900000,
):
    prepared_blocks = prepare_blocks(flash_info, input_blocks, callback)
    flash_uds.flash_blocks(
        flash_info=flash_info,
        block_files=prepared_blocks,
        callback=callback,
        interface=interface,
        interface_path=interface_path,
        stmin_override=stmin_override,
    )
