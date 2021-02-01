import sys, getopt
import binascii
import zlib
import struct
import logging
from enum import Enum

import lib.constants as constants

rootLogger = logging.getLogger()

checksum = None
checksum_location = None

def validate(simos12 = False, data_binary = None, blocknum = 5, loglevel = logging.INFO):
   global checksum
   global checksum_location
   rootLogger.setLevel(loglevel)
   rootLogger.debug("Performing Checksum")

   checksum_location = constants.checksum_block_location[blocknum]

   current_checksum = struct.unpack("<I", data_binary[checksum_location+4:checksum_location+8])[0]
   checksum_area_count = data_binary[checksum_location+8]
   base_address = constants.base_addresses_s12[blocknum] if simos12 else constants.base_addresses[blocknum] 
   
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
      return constants.ChecksumState.VALID_CHECKSUM

   else:
      rootLogger.debug("File is invalid! File checksum: " + hex(current_checksum) + " does not match " + hex(checksum))
      return constants.ChecksumState.INVALID_CHECKSUM
 
def fix(simos12 = False, data_binary = None, blocknum = 5, loglevel = logging.INFO):
   global checksum
   global checksum_location
   rootLogger.setLevel(loglevel)
   result = validate(simos12 = simos12, data_binary = data_binary, blocknum = blocknum, loglevel = loglevel)

   if result == constants.ChecksumState.VALID_CHECKSUM:
      rootLogger.debug("Checksum in binary already valid")

   elif checksum is not None and checksum_location is not None:
      data_binary = bytearray(data_binary)
      data_binary[checksum_location+4:checksum_location+8] = struct.pack('<I', checksum)     
      rootLogger.debug("Fixed checksum in binary")

   else:
      return constants.ChecksumState.FAILED_ACTION

   return data_binary

  
