import argparse
import binascii
from Crypto.Cipher import AES
from pathlib import Path
import os
import xml.etree.ElementTree as ET
from lib import constants


def bits(byte):
    return (
        (byte >> 7) & 1,
        (byte >> 6) & 1,
        (byte >> 5) & 1,
        (byte >> 4) & 1,
        (byte >> 3) & 1,
        (byte >> 2) & 1,
        (byte >> 1) & 1,
        (byte) & 1,
    )


def decompress_raw_lzss10(indata, decompressed_size):
    """Decompress LZSS-compressed bytes. Returns a bytearray."""
    data = bytearray()

    it = iter(indata)

    def writebyte(b):
        data.append(b)

    def readbyte():
        return next(it)

    def readshort():
        # big-endian
        a = next(it)
        b = next(it)
        return (a << 8) | b

    def copybyte():
        data.append(next(it))

    while len(data) < decompressed_size:
        b = readbyte()
        flags = bits(b)
        for flag in flags:
            if flag == 0:
                copybyte()
            elif flag == 1:
                sh = readshort()
                count = sh >> 10
                disp = sh & 0x3FF
                for _ in range(count):
                    writebyte(data[-disp])
            else:
                raise ValueError(flag)

            if decompressed_size <= len(data):
                break
    return data


def extract_odx(odx_string, flash_info):
    key = flash_info.key
    iv = flash_info.iv
    root = ET.fromstring(odx_string)
    flashdata = root.findall("./FLASH/ECU-MEMS/ECU-MEM/MEM/FLASHDATAS/FLASHDATA")

    all_data = {}

    for data in flashdata:
        dataContent = data.findall("./DATA")[0].text
        dataId = data.get("ID")
        length = int(
            root.findall(
                "./FLASH/ECU-MEMS/ECU-MEM/MEM/DATABLOCKS/DATABLOCK/FLASHDATA-REF[@ID-REF='{}']/../SEGMENTS/SEGMENT/UNCOMPRESSED-SIZE".format(
                    dataId
                )
            )[0].text
        )
        if len(dataContent) == 2:
            # These are ERASE blocks with no data so skip them
            continue

        dataBinary = binascii.unhexlify(dataContent)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        decryptedContent = cipher.decrypt(dataBinary)
        decompressedContent = decompress_raw_lzss10(decryptedContent, length)

        all_data[data[0].text] = decompressedContent

    return all_data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Decrypt and decompress flash blocks from an ODX file using Simos18.1 or Simos12 AES keys.",
        epilog="For example, --file test.odx --outdir test",
    )
    parser.add_argument("--file", type=str, help="ODX file input", required=True)
    parser.add_argument(
        "--simos12",
        dest="simos12",
        action="store_true",
        default=False,
        help="(optional) use known Simos12 AES keys instead of Simos18.1/18.6",
    )
    parser.add_argument(
        "--simos1810",
        dest="simos1810",
        action="store_true",
        default=False,
        help="(optional) use known Simos18.10 AES keys instead of Simos18.1/18.6",
    )
    parser.add_argument(
        "--outdir",
        type=str,
        default="",
        help="(optional) output directory, otherwise files will be output to current directory",
    )

    args = parser.parse_args()

    flash_info = constants.s18_flash_info
    if args.simos12:
        flash_info = constants.s12_flash_info
    if args.simos1810:
        flash_info = constants.s1810_flash_info

    file_data = Path(args.file).read_text()

    data_blocks = extract_odx(file_data, flash_info)
    for data_block in data_blocks:
        with open(os.path.join(args.outdir, data_block), "wb") as dataFile:
            dataFile.write(data_blocks[data_block])
