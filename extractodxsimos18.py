import argparse
import binascii
from Crypto.Cipher import AES
import os
import xml.etree.ElementTree as ET
from lib import constants

parser = argparse.ArgumentParser(description='Decrypt and decompress flash blocks from an ODX file using Simos18.1 or Simos12 AES keys.', epilog="For example, --file test.odx --outdir test")
parser.add_argument('--file', type=str,
                    help='ODX file input',
                    required=True)
parser.add_argument('--simos12', dest='simos12', action='store_true', default=False,
                    help='(optional) use known Simos12 AES keys instead of Simos18.1')
parser.add_argument('--outdir', type=str, default="",
                    help='(optional) output directory, otherwise files will be output to current directory')

args = parser.parse_args()

def bits(byte):
    return ((byte >> 7) & 1,
            (byte >> 6) & 1,
            (byte >> 5) & 1,
            (byte >> 4) & 1,
            (byte >> 3) & 1,
            (byte >> 2) & 1,
            (byte >> 1) & 1,
            (byte) & 1)

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
                count = (sh >> 10)
                disp = (sh & 0x3ff)
                for _ in range(count):
                    writebyte(data[-disp])
            else:
                raise ValueError(flag)

            if decompressed_size <= len(data):
                break
    return data

key = constants.s18_key
iv = constants.s18_iv

if args.simos12:
    key = constants.s12_key
    iv = constants.s12_iv

tree = ET.parse(args.file)
root = tree.getroot()
flashdata = root.findall('./FLASH/ECU-MEMS/ECU-MEM/MEM/FLASHDATAS/FLASHDATA')

for data in flashdata:
    dataContent = data.findall('./DATA')[0].text
    dataId = data.get('ID')
    length = int(root.findall("./FLASH/ECU-MEMS/ECU-MEM/MEM/DATABLOCKS/DATABLOCK/FLASHDATA-REF[@ID-REF='{}']/../SEGMENTS/SEGMENT/UNCOMPRESSED-SIZE".format(dataId))[0].text)
    if len(dataContent) == 2:
        # These are ERASE blocks with no data so skip them
        continue
    
    dataBinary = binascii.unhexlify(dataContent)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    decryptedContent = cipher.decrypt(dataBinary)
    decompressedContent = decompress_raw_lzss10(decryptedContent, length)

    with open(os.path.join(args.outdir, data[0].text), 'wb') as dataFile:
        dataFile.write(decompressedContent)
