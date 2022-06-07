import argparse
import binascii
from lib import legacysimos
from pathlib import Path
import os
import xml.etree.ElementTree as ET

from lib import constants
from lib.modules import (
    simos8,
    simos10,
    simos12,
    simos18,
    simos1810,
    simos184,
    dq250mqb,
    simos16,
    simos122,
    dq381,
)


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


def extract_odx(odx_string, flash_info: constants.FlashInfo, is_dsg=False):
    root = ET.fromstring(odx_string)
    flashdata = root.findall("./FLASH/ECU-MEMS/ECU-MEM/MEM/FLASHDATAS/FLASHDATA")

    boxcodes = root.findall(
        "./FLASH/ECU-MEMS/ECU-MEM/MEM/SESSIONS/SESSION/EXPECTED-IDENTS/EXPECTED-IDENT/IDENT-VALUES/IDENT-VALUE"
    )

    all_data = {}

    allowed_boxcodes = []
    for boxcode in boxcodes:
        allowed_boxcodes.append(boxcode.text.rstrip())

    for data in flashdata:
        dataContent = data.findall("./DATA")[0].text
        encryptionCompressionType = data.findall("./ENCRYPT-COMPRESS-METHOD")[0].text
        compressionType = encryptionCompressionType[0]
        encryptionType = encryptionCompressionType[1]
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

        if encryptionType == "0":
            decryptedContent = dataBinary
        else:
            decryptedContent = flash_info.crypto.decrypt(dataBinary)

        if compressionType == "A" or is_dsg:
            decompressedContent = decompress_raw_lzss10(decryptedContent, length)
        elif compressionType == "1":
            decompressedContent = legacysimos.decompress(decryptedContent)
        else:
            decompressedContent = decryptedContent

        all_data[data[0].text] = decompressedContent

    return (all_data, allowed_boxcodes)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Decrypt and decompress flash blocks from an ODX file using Simos18.1 or Simos12 AES keys.",
        epilog="For example, --file test.odx --outdir test",
    )
    parser.add_argument("--file", type=str, help="ODX file input", required=True)

    parser.add_argument(
        "--simos8",
        dest="simos8",
        action="store_true",
        default=False,
        help="(optional) use Simos8 compression",
    )

    parser.add_argument(
        "--simos10",
        dest="simos10",
        action="store_true",
        default=False,
        help="(optional) use Simos10 XOR encryption and compression",
    )

    parser.add_argument(
        "--simos1810",
        dest="simos1810",
        action="store_true",
        default=False,
        help="(optional) use known Simos18.10 AES keys instead of Simos18.1/18.6",
    )
    parser.add_argument(
        "--simos1841",
        dest="simos1841",
        action="store_true",
        default=False,
        help="(optional) use known Simos18.41 AES keys instead of Simos18.1/18.6",
    )
    parser.add_argument(
        "--simos122",
        dest="simos122",
        action="store_true",
        default=False,
        help="(optional) use known Simos12.2 AES keys instead of Simos18.1/18.6",
    )
    parser.add_argument(
        "--simos16",
        dest="simos16",
        action="store_true",
        default=False,
        help="(optional) use known Simos16 AES keys instead of Simos18.1/18.6",
    )
    parser.add_argument(
        "--dsg",
        dest="dsg",
        action="store_true",
        default=False,
        help="(optional) use DSG decryption algorithm",
    )
    parser.add_argument(
        "--dq381",
        dest="dq381",
        action="store_true",
        default=False,
        help="(optional) use DSG decryption algorithm",
    )

    parser.add_argument(
        "--outdir",
        type=str,
        default="",
        help="(optional) output directory, otherwise files will be output to current directory",
    )

    args = parser.parse_args()

    flash_info = simos18.s18_flash_info
    if args.simos122:
        flash_info = simos122.s122_flash_info
    if args.simos1810:
        flash_info = simos1810.s1810_flash_info
    if args.simos1841:
        flash_info = simos184.s1841_flash_info
    if args.simos16:
        flash_info = simos16.s16_flash_info
    if args.simos10:
        flash_info = simos10.s10_flash_info
    if args.simos8:
        flash_info = simos8.s8_flash_info
    if args.dq381:
        flash_info = dq381.dsg_flash_info
    if args.dsg:
        flash_info = dq250mqb.dsg_flash_info

    file_data = Path(args.file).read_text()

    (data_blocks, allowed_boxcodes) = extract_odx(file_data, flash_info, args.dsg)
    for data_block in data_blocks:
        print(data_block)
        with open(os.path.join(args.outdir, data_block), "wb") as dataFile:
            dataFile.write(data_blocks[data_block])
