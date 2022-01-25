import logging

from . import lzss_helper as lzss
from . import dsg_checksum as dsg_checksum
from . import constants as constants
from . import flash_uds
from .modules import dq250mqb
from .constants import BlockData, FlashInfo, PreparedBlockData

cliLogger = logging.getLogger("FlashUtils")


def checksum_blocks(
    flash_info: constants.FlashInfo,
    input_blocks: dict[str, BlockData],
    callback=None,
):
    output_blocks = {}
    for filename in input_blocks:
        binary_data = input_blocks[filename].block_bytes
        blocknum = input_blocks[filename].block_number
        blockname = dq250mqb.int_to_block_name[blocknum]

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

        # Block 2 (Driver) has a different checksum mechanism - it is sent externally.
        if blocknum != 2:
            (result, corrected_file) = dsg_checksum.validate(
                data_binary=binary_data,
                blocknum=blocknum,
                should_fix=True,
            )
            if result == constants.ChecksumState.FAILED_ACTION:
                cliLogger.critical("Failure to checksum and/or save file CRC32!")
                continue
            cliLogger.info("File CRC32 checksum is valid.")
        else:
            corrected_file = binary_data

        output_blocks[filename] = BlockData(blocknum, corrected_file, blockname)
    return output_blocks


def checksum_and_patch_blocks(
    flash_info: constants.FlashInfo,
    input_blocks: dict[str, BlockData],
    callback=None,
    should_patch_cboot=False,
):
    return checksum_blocks(flash_info, input_blocks, callback)


def prepare_blocks(flash_info: constants.FlashInfo, input_blocks: dict, callback=None):
    blocks = checksum_blocks(flash_info, input_blocks, callback)
    output_blocks = {}
    for filename in blocks:
        block: BlockData = blocks[filename]
        binary_data = block.block_bytes
        blocknum = block.block_number
        try:
            boxcode = binary_data[
                dq250mqb.box_code_location_dsg[blocknum][
                    0
                ] : dq250mqb.box_code_location_dsg[blocknum][1]
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
        compressed_binary = lzss.lzss_compress(binary_data, True)

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

        if blocknum > 2:
            should_erase = True
        else:
            should_erase = False

        output_blocks[filename] = PreparedBlockData(
            blocknum,
            flash_info.crypto.encrypt(compressed_binary),
            boxcode,
            0x1,
            0x1,
            should_erase,
            flash_info.block_checksums[blocknum],
            block.block_name,
        )

    return output_blocks


def checksum(flash_info, input_blocks):
    for filename in input_blocks:
        input_block = input_blocks[filename]
        binary_data = input_block.block_bytes
        blocknum = input_block.block_number

        cliLogger.info("Checksumming: " + filename + " as block: " + str(blocknum))

        (result, _) = dsg_checksum.validate(data_binary=binary_data, blocknum=blocknum)

        if result == constants.ChecksumState.VALID_CHECKSUM:
            cliLogger.info("Checksum on file was valid")
        elif result == constants.ChecksumState.INVALID_CHECKSUM:
            cliLogger.info("Checksum on file was invalid")
        else:
            cliLogger.info("Checksumming process failed.")


def checksum_fix(flash_info: FlashInfo, input_blocks: dict[str, BlockData]):
    output_blocks = {}
    for filename in input_blocks:
        input_block = input_blocks[filename]
        binary_data = input_block.block_bytes
        blocknum = input_block.block_number
        blockname = dq250mqb.int_to_block_name[blocknum]

        cliLogger.info(
            "Fixing Checksum for: " + filename + " as block: " + str(blocknum)
        )

        (result, data) = dsg_checksum.validate(
            data_binary=binary_data,
            blocknum=blocknum,
            should_fix=True,
        )

        if result == constants.ChecksumState.FAILED_ACTION:
            cliLogger.info("Checksum correction failed")

        cliLogger.info("Checksum correction successful")
        output_blocks[filename] = BlockData(input_block.block_number, data, blockname)
    return output_blocks


def encrypt_blocks(
    flash_info: FlashInfo, input_blocks_compressed: dict[str, BlockData]
) -> dict[str, PreparedBlockData]:
    output_blocks = {}
    for filename in input_blocks_compressed:
        input_block = input_blocks_compressed[filename]
        binary_data = input_block.block_bytes

        if input_block.block_number > 2:
            should_erase = True
        else:
            should_erase = False

        output_blocks[filename] = PreparedBlockData(
            input_block.block_number,
            flash_info.crypto.encrypt(binary_data),
            input_block.boxcode,
            0x1,  # Compression
            0x1,  # Encryption
            should_erase,
            flash_info.block_checksums[input_block.block_number],
            input_block.block_name,
        )

    return output_blocks


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
