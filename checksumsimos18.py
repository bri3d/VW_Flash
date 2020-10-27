import sys, getopt
import binascii
import zlib
import struct

checksum_block_location = {
   1: 0x300, # CBOOT
   2: 0x300, # ASW1
   3: 0x0, # ASW2
   4: 0x0, # ASW3
   5: 0x300 # CAL
}

base_addresses = {
   1: 0x8001C000, # CBOOT
   2: 0x80040000, # ASW1
   3: 0x80140000, # ASW2
   4: 0x80880000, # ASW3
   5: 0xA0800000 # CAL
}

def main(argv):
   inputfile = ''
   outputfile = ''
   try:
      opts, args = getopt.getopt(argv,"hi:o:b:",["ifile=","ofile=","blocknum="])
   except getopt.GetoptError:
      print('checksumsimos18.py -i <inputfile> -o <outputfile>')
      sys.exit(2)
   for opt, arg in opts:
      if opt == '-h':
         print('checksumsimos18.py -i <inputfile> -o <outputfile>')
         sys.exit()
      elif opt in ("-i", "--ifile"):
         inputfile = arg
      elif opt in ("-o", "--ofile"):
         outputfile = arg
      elif opt in ("-b", "--blocknum"):
         blocknum = int(arg)

   print("Checksumming " + inputfile + " to " + outputfile)
   f = open(inputfile, "rb")
   data_binary = f.read()

   checksum_location = checksum_block_location[blocknum]

   current_checksum = struct.unpack("<I", data_binary[checksum_location+4:checksum_location+8])[0]
   checksum_area_count = data_binary[checksum_location+8]
   base_address = base_addresses[blocknum]
   
   addresses = []
   for i in range(0, checksum_area_count * 2):
      address = struct.unpack('<I', data_binary[checksum_location+12+(i*4):checksum_location+16+(i*4)])
      offset = address[0] - base_address
      addresses.append(offset)
   checksum_data = bytearray()
   for i in range (0, len(addresses), 2):
      start_address = int(addresses[i])
      end_address = int(addresses[i+1])
      print("Adding " + hex(start_address) + ":" + hex(end_address))
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
   print("Checksum = " + hex(checksum))
   if(checksum == current_checksum):
      print("File is valid!")
   else:
      print("File is invalid! File checksum: " + hex(current_checksum) + " does not match " + hex(checksum))
      if(len(outputfile) > 0):
         with open(outputfile, 'wb') as fullDataFile:
            data_binary = bytearray(data_binary)
            data_binary[checksum_location+4:checksum_location+8] = struct.pack('<I', checksum)
            fullDataFile.write(data_binary)
   

if __name__ == "__main__":
   main(sys.argv[1:])
