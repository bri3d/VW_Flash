import logging
import zlib

from . import constants as constants
from . import flash_uds
from .modules import haldex4motion
from .constants import BlockData, FlashInfo, PreparedBlockData

cliLogger = logging.getLogger("FlashUtils")


def prepare_blocks(flash_info: constants.FlashInfo, input_blocks: dict, callback=None):
    output_blocks = {}
    for filename in input_blocks:
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
            "Haldex block passed through " + filename + " as block: " + str(blocknum) + " with name " + blockname
        )
        output_blocks[filename] = BlockData(
            input_block.block_number, binary_data, blockname
        )
    return output_blocks


def checksum_and_patch_blocks(
    flash_info: constants.FlashInfo,
    input_blocks: dict[str, BlockData],
    callback=None,
    should_patch_cboot=False,
):
    return build_blocks(flash_info, input_blocks)


def flash_bin(
    flash_info: constants.FlashInfo,
    input_blocks: dict,
    callback=None,
    interface: str = "CAN",
    patch_cboot=False,
    interface_path: str = None,
):
    prepared_blocks = prepare_blocks(flash_info, input_blocks, callback)
    flash_uds.flash_blocks(
        flash_info=flash_info,
        block_files=prepared_blocks,
        callback=callback,
        interface=interface,
        interface_path=interface_path,
    )
