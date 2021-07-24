from sys import argv
from zipfile import ZipFile
import argparse
import io
import os

# Implements a goofy "recursive xor" cypher used to encrypt FRF files, which at the end of the day are ZIP files containing either SGO (binary flash data) or ODX data.
def decrypt_data(key_material: bytes, encrypted_data: bytes):
    output_data = bytearray()
    key_index = 0
    first_seed = 0
    second_seed = 1
    for data_byte in encrypted_data:
        key_byte = key_material[key_index]
        first_seed = ((first_seed + key_byte) * 3) & 0xFF
        decrypted_byte = data_byte ^ (first_seed ^ 0xFF ^ second_seed ^ key_byte)
        output_data.append(decrypted_byte)
        second_seed = ((second_seed + 1) * first_seed) & 0xFF
        key_index += 1
        key_index %= len(key_material)
    return output_data


def read_key_material():
    key_data = []

    def key_material_reader():
        if len(key_data) == 0:
            __location__ = os.path.realpath(
                os.path.join(os.getcwd(), os.path.dirname(__file__))
            )
            key_file = open(os.path.join(__location__, "frf.key"), "rb")
            key_data.append(key_file.read())
            key_file.close()
        return key_data[0]

    return key_material_reader()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Decrypt and decompress FRF file.",
        epilog="For example, --file test.frf --outdir test",
    )
    parser.add_argument("--file", type=str, help="FRF file input", required=True)
    parser.add_argument(
        "--outdir",
        type=str,
        default="",
        help="(optional) output directory, otherwise files will be output to current directory",
    )

    args = parser.parse_args()

    key_material = read_key_material()

    encrypted_file = open(args.file, "rb")
    encrypted_data = encrypted_file.read()

    decrypted_data = decrypt_data(key_material, encrypted_data)

    zf = ZipFile(io.BytesIO(decrypted_data), "r")
    for fileinfo in zf.infolist():
        zf.extract(fileinfo, args.outdir)

    encrypted_file.close()
