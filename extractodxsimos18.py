import xml.etree.ElementTree as ET
from Crypto.Cipher import AES
import binascii
import sys

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

key = binascii.unhexlify('98D31202E48E3854F2CA561545BA6F2F')
iv = binascii.unhexlify('E7861278C508532798BCA4FE451D20D1')
tree = ET.parse(sys.argv[1])
root = tree.getroot()
flashdata = root.findall('./FLASH/ECU-MEMS/ECU-MEM/MEM/FLASHDATAS/FLASHDATA')
fulldata = bytearray()
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

    fulldata.extend(decompressedContent)

    with open(data[0].text, 'wb') as dataFile:
        dataFile.write(decompressedContent)

with open("{}.bin".format(sys.argv[1]), 'wb') as fullDataFile:
    fullDataFile.write(fulldata)