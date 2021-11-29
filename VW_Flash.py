from pathlib import Path
import tqdm
import logging
import argparse
import sys
from os import path

from lib.extract_flash import extract_flash_from_frf
from lib.constants import (
    BlockData,
    PreparedBlockData,
    FlashInfo,
    BLE_SERVICE_IDENTIFIER,
)
import lib.binfile as binfile
import lib.simos_flash_utils as simos_flash_utils
import lib.dsg_flash_utils as dsg_flash_utils
import lib.flash_uds as flash_uds
import lib.modules.simos12 as simos12
import lib.modules.simos16 as simos16
import lib.modules.simos18 as simos18
import lib.modules.simos1810 as simos1810
import lib.modules.simos184 as simos184
import lib.modules.dq250mqb as dq250mqb
import lib.modules.simosshared as simosshared

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
for name, number in simosshared.block_name_to_int.items():
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
        "checksum_ecm3",
        "lzss",
        "encrypt",
        "prepare",
        "flash_cal",
        "flash_bin",
        "flash_frf",
        "flash_raw",
        "flash_unlock",
        "get_ecu_info",
        "get_dtcs",
    ],
    required=True,
)
parser.add_argument(
    "--infile", help="the absolute path of an inputfile", action="append"
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

parser.add_argument("--dsg", help="Perform DSG flash actions", action="store_true")

parser.add_argument(
    "--patch-cboot",
    help="Automatically patch CBOOT into Sample Mode",
    action="store_true",
)

parser.add_argument(
    "--simos12", help="specify simos12, available for checksumming", action="store_true"
)
parser.add_argument("--simos16", help="specify simos16", action="store_true")
parser.add_argument("--simos1810", help="specify simos18.10", action="store_true")
parser.add_argument("--simos1841", help="specify simos18.41", action="store_true")


parser.add_argument(
    "--is_early", help="specify an early car for ECM3 checksumming", action="store_true"
)

parser.add_argument(
    "--input_bin",
    type=str,
    help="An (optional) single BIN file to attempt to parse into flash data",
    required=False,
)

parser.add_argument(
    "--output_bin",
    help="output a single BIN file, as used by some commercial tools",
    type=str,
    required=False,
)

parser.add_argument(
    "--interface",
    help="specify an interface type",
    choices=["J2534", "SocketCAN", "BLEISOTP", "USBISOTP", "TEST"],
    default=defaultInterface,
)

parser.add_argument(
    "--ble_name", help="Pass a custom device name for the BLEISOTP adapter"
)

parser.add_argument(
    "--usb_name",
    help="Pass a serial port identifier for the USB ISOTP A0 Firmware. Find one using python -m serial.tools.list_ports",
)

args = parser.parse_args()

flash_info = simos18.s18_flash_info

if args.simos12:
    flash_info = simos12.s12_flash_info

if args.simos1810:
    flash_info = simos1810.s1810_flash_info

if args.simos1841:
    flash_info = simos184.s1841_flash_info

if args.simos16:
    flash_info = simos16.s16_flash_info

if args.dsg:
    flash_info = dq250mqb.dsg_flash_info

flash_utils = simos_flash_utils

if args.dsg:
    flash_utils = dsg_flash_utils

ble_device_name = "BLE_TO_ISOTP20"
if args.ble_name:
    ble_device_name = args.ble_name


async def scan_for_devices(ble_device_name):
    devices = await BleakScanner.discover(service_uuids=[BLE_SERVICE_IDENTIFIER])
    device = None

    for d in devices:
        if d.name == ble_device_name:
            device = d

    if device is None:
        raise RuntimeError("Did not find a BLE_ISOTP device named " + ble_device_name)
    else:
        return device


if args.interface == "BLEISOTP":
    import asyncio
    from bleak import BleakScanner

    logger.info("Searching for BLE device named " + ble_device_name)
    device = asyncio.run(scan_for_devices(ble_device_name))
    args.interface = "BLEISOTP_" + device.address
    logger.info("Found BLE device with address: " + args.interface)

if args.interface == "USBISOTP":
    if args.usb_name is None:
        logger.error(
            "Cannot use USB-ISOTP without specifying a serial device using --usb_name . List serial devices using python -m serial.tools.list_ports"
        )
        exit()
    args.interface = "USBISOTP_" + args.usb_name


def input_blocks_from_frf(frf_path: str) -> dict[str, BlockData]:
    frf_data = Path(frf_path).read_bytes()
    (flash_data, allowed_boxcodes) = extract_flash_from_frf(
        frf_data, flash_info, is_dsg=args.dsg
    )
    input_blocks = {}
    for i in flash_info.block_names_frf.keys():
        filename = flash_info.block_names_frf[i]
        input_blocks[filename] = BlockData(i, flash_data[filename])
    return input_blocks


if args.action == "flash_cal":
    args.block = ["CAL"]

# if the number of block args doesn't match the number of file args, log it and exit
if (args.infile and not args.block) or (
    args.infile and (len(args.block) != len(args.infile))
):
    logger.critical("You must specify a block for every infile")
    exit()

# convert --blocks on the command line into a list of ints
if args.block:
    blocks = [int(simosshared.block_to_number(block)) for block in args.block]

if args.frf:
    input_blocks = input_blocks_from_frf(args.frf)

if args.input_bin:
    input_blocks = binfile.blocks_from_bin(args.input_bin, flash_info)
    logger.info(binfile.input_block_info(input_blocks, flash_info))

# build the dict that's used to proces the blocks
#  'filename' : BlockData (block_number, binary_data)
if args.infile and args.block:
    input_blocks: dict[str, BlockData] = {}
    for i in range(0, len(args.infile)):
        input_blocks[args.infile[i]] = BlockData(
            blocks[i], Path(args.infile[i]).read_bytes()
        )


def callback_function(t, flasher_step, flasher_status, flasher_progress):
    t.update(round(flasher_progress - t.n))
    t.set_description(flasher_status, refresh=True)


def flash_bin(flash_info: FlashInfo, input_blocks: dict[str, BlockData], is_dsg=False):
    logger.info(binfile.input_block_info(input_blocks, flash_info))

    t = tqdm.tqdm(
        total=100,
        colour="green",
        ncols=round(shutil.get_terminal_size().columns * 0.75),
    )

    def wrap_callback_function(flasher_step, flasher_status, flasher_progress):
        callback_function(t, flasher_step, flasher_status, float(flasher_progress))

    flash_utils.flash_bin(
        flash_info,
        input_blocks,
        wrap_callback_function,
        interface=args.interface,
        patch_cboot=args.patch_cboot,
    )

    t.close()


# if statements for the various cli actions
if args.action == "checksum":
    flash_utils.checksum(flash_info=flash_info, input_blocks=input_blocks)

elif args.action == "checksum_ecm3":
    simos_flash_utils.checksum_ecm3(
        flash_info, input_blocks, is_early=(args.is_early or args.simos12)
    )

elif args.action == "lzss":
    simos_flash_utils.lzss_compress(input_blocks, args.outfile)

elif args.action == "encrypt":
    output_blocks = flash_utils.encrypt_blocks(flash_info, input_blocks)

    for filename in output_blocks:
        output_block: PreparedBlockData = output_blocks[filename]
        binary_data = output_block.block_encrypted_bytes
        blocknum = output_block.block_number

        outfile = filename + ".flashable_block" + str(blocknum)
        logger.info("Writing encrypted file to: " + outfile)
        Path(outfile).write_bytes(binary_data)

elif args.action == "prepare":
    output_blocks = flash_utils.checksum_and_patch_blocks(
        flash_info, input_blocks, should_patch_cboot=args.patch_cboot
    )

    if args.output_bin:
        outfile_data = binfile.bin_from_blocks(output_blocks, flash_info)
        Path(args.output_bin).write_bytes(outfile_data)
    else:
        for filename in output_blocks:
            output_block: BlockData = output_blocks[filename]
            binary_data = output_block.block_bytes
            block_number = output_block.block_number
            file_name = filename.rstrip(".bin") + "." + output_block.block_name + ".bin"
            Path(file_name).write_bytes(binary_data)

elif args.action == "flash_cal":
    t = tqdm.tqdm(
        total=100,
        colour="green",
        ncols=round(shutil.get_terminal_size().columns * 0.75),
    )

    def wrap_callback_function(flasher_step, flasher_status, flasher_progress):
        callback_function(t, flasher_step, flasher_status, float(flasher_progress))

    ecuInfo = flash_uds.read_ecu_data(
        flash_info, interface=args.interface, callback=wrap_callback_function
    )

    for did in ecuInfo:
        logger.debug(did + " - " + ecuInfo[did])

    logger.info(binfile.input_block_info(input_blocks, flash_info))

    cal_flash_blocks = {}

    for filename in input_blocks:
        input_block = input_blocks[filename]
        if input_block.block_number != simosshared.block_name_to_int["CAL"]:
            continue
        file_box_code = str(
            input_block.block_bytes[
                flash_info.box_code_location[input_block.block_number][
                    0
                ] : flash_info.box_code_location[input_block.block_number][1]
            ].decode()
        )

        if ecuInfo["VW Spare Part Number"].strip() != file_box_code.strip():
            logger.critical(
                "Attempting to flash a file that doesn't match box codes, exiting!: "
                + ecuInfo["VW Spare Part Number"]
                + " != "
                + file_box_code
            )
            exit()
        else:
            logger.critical("File matches ECU box code")
        cal_flash_blocks[filename] = input_block

    flash_utils.flash_bin(
        flash_info, cal_flash_blocks, wrap_callback_function, interface=args.interface
    )

    t.close()

elif args.action == "flash_frf":
    flash_bin(flash_info, input_blocks)

elif args.action == "flash_unlock":
    cal_block = input_blocks[flash_info.block_names_frf[5]]
    file_box_code = str(
        cal_block.block_bytes[
            flash_info.box_code_location[5][0] : flash_info.box_code_location[5][1]
        ].decode()
    )
    if file_box_code.strip() != flash_info.patch_box_code.strip():
        logger.error(
            f"Boxcode mismatch for unlocking. Got box code {file_box_code} but expected {flash_info.patch_box_code}"
        )
        exit()

    input_blocks["UNLOCK_PATCH"] = BlockData(
        flash_info.patch_block_index + 5, Path(flash_info.patch_filename).read_bytes()
    )

    key_order = list(map(lambda i: flash_info.block_names_frf[i], [1, 2, 3, 4, 5]))
    key_order.insert(4, "UNLOCK_PATCH")
    input_blocks_with_patch = {k: input_blocks[k] for k in key_order}

    flash_bin(flash_info, input_blocks_with_patch)

elif args.action == "flash_bin":
    flash_bin(flash_info, input_blocks, args.dsg)


elif args.action == "flash_raw":
    t = tqdm.tqdm(
        total=100,
        colour="green",
        ncols=round(shutil.get_terminal_size().columns * 0.75),
    )

    def wrap_callback_function(flasher_step, flasher_status, flasher_progress):
        callback_function(t, flasher_step, flasher_status, float(flasher_progress))

    flash_uds.flash_blocks(flash_info, input_blocks, callback=wrap_callback_function)

    t.close()

elif args.action == "get_ecu_info":
    t = tqdm.tqdm(
        total=100,
        colour="green",
        ncols=round(shutil.get_terminal_size().columns * 0.75),
    )

    def wrap_callback_function(flasher_step, flasher_status, flasher_progress):
        callback_function(t, flasher_step, flasher_status, float(flasher_progress))

    ecu_info = flash_uds.read_ecu_data(
        flash_info, interface=args.interface, callback=wrap_callback_function
    )

    [t.write(did + " : " + ecu_info[did]) for did in ecu_info]

    t.close()

elif args.action == "get_dtcs":
    t = tqdm.tqdm(
        total=100,
        colour="green",
        ncols=round(shutil.get_terminal_size().columns * 0.75),
    )

    def wrap_callback_function(flasher_step, flasher_status, flasher_progress):
        callback_function(t, flasher_step, flasher_status, float(flasher_progress))

    dtcs = flash_uds.read_dtcs(
        flash_info, interface=args.interface, callback=wrap_callback_function
    )
    [t.write(str(dtc) + " : " + dtcs[dtc]) for dtc in dtcs]

    t.close()
