
import struct
import logging

from . import fastcrc
from enum import Enum

from . import constants 

logger = logging.getLogger('Checksum')

checksum = None
checksum_location = None

def validate(simos12 = False, data_binary = None, blocknum = 5):
   global checksum
   global checksum_location

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
      logger.debug("Adding " + hex(start_address) + ":" + hex(end_address))
      checksum_data += data_binary[start_address:end_address+1]

   # The CRC checksum algorithm used in Simos is 32-bit, 0x4C11DB7 polynomial, 0x0 initial value, 0x0 ending xor.
   # Please see fastcrc.py for a reference bitwise reference implementation as well as the generated fast tabular implementation.

   checksum = fastcrc.crc_32_fast(checksum_data)
   logger.debug("Checksum = " + hex(checksum))

   if(checksum == current_checksum):
      logger.info("File is valid!")
      return constants.ChecksumState.VALID_CHECKSUM

   else:
      logger.warning("File is invalid! File checksum: " + hex(current_checksum) + " does not match " + hex(checksum))
      return constants.ChecksumState.INVALID_CHECKSUM
 
def fix(simos12 = False, data_binary = None, blocknum = 5):
   global checksum
   global checksum_location

   result = validate(simos12 = simos12, data_binary = data_binary, blocknum = blocknum)

   if result == constants.ChecksumState.VALID_CHECKSUM:
      logger.info("Binary not fixed: checksum in binary already valid")

   elif checksum is not None and checksum_location is not None:
      data_binary = bytearray(data_binary)
      data_binary[checksum_location+4:checksum_location+8] = struct.pack('<I', checksum)
      logger.info("Fixed checksum in binary")

   else:
      return constants.ChecksumState.FAILED_ACTION

   return data_binary

  
