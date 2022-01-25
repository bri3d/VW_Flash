import argparse
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import csv
import itertools
import sys
from lib import binfile
from lib import constants
from lib import checksum
from lib.extract_flash import extract_odx_from_frf, extract_data_from_odx
from pathlib import Path
from lib.modules import simos18
from lib.modules import simos1810
from lib.modules import simos184
from lib.modules import simos16
from lib.modules import simos12
from lib.modules import simos122
from lib.modules import simos10
from lib.modules import simos8


def extract_cboot_version(flash_data: bytes, flash_info: constants.FlashInfo):
    start_address = flash_info.software_version_location[1][0]
    end_address = flash_info.software_version_location[1][1]
    return (
        flash_data[start_address:end_address].decode("US-ASCII").strip().strip("\x00")
    )


def extract_cboot_filename(flash_data: bytes, flash_info: constants.FlashInfo):
    start_address = flash_info.software_version_location[1][0]
    end_address = flash_info.software_version_location[1][1]
    return (
        flash_data[start_address:end_address]
        .decode("US-ASCII")[3:5]
        .strip()
        .strip("\x00")
    )


def extract_asw_version(flash_data: bytes, flash_info: constants.FlashInfo):
    start_address = flash_info.software_version_location[2][0]
    end_address = flash_info.software_version_location[2][1]
    return (
        flash_data[start_address:end_address].decode("US-ASCII").strip().strip("\x00")
    )


def extract_ecm3_addresses(
    flash_data: bytes, flash_info: constants.FlashInfo, is_early: bool
):
    return checksum.locate_ecm3_with_asw1(flash_info, flash_data, is_early)


def extract_cal_version(flash_data: bytes, flash_info: constants.FlashInfo):
    start_address = flash_info.software_version_location[5][0]
    end_address = flash_info.software_version_location[5][1]
    return (
        flash_data[start_address:end_address].decode("US-ASCII").strip().strip("\x00")
    )


def extract_box_code(flash_data: bytes, flash_info: constants.FlashInfo):
    start_address = flash_info.box_code_location[5][0]
    end_address = flash_info.box_code_location[5][1]
    return (
        flash_data[start_address:end_address].decode("US-ASCII").strip().strip("\x00")
    )


def extract_box_version(flash_data: bytes):
    start_address = 0x80
    end_address = 0x84
    return (
        flash_data[start_address:end_address].decode("US-ASCII").strip().strip("\x00")
    )


def extract_engine_name(flash_data: bytes):
    start_address = 0x6C
    end_address = 0x78
    return (
        flash_data[start_address:end_address].decode("US-ASCII").strip().strip("\x00")
    )


def extract_info_from_flash_blocks(
    flash_blocks: dict, flash_info: constants.FlashInfo, allowed_boxcodes=None
):
    if len(flash_info.block_names_frf) > 3:
        cboot_key = flash_info.block_names_frf[1]
        asw1_key = flash_info.block_names_frf[2]
        cal_key = flash_info.block_names_frf[5]
    else:
        cboot_key = flash_info.block_names_frf[1]
        asw1_key = flash_info.block_names_frf[2]
        cal_key = flash_info.block_names_frf[3]
    cboot_version = extract_cboot_version(flash_blocks[cboot_key], flash_info)
    asw_version = extract_asw_version(flash_blocks[asw1_key], flash_info)
    try:
        ecm3_addresses = extract_ecm3_addresses(
            flash_blocks[asw1_key], flash_info, False
        )
    except:
        ecm3_addresses = [0, 0]
    cal_version = extract_cal_version(flash_blocks[cal_key], flash_info)
    box_code = extract_box_code(flash_blocks[cal_key], flash_info)
    box_version = extract_box_version(flash_blocks[cal_key])
    engine_name = extract_engine_name(flash_blocks[cal_key])
    return {
        "cboot_version": cboot_version,
        "asw_version": asw_version,
        "ecm3_address_start": ecm3_addresses[0],
        "ecm3_address_end": ecm3_addresses[1],
        "cal_version": cal_version,
        "box_version": box_version,
        "box_code": box_code,
        "engine_name": engine_name,
        "allowed_boxcodes": allowed_boxcodes,
    }


def process_odx_data(odx_data: bytes):
    try:
        flash_infos = [
            simos18.s18_flash_info,
            simos1810.s1810_flash_info,
            simos184.s1841_flash_info,
            simos16.s16_flash_info,
            simos12.s12_flash_info,
            simos122.s122_flash_info,
            simos10.s10_flash_info,
            simos8.s8_flash_info,
        ]
        flash_data = None
        for flash_info in flash_infos:
            try:
                (flash_data, allowed_boxcodes) = extract_data_from_odx(
                    odx_data, flash_info
                )
                return extract_info_from_flash_blocks(
                    flash_data, flash_info, allowed_boxcodes
                )
            except:
                pass
        return None

    except:
        print(
            "Couldn't handle file, continuing with other files:",
            sys.exc_info()[0],
        )
        return None


def process_bin_file(bin_path: str):
    blocks = binfile.blocks_from_bin(bin_path, simos18.s18_flash_info)
    blocks = dict(map(lambda item: (item[0], item[1].block_bytes), blocks.items()))
    return extract_info_from_flash_blocks(blocks, simos18.s18_flash_info)


def process_frf_file(frf_file: str):
    frf_data = frf_file.read_bytes()
    odx_data = extract_odx_from_frf(frf_data)
    return process_odx_data(odx_data)


def process_directory(dir_path: str):
    frf_files = Path(dir_path).glob("*.frf")
    bin_files = Path(dir_path).glob("*.bin")
    with ProcessPoolExecutor() as executor:
        frf_files = executor.map(process_frf_file, frf_files)
    with ProcessPoolExecutor() as executor:
        bin_files = executor.map(process_bin_file, bin_files)
    return itertools.chain(frf_files, bin_files)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Parse a directory of FRF files and produce a report about the software within",
        epilog="For example, --dir Flashdaten --outfile file.csv",
    )
    parser.add_argument("--dir", type=str, help="Directory Input", required=True)
    parser.add_argument(
        "--outfile", type=str, required=True, help="CSV file name to output"
    )

    args = parser.parse_args()

    file_info = process_directory(args.dir)

    with open(args.outfile, "w", newline="") as csvfile:
        fieldnames = [
            "box_code",
            "box_version",
            "engine_name",
            "cboot_version",
            "asw_version",
            "cal_version",
            "ecm3_address_start",
            "ecm3_address_end",
            "allowed_boxcodes",
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, escapechar="\\")

        writer.writeheader()
        for info in file_info:
            if info is not None:
                writer.writerow(info)
