from sys import argv
from zipfile import ZipFile
import argparse
import io
import os

parser = argparse.ArgumentParser(description='Decrypt and decompress FRF file.', epilog="For example, --file test.frf --outdir test")
parser.add_argument('--file', type=str,
                    help='FRF file input',
                    required=True)
parser.add_argument('--outdir', type=str, default="",
                    help='(optional) output directory, otherwise files will be output to current directory')

args = parser.parse_args()

__location__ = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__)))

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

key_file = open(os.path.join(__location__, "frf.key"), "rb")
key_material = key_file.read()

encrypted_file = open(args.file, "rb")
encrypted_data = encrypted_file.read()

decrypted_data = decrypt_data(key_material, encrypted_data)

zf = ZipFile(io.BytesIO(decrypted_data), "r")
for fileinfo in zf.infolist():
    out_file = open(os.path.join(args.outdir, fileinfo.filename), "wb")
    out_file.write(zf.read(fileinfo))
    out_file.close()

key_file.close()
encrypted_file.close()
