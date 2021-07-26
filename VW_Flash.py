from pathlib import Path
import tqdm
import logging
import argparse
import sys
from os import path

from lib.extract_flash import extract_flash_from_frf
import lib.simos_flash_utils as simos_flash_utils
import lib.constants as constants
import lib.simos_uds as simos_uds

import shutil

# Get an instance of logger, which we'll pull from the config file
logger = logging.getLogger("VWFlash")

try:
    currentPath = path.dirname(path.abspath(__file__))
except NameError:  # We are the main py2exe script, not a module
    currentPath = path.dirname(path.abspath(sys.argv[0]))

logging.config.fileConfig(path.join(currentPath, "logging.conf"))

logger.info("Starting VW_Flash.py")

if sys.platform == "win32":
    defaultInterface = "J2534"
else:
    defaultInterface = "SocketCAN"

logger.debug("Default interface set to " + defaultInterface)

# build a List of valid block parameters for the help message
block_number_help = []
for name, number in constants.block_name_to_int.items():
    block_number_help.append(name)
    block_number_help.append(str(number))

# Set up the argument/parser with run options
parser = argparse.ArgumentParser(
    description="VW_Flash CLI",
    epilog="The MAIN CLI interface for using the tools herein",
)
parser.add_argument(
    "--action",
    help="The action you want to take",
    choices=[
        "checksum",
        "checksum_fix",
        "checksum_ecm3",
        "checksum_fix_ecm3",
        "lzss",
        "encrypt",
        "prepare",
        "flash_cal",
        "flash_bin",
        "flash_frf",
        "flash_prepared",
        "get_ecu_info",
    ],
    required=True,
)
parser.add_argument(
    "--infile", help="the absolute path of an inputfile", action="append"
)
parser.add_argument(
    "--outfile", help="the absolutepath of a file to output", action="store_true"
)
parser.add_argument(
    "--block",
    type=str,
    help="The block name or number",
    choices=block_number_help,
    action="append",
    required=False,
)

parser.add_argument(
    "--frf",
    type=str,
    help="An (optional) FRF file to source flash data from",
    required=False,
)

parser.add_argument(
    "--patch-cboot",
    help="Automatically patch CBOOT into Sample Mode",
    action="store_true",
)

parser.add_argument(
    "--simos12", help="specify simos12, available for checksumming", action="store_true"
)

parser.add_argument("--simos1810", help="specify simos18.10", action="store_true")

parser.add_argument(
    "--is_early", help="specify an early car for ECM3 checksumming", action="store_true"
)

parser.add_argument(
    "--interface",
    help="specify an interface type",
    choices=["J2534", "SocketCAN", "TEST"],
    default=defaultInterface,
)

args = parser.parse_args()

flash_info = constants.s18_flash_info

if args.simos12:
    flash_info = constants.s12_flash_info

if args.simos1810:
    flash_info = constants.s1810_flash_info

# function that reads in from a file
def read_from_file(infile=None):
    f = open(infile, "rb")
    return f.read()


# function that writes out binary data to a file
def write_to_file(outfile=None, data_binary=None):
    if outfile and data_binary:
        with open(outfile, "wb") as fullDataFile:
            fullDataFile.write(data_binary)


if args.action == "flash_cal":
    if len(args.infile) != 1:
        logger.critical(
            "You chose to flash a calibration, but you must specify a single calibration file"
        )
        exit()

    args.block = ["CAL"]

# if the number of block args doesn't match the number of file args, log it and exit
if (args.infile and not args.block) or (
    args.infile and (len(args.block) != len(args.infile))
):
    logger.critical("You must specify a block for every infile")
    exit()

# convert --blocks on the command line into a list of ints
if args.block:
    blocks = [int(constants.block_to_number(block)) for block in args.block]

# build the dict that's used to proces the blocks
#  Everything is structured based on the following format:
#  {'infile1': {'blocknum': num, 'binary_data': binary},
#     'infile2: {'blocknum': num2, 'binary_data': binary2}
#  }
if args.infile and args.block:
    input_blocks = {}
    for i in range(0, len(args.infile)):
        input_blocks[args.infile[i]] = simos_flash_utils.BlockData(
            blocks[i], read_from_file(args.infile[i])
        )


def callback_function(t, flasher_step, flasher_status, flasher_progress):
    t.update(round(flasher_progress - t.n))
    t.set_description(flasher_status, refresh=True)


def flash_bin(flash_info, input_blocks):
    t = tqdm.tqdm(
        total=100,
        colour="green",
        ncols=round(shutil.get_terminal_size().columns * 0.75),
    )

    def wrap_callback_function(flasher_step, flasher_status, flasher_progress):
        callback_function(t, flasher_step, flasher_status, float(flasher_progress))

    logger.info(
        "Executing flash_bin with the following blocks:\n"
        + "\n".join(
            [
                " : ".join(
                    [
                        filename,
                        str(input_blocks[filename].block_number),
                        constants.int_to_block_name[
                            input_blocks[filename].block_number
                        ],
                        str(
                            input_blocks[filename]
                            .block_bytes[
                                constants.software_version_location[
                                    input_blocks[filename].block_number
                                ][0] : constants.software_version_location[
                                    input_blocks[filename].block_number
                                ][
                                    1
                                ]
                            ]
                            .decode()
                        ),
                        str(
                            input_blocks[filename]
                            .block_bytes[
                                constants.box_code_location[
                                    input_blocks[filename].block_number
                                ][0] : constants.box_code_location[
                                    input_blocks[filename].block_number
                                ][
                                    1
                                ]
                            ]
                            .decode()
                        ),
                    ]
                )
                for filename in input_blocks
            ]
        )
    )

    simos_flash_utils.flash_bin(
        flash_info,
        input_blocks,
        wrap_callback_function,
        interface=args.interface,
        patch_cboot=args.patch_cboot,
    )

    t.close()


# if statements for the various cli actions
if args.action == "checksum":
    simos_flash_utils.checksum(flash_info=flash_info, input_blocks=input_blocks)

elif args.action == "checksum_fix":
    output_blocks = simos_flash_utils.checksum_fix(
        flash_info=flash_info, input_blocks=input_blocks
    )

    # if outfile was specified in the arguments, go through the dict and write each block out
    if args.outfile:
        for filename in output_blocks:
            output_block: simos_flash_utils.BlockData = output_blocks[filename]
            binary_data = output_block.block_bytes
            blocknum = output_block.block_number

            write_to_file(
                data_binary=binary_data,
                outfile=filename.rstrip(".bin")
                + ".checksummed_block"
                + str(blocknum)
                + ".bin",
            )
    else:
        logger.critical("Outfile not specified, files not saved!!")

if args.action == "checksum_ecm3":
    simos_flash_utils.checksum_ecm3(
        flash_info, input_blocks, is_early=(args.is_early or args.simos12)
    )

elif args.action == "checksum_fix_ecm3":
    output_blocks = simos_flash_utils.checksum_ecm3(
        flash_info, input_blocks, should_fix=True, is_early=args.is_early
    )

    # if outfile was specified in the arguments, go through the dict and write each block out
    if args.outfile:
        for filename in output_blocks:
            output_block: simos_flash_utils.BlockData = output_blocks[filename]
            binary_data = output_block.block_bytes
            blocknum = output_block.block_number

            write_to_file(
                data_binary=binary_data,
                outfile=filename.rstrip(".bin")
                + ".checksummed_block"
                + str(blocknum)
                + ".bin",
            )
    else:
        logger.critical("Outfile not specified, files not saved!!")

elif args.action == "lzss":
    simos_flash_utils.lzss_compress(input_blocks, args.outfile)

elif args.action == "encrypt":
    output_blocks = simos_flash_utils.encrypt_blocks(
        flash_info=flash_info, blocks_infile=input_blocks
    )

    # if outfile was specified, go through each block in the dict and write it out
    if args.outfile:
        for filename in output_blocks:
            output_block: simos_flash_utils.PreparedBlockData = output_blocks[filename]
            binary_data = output_block.block_encrypted_bytes
            blocknum = output_block.block_number

            outfile = filename + ".flashable_block" + str(blocknum)
            logger.info("Writing encrypted file to: " + outfile)
            write_to_file(outfile=outfile, data_binary=binary_data)
    else:
        logger.critical("No outfile specified, skipping")


elif args.action == "prepare":
    simos_flash_utils.prepareBlocks(flash_info, input_blocks)

elif args.action == "flash_cal":
    t = tqdm.tqdm(
        total=100,
        colour="green",
        ncols=round(shutil.get_terminal_size().columns * 0.75),
    )

    def wrap_callback_function(flasher_step, flasher_status, flasher_progress):
        callback_function(t, flasher_step, flasher_status, float(flasher_progress))

    ecuInfo = simos_uds.read_ecu_data(
        interface=args.interface, callback=wrap_callback_function
    )

    for did in ecuInfo:
        logger.debug(did + " - " + ecuInfo[did])
    print()
    logger.info(
        "Executing flash_bin with the following blocks:\n"
        + "\n".join(
            [
                " : ".join(
                    [
                        filename,
                        str(input_blocks[filename].block_number),
                        constants.int_to_block_name[
                            input_blocks[filename].block_number
                        ],
                        str(
                            input_blocks[filename]
                            .block_bytes[
                                constants.software_version_location[
                                    input_blocks[filename].block_number
                                ][0] : constants.software_version_location[
                                    input_blocks[filename].block_number
                                ][
                                    1
                                ]
                            ]
                            .decode()
                        ),
                        str(
                            input_blocks[filename]
                            .block_bytes[
                                constants.box_code_location[
                                    input_blocks[filename].block_number
                                ][0] : constants.box_code_location[
                                    input_blocks[filename].block_number
                                ][
                                    1
                                ]
                            ]
                            .decode()
                        ),
                    ]
                )
                for filename in input_blocks
            ]
        )
    )

    for filename in input_blocks:
        input_block: simos_flash_utils.BlockData = input_blocks[filename]
        fileBoxCode = str(
            input_block.block_bytes[
                constants.box_code_location[input_block.block_number][
                    0
                ] : constants.box_code_location[input_block.block_number][1]
            ].decode()
        )

        if ecuInfo["VW Spare Part Number"].strip() != fileBoxCode.strip():
            logger.critical(
                "Attempting to flash a file that doesn't match box codes, exiting!: "
                + ecuInfo["VW Spare Part Number"]
                + " != "
                + fileBoxCode
            )
            exit()
        else:
            logger.critical("File matches ECU box code")

    simos_flash_utils.flash_bin(
        flash_info, input_blocks, wrap_callback_function, interface=args.interface
    )

    t.close()

elif args.action == "flash_frf":
    frf_data = Path(args.frf).read_bytes()
    flash_data = extract_flash_from_frf(frf_data)
    input_blocks = {}
    for i in range(5):
        filename = "FD_" + str(i)
        input_blocks[filename] = simos_flash_utils.BlockData(
            i + 1, flash_data[filename]
        )
    flash_bin(flash_info, input_blocks)

elif args.action == "flash_bin":
    flash_bin(flash_info, input_blocks)


elif args.action == "flash_prepared":
    t = tqdm.tqdm(
        total=100,
        colour="green",
        ncols=round(shutil.get_terminal_size().columns * 0.75),
    )

    def wrap_callback_function(flasher_step, flasher_status, flasher_progress):
        callback_function(t, flasher_step, flasher_status, float(flasher_progress))

    simos_uds.flash_blocks(flash_info, input_blocks, callback=wrap_callback_function)

    t.close()

elif args.action == "get_ecu_info":

    t = tqdm.tqdm(
        total=100,
        colour="green",
        ncols=round(shutil.get_terminal_size().columns * 0.75),
    )

    def wrap_callback_function(flasher_step, flasher_status, flasher_progress):
        callback_function(t, flasher_step, flasher_status, float(flasher_progress))

    ecu_info = simos_uds.read_ecu_data(
        interface=args.interface, callback=wrap_callback_function
    )

    t.close()

    [print(did + " : " + ecu_info[did]) for did in ecu_info]
