import sys, getopt
import binascii
import zlib
import struct
import logging

rootLogger = logging.getLogger()
rootLogger.setLevel(logging.DEBUG)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
rootLogger.addHandler(handler)


checksum_block_location = {
   0: 0x300, # SBOOT
   1: 0x300, # CBOOT
   2: 0x300, # ASW1
   3: 0x0, # ASW2
   4: 0x0, # ASW3
   5: 0x300 # CAL
}

base_addresses_s12 = {
   0: 0x80000000, # SBOOT
   1: 0x80020000, # CBOOT
   2: 0x800C0000, # ASW1
   3: 0x80180000, # ASW2
   4: 0x80240000, # ASW3
   5: 0xA0040000 # CAL
}

base_addresses = {
   0: 0x80000000, # SBOOT
   1: 0x8001C000, # CBOOT
   2: 0x80040000, # ASW1
   3: 0x80140000, # ASW2
   4: 0x80880000, # ASW3
   5: 0xA0800000 # CAL
}

def main(simos12 = False, inputfile = '', outputfile = '', blocknum = 5, loglevel = logging.DEBUG):
   rootLogger.setLevel(loglevel)
   result = []

   rootLogger.debug("Checksumming " + inputfile + " to " + outputfile)
   f = open(inputfile, "rb")
   data_binary = f.read()

   checksum_location = checksum_block_location[blocknum]

   current_checksum = struct.unpack("<I", data_binary[checksum_location+4:checksum_location+8])[0]
   checksum_area_count = data_binary[checksum_location+8]
   base_address = base_addresses_s12[blocknum] if simos12 else base_addresses[blocknum] 
   
   addresses = []
   for i in range(0, checksum_area_count * 2):
      address = struct.unpack('<I', data_binary[checksum_location+12+(i*4):checksum_location+16+(i*4)])
      offset = address[0] - base_address
      addresses.append(offset)
   checksum_data = bytearray()
   for i in range (0, len(addresses), 2):
      start_address = int(addresses[i])
      end_address = int(addresses[i+1])
      rootLogger.debug("Adding " + hex(start_address) + ":" + hex(end_address))
      checksum_data += data_binary[start_address:end_address+1]
   
   def crc32(data):
     poly = 0x4c11db7
     crc = 0x00000000
     for byte in data:
         for bit in range(7,-1,-1):  # MSB to LSB
             z32 = crc>>31    # top bit
             crc = crc << 1
             if ((byte>>bit)&1) ^ z32:
                 crc = crc ^ poly
             crc = crc & 0xffffffff
     return crc
   checksum = crc32(checksum_data)
   rootLogger.debug("Checksum = " + hex(checksum))

   if(checksum == current_checksum):
      rootLogger.debug("File is valid!")
      return [True, "File is valid!"]
   else:
      rootLogger.debug("File is invalid! File checksum: " + hex(current_checksum) + " does not match " + hex(checksum))
      if(len(outputfile) > 0):
         with open(outputfile, 'wb') as fullDataFile:
            data_binary = bytearray(data_binary)
            data_binary[checksum_location+4:checksum_location+8] = struct.pack('<I', checksum)
            fullDataFile.write(data_binary)
         rootLogger.debug("Fixed checksums and wrote to : " + outputfile)
         return [True, "Fixed checksums and wrote to: " + outputfile]
      else:
         return [False, "File checksum is invalid!"]
   
