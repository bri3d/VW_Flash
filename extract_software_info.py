import argparse
import csv
import io
import struct
import zipfile
from lib import constants
from pathlib import Path
from frf import decryptfrf
import extractodxsimos18


def extract_cboot_version(flash_data: bytes):
    start_address = constants.software_version_location[1][0]
    end_address = constants.software_version_location[1][1]
    return flash_data[start_address:end_address].decode("US-ASCII")


def extract_asw_version(flash_data: bytes):
    start_address = constants.software_version_location[2][0]
    end_address = constants.software_version_location[2][1]
    return flash_data[start_address:end_address].decode("US-ASCII")


def extract_ecm3_addresses(
    flash_data: bytes, flash_info: constants.FlashInfo, is_early: bool
):
    addresses = []
    checksum_address_location = (
        constants.ecm3_cal_monitor_addresses_early
        if is_early
        else constants.ecm3_cal_monitor_addresses
    )
    base_address = flash_info.base_addresses[constants.block_name_to_int["CAL"]]
    checksum_area_count = 1
    for i in range(0, checksum_area_count * 2):
        address = struct.unpack(
            "<I",
            flash_data[
                checksum_address_location
                + (i * 4) : checksum_address_location
                + 4
                + (i * 4)
            ],
        )

        offset_correction = (
            constants.ecm3_cal_monitor_offset_early
            if is_early
            else constants.ecm3_cal_monitor_offset
        )
        offset = address[0] + offset_correction - base_address

        addresses.append(offset)
    return addresses


def extract_cal_version(flash_data: bytes):
    start_address = constants.software_version_location[5][0]
    end_address = constants.software_version_location[5][1]
    return flash_data[start_address:end_address].decode("US-ASCII")


def extract_box_code(flash_data: bytes):
    start_address = constants.box_code_location[5][0]
    end_address = constants.box_code_location[5][1]
    return flash_data[start_address:end_address].decode("US-ASCII")


def extract_box_version(flash_data: bytes):
    start_address = 0x80
    end_address = 0x84
    return flash_data[start_address:end_address].decode("US-ASCII")


def extract_engine_name(flash_data: bytes):
    start_address = 0x6C
    end_address = 0x78
    return flash_data[start_address:end_address].decode("US-ASCII")


def extract_info_from_flash_blocks(flash_blocks: dict):
    flash_info = constants.s18_flash_info
    cboot_version = extract_cboot_version(flash_blocks["FD_0"])
    asw_version = extract_asw_version(flash_blocks["FD_1"])
    ecm3_addresses = extract_ecm3_addresses(flash_blocks["FD_1"], flash_info, False)
    if ecm3_addresses[0] < 0:
        ecm3_addresses = extract_ecm3_addresses(flash_blocks["FD_1"], flash_info, True)
    cal_version = extract_cal_version(flash_blocks["FD_4"])
    box_code = extract_box_code(flash_blocks["FD_4"])
    box_version = extract_box_version(flash_blocks["FD_4"])
    engine_name = extract_engine_name(flash_blocks["FD_4"])
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


def extract_flash_from_frf(frf_data: bytes):
    decrypted_frf = decryptfrf.decrypt_data(decryptfrf.read_key_material(), frf_data)
    zf = zipfile.ZipFile(io.BytesIO(decrypted_frf), "r")

    for fileinfo in zf.infolist():
        with zf.open(fileinfo) as odxfile:
            return extractodxsimos18.extract_odx(
                odxfile.read(), constants.s18_flash_info
            )


def process_frf_file(frf_file: Path):
    try:
        frf_data = frf_file.read_bytes()
        flash_data = extract_flash_from_frf(frf_data)
        return extract_info_from_flash_blocks(flash_data)
    except:
        return {"box_code": str(frf_file)}


def process_directory(dir_path: str):
    frf_files = Path(dir_path).glob("*.frf")
    return map(lambda frf_file: process_frf_file(frf_file), frf_files)


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
