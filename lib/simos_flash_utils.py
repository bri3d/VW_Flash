import logging
import base64

from . import lzss_helper as lzss
from . import checksum as simos_checksum
from . import encrypt as encrypt
from . import patch_cboot
from . import constants as constants
from . import simos_uds as simos_uds

cliLogger = logging.getLogger("FlashUtils")


class BlockData:
    block_number: int
    block_bytes: bytes

    def __init__(self, block_number, block_bytes):
        self.block_number = block_number
        self.block_bytes = block_bytes


class PreparedBlockData:
    block_number: int
    block_encrypted_bytes: bytes
    boxcode: str

    def __init__(self, block_number, block_bytes, boxcode):
        self.block_number = block_number
        self.block_encrypted_bytes = block_bytes
        self.boxcode = boxcode


def decode_blocks(base64_blocks):
    output_blocks = {}

    for filename in base64_blocks:
        base64_data = base64_blocks[filename]["base64_data"]
        blocknum = base64_blocks[filename]["blocknum"]

        block_data = BlockData(blocknum, base64.b64decode(str(base64_data)))
        output_blocks[filename] = block_data

    return output_blocks


def prepare_blocks(
    flash_info: constants.FlashInfo,
    input_blocks: dict,
    callback=None,
    should_patch_cboot=False,
):
    output_blocks = {}
    for filename in input_blocks:
        binary_data = input_blocks[filename].block_bytes
        blocknum = input_blocks[filename].block_number
        try:
            boxcode = binary_data[
                constants.box_code_location[blocknum][0] : constants.box_code_location[
                    blocknum
                ][1]
            ].decode()

        except:
            boxcode = "-"

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

        if blocknum == constants.block_name_to_int["CAL"]:
            (result, binary_data) = checksum_ecm3(
                flash_info=flash_info,
                input_blocks=input_blocks,
                should_fix=True,
                is_early=False,
            )

            if result == constants.ChecksumState.FAILED_ACTION:
                cliLogger.critical("Failure to checksum and/or save file ECM3!")
                continue

            cliLogger.info("File ECM3 checksum is valid.")

        if blocknum == constants.block_name_to_int["CBOOT"]:
            if should_patch_cboot:
                binary_data = patch_cboot.patch_cboot(binary_data)
            (result, binary_data) = simos_checksum.validate(
                flash_info=flash_info,
                data_binary=binary_data,
                blocknum=constants.block_name_to_int["CBOOT_TEMP"],
                should_fix=True,
            )
            if result == constants.ChecksumState.FAILED_ACTION:
                cliLogger.critical(
                    "Failure to checksum and/or save CBOOT_TEMP secondary CRC32!"
                )
                continue
            cliLogger.info("CBOOT secondary CRC32 checksum is valid.")

        if blocknum < 6:
            (result, corrected_file) = simos_checksum.validate(
                flash_info=flash_info,
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

        cliLogger.info(
            "Encrypting "
            + filename
            + " compressed size :"
            + str(len(compressed_binary))
        )
        output_blocks[filename] = PreparedBlockData(
            blocknum,
            encrypt.encrypt(flash_info=flash_info, data_binary=compressed_binary),
            boxcode,
        )

    return output_blocks


def checksum(flash_info, input_blocks):
    for filename in input_blocks:
        input_block = input_blocks[filename]
        binary_data = input_block.block_bytes
        blocknum = input_block.block_number

        cliLogger.info("Checksumming: " + filename + " as block: " + str(blocknum))

        (result, _) = simos_checksum.validate(
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

        cliLogger.info(
            "Fixing Checksum for: " + filename + " as block: " + str(blocknum)
        )

        (result, data) = simos_checksum.validate(
            flash_info=flash_info,
            data_binary=binary_data,
            blocknum=blocknum,
            should_fix=True,
        )

        if result == constants.ChecksumState.FAILED_ACTION:
            cliLogger.info("Checksum correction failed")

        cliLogger.info("Checksum correction successful")
        output_blocks[filename] = BlockData(input_block.block_number, data)
    return output_blocks


def checksum_ecm3(
    flash_info: constants.FlashInfo, input_blocks, should_fix=False, is_early=False
):
    blocks_available = {}
    for filename in input_blocks:
        input_block: BlockData = input_blocks[filename]
        blocknum = input_block.block_number
        blocks_available[blocknum] = input_block
    asw1_block_number = constants.block_name_to_int["ASW1"]
    cal_block_number = constants.block_name_to_int["CAL"]
    addresses = []
    if asw1_block_number in blocks_available and cal_block_number in blocks_available:
        addresses = simos_checksum.locate_ecm3_with_asw1(
            flash_info, blocks_available[asw1_block_number].block_bytes, is_early
        )
    elif cal_block_number in blocks_available:
        addresses = simos_checksum.load_ecm3_location(
            blocks_available[cal_block_number].block_bytes
        )
    else:
        cliLogger.error("Validing ECM3 checksum requires CAL block to be provided!")
        return (constants.ChecksumState.FAILED_ACTION, None)

    (result, validated_ecm3_data) = simos_checksum.validate_ecm3(
        addresses, blocks_available[cal_block_number].block_bytes, should_fix
    )

    if result == constants.ChecksumState.VALID_CHECKSUM:
        cliLogger.info("ECM3 Checksum on file was valid")
    elif result == constants.ChecksumState.INVALID_CHECKSUM:
        cliLogger.info("ECM3 Checksum on file was invalid")
    else:
        cliLogger.info("ECM3 Checksum on file was corrected!")

    return (result, validated_ecm3_data)


def lzss_compress(input_blocks, outfile=None):
    for filename in input_blocks:

        if outfile:
            lzss.main(inputfile=filename, outputfile=filename + ".compressed")
        else:
            cliLogger.info("No outfile specified, skipping")


def encrypt_blocks(flash_info, input_blocks_compressed):
    output_blocks = {}
    for filename in input_blocks_compressed:
        input_block: BlockData = input_blocks_compressed[filename]
        binary_data = input_block.block_bytes

        output_blocks[filename] = PreparedBlockData(
            input_block.block_number,
            encrypt.encrypt(flash_info=flash_info, data_binary=binary_data),
            input_block.boxcode,
        )

    return output_blocks


def flash_bin(
    flash_info: constants.FlashInfo,
    input_blocks: dict,
    callback=None,
    interface: str = "CAN",
    patch_cboot=False,
):
    prepared_blocks = prepare_blocks(
        flash_info, input_blocks, callback, should_patch_cboot=patch_cboot
    )
    simos_uds.flash_blocks(
        flash_info=flash_info,
        block_files=prepared_blocks,
        callback=callback,
        interface=interface,
    )


def flash_base64(flash_info, base64_infile, callback=None):
    if callback:
        callback(
            flasher_step="DECODING",
            flasher_status="Preparing to Base64 decode the block(s)",
            flasher_progress=0,
        )
    blocks_infile = decode_blocks(base64_infile)
    flash_bin(flash_info, blocks_infile, callback)
