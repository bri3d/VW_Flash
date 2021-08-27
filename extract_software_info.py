import argparse
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import csv
import sys
from lib import constants
from lib import checksum
from lib.extract_flash import extract_flash_from_frf
from pathlib import Path


def extract_cboot_version(flash_data: bytes, flash_info: constants.FlashInfo):
    start_address = flash_info.software_version_location[1][0]
    end_address = flash_info.software_version_location[1][1]
    return flash_data[start_address:end_address].decode("US-ASCII")


def extract_cboot_filename(flash_data: bytes, flash_info: constants.FlashInfo):
    start_address = flash_info.software_version_location[1][0]
    end_address = flash_info.software_version_location[1][1]
    return flash_data[start_address:end_address].decode("US-ASCII")[3:5]


def extract_asw_version(flash_data: bytes, flash_info: constants.FlashInfo):
    start_address = flash_info.software_version_location[2][0]
    end_address = flash_info.software_version_location[2][1]
    return flash_data[start_address:end_address].decode("US-ASCII")


def extract_ecm3_addresses(
    flash_data: bytes, flash_info: constants.FlashInfo, is_early: bool
):
    return checksum.locate_ecm3_with_asw1(flash_info, flash_data, is_early)


def extract_cal_version(flash_data: bytes, flash_info: constants.FlashInfo):
    start_address = flash_info.software_version_location[5][0]
    end_address = flash_info.software_version_location[5][1]
    return flash_data[start_address:end_address].decode("US-ASCII")


def extract_box_code(flash_data: bytes, flash_info: constants.FlashInfo):
    start_address = flash_info.box_code_location[5][0]
    end_address = flash_info.box_code_location[5][1]
    return flash_data[start_address:end_address].decode("US-ASCII").strip()


def extract_box_version(flash_data: bytes):
    start_address = 0x80
    end_address = 0x84
    return flash_data[start_address:end_address].decode("US-ASCII")


def extract_engine_name(flash_data: bytes):
    start_address = 0x6C
    end_address = 0x78
    return flash_data[start_address:end_address].decode("US-ASCII")


def extract_info_from_flash_blocks(flash_blocks: dict):
    if "FD_01DATA" in flash_blocks:
        flash_info = constants.s1810_flash_info
        cboot_key = "FD_01DATA"
        asw1_key = "FD_02DATA"
        cal_key = "FD_05DATA"
    else:
        flash_info = constants.s18_flash_info
        cboot_key = "FD_0"
        asw1_key = "FD_1"
        cal_key = "FD_4"

    cboot_version = extract_cboot_version(flash_blocks[cboot_key], flash_info)
    asw_version = extract_asw_version(flash_blocks[asw1_key], flash_info)
    ecm3_addresses = extract_ecm3_addresses(flash_blocks[asw1_key], flash_info, False)
    cal_version = extract_cal_version(flash_blocks[cal_key], flash_info)
    box_code = extract_box_code(flash_blocks[cal_key], flash_info)
    box_version = extract_box_version(flash_blocks[cal_key])
    engine_name = extract_engine_name(flash_blocks[cal_key])
    cboot_filename = extract_cboot_filename(flash_blocks[cboot_key], flash_info)
    cboot_file = open(cboot_filename + "_CBOOT.bin", "wb")
    cboot_file.write(flash_blocks[cboot_key])
    cboot_file.close()
    return {
        "cboot_version": cboot_version,
        "asw_version": asw_version,
        "ecm3_address_start": ecm3_addresses[0],
        "ecm3_address_end": ecm3_addresses[1],
        "cal_version": cal_version,
        "box_version": box_version,
        "box_code": box_code,
        "engine_name": engine_name,
    }


def process_frf_file(frf_file: Path):
    try:
        frf_data = frf_file.read_bytes()
        flash_data = extract_flash_from_frf(frf_data)
        return extract_info_from_flash_blocks(flash_data)
    except:
        print(
            "Couldn't handle file, continuing with other files:",
            sys.exc_info()[0],
            frf_file,
        )
        return {"box_code": str(frf_file)}


def process_directory(dir_path: str):
    frf_files = Path(dir_path).glob("*.frf")
    with ProcessPoolExecutor() as executor:
        return executor.map(process_frf_file, frf_files)


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
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for info in file_info:
            writer.writerow(info)
