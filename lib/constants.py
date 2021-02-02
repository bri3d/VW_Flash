from enum import Enum
from typing import List
from sa2_seed_key.sa2_seed_key import Sa2SeedKey

class ChecksumState(Enum):
   VALID_CHECKSUM = 1
   INVALID_CHECKSUM = 2
   FIXED_CHECKSUM = 3
   FAILED_ACTION = 4

class DataRecord:
   address: int
   parse_type: int
   description:  str
   def __init__(self, address, parse_type, description):
      self.address = address
      self.parse_type = parse_type
      self.description = description
 
#The location of each checksum in the bin
checksum_block_location = {
   0: 0x300, # SBOOT
   1: 0x300, # CBOOT
   2: 0x300, # ASW1
   3: 0x0, # ASW2
   4: 0x0, # ASW3
   5: 0x300 # CAL
}

software_version_location = {
   1: [0x437, 0x43f],
   2: [0x627, 0x62f],
   3: [0x203, 0x20b],
   4: [0x203, 0x20b],
   5: [0x23, 0x2b],
   9: [0,0]
}

#The base address of each block on simos12
base_addresses_s12 = {
   0: 0x80000000, # SBOOT
   1: 0x80020000, # CBOOT
   2: 0x800C0000, # ASW1
   3: 0x80180000, # ASW2
   4: 0x80240000, # ASW3
   5: 0xA0040000 # CAL
}

#The base address of each block
base_addresses = {
   0: 0x80000000, # SBOOT
   1: 0x8001C000, # CBOOT
   2: 0x80040000, # ASW1
   3: 0x80140000, # ASW2
   4: 0x80880000, # ASW3
   5: 0xA0800000 # CAL
}

#Conversion dict for block name to number
block_name_to_int = {
  'CBOOT': 1,
  'ASW1' : 2,
  'ASW2' : 3,
  'ASW3' : 4,
  'CAL' : 5,
  'PATCH_ASW1': 7,
  'PATCH_ASW2': 8,
  'PATCH_ASW3': 9
}


#The size of each block
block_lengths = {
  1: 0x23e00, # CBOOT
  2: 0xffc00, # ASW1
  3: 0xbfc00, # ASW2
  4: 0x7fc00, # ASW3
  5: 0x7fc00 # CAL
}



# We can send the maximum allowable size worth of compressed data in an ISO-TP request when we are using the "normal" TransferData system.
block_transfer_sizes = {
  1: 0xFFD,
  2: 0xFFD,
  3: 0xFFD,
  4: 0xFFD,
  5: 0xFFD
}

s18_key = bytes.fromhex('98D31202E48E3854F2CA561545BA6F2F')
s18_iv = bytes.fromhex('E7861278C508532798BCA4FE451D20D1')

s12_iv = bytes.fromhex('306e37426b6b536f316d4a6974366d34')
s12_key = bytes.fromhex('314d7536416e3047396a413252356f45')

int_to_block_name = dict((reversed(item) for item in block_name_to_int.items()))

def block_to_number(blockname: str) -> int:
  if blockname.isdigit():
    return blockname
  else:
    return block_name_to_int[blockname.upper()]

def volkswagen_security_algo(level: int, seed: bytes, params=None) -> bytes:
  simos18_sa2_script = bytearray([0x68, 0x02, 0x81, 0x4A, 0x10, 0x68, 0x04, 0x93, 0x08, 0x08, 0x20, 0x09, 0x4A, 0x05, 0x87, 0x22, 0x12, 0x19, 0x54, 0x82, 0x49, 0x93, 0x07, 0x12, 0x20, 0x11, 0x82, 0x4A, 0x05, 0x87, 0x03, 0x11, 0x20, 0x10, 0x82, 0x4A, 0x01, 0x81, 0x49, 0x4C])
  vs = Sa2SeedKey(simos18_sa2_script, int.from_bytes(seed, "big"))
  return vs.execute().to_bytes(4, 'big')

data_records : List[DataRecord] = [
 DataRecord(0xF190, 0, "VIN Vehicle Identification Number"),
 DataRecord(0xF19E, 0, "ASAM/ODX File Identifier"),
 DataRecord(0xF1A2, 0, "ASAM/ODX File Version"),
 DataRecord(0xF40D, 1, "Vehicle Speed"),
 DataRecord(0xF806, 1, "Calibration Verification Numbers"),
 DataRecord(0xF187, 0, "VW Spare Part Number"),
 DataRecord(0xF189, 0, "VW Application Software Version Number"),
 DataRecord(0xF191, 0, "VW ECU Hardware Number"),
 DataRecord(0xF1A3, 0, "VW ECU Hardware Version Number"),
 DataRecord(0xF197,0,"VW System Name Or Engine Type"),
 DataRecord(0xF1AD,0,"Engine Code Letters"),
 DataRecord(0xF1AA,0,"VW Workshop System Name"),
 DataRecord(0x0405,1,"State Of Flash Memory"),
 DataRecord(0x0407,1,"VW Logical Software Block Counter Of Programming Attempts"),
 DataRecord(0x0408,1,"VW Logical Software Block Counter Of Successful Programming Attempts"),
 DataRecord(0x0600,1,"VW Coding Value"),
 DataRecord(0xF186,1,"Active Diagnostic Session"),
 DataRecord(0xF18C,0,"ECU Serial Number"),
 DataRecord(0xF17C,0,"VW FAZIT Identification String"),
 DataRecord(0xF442,1,"Control Module Voltage"),
 DataRecord(0xEF90,1,"Immobilizer Status SHE"),
 DataRecord(0xF1F4,0,"Boot Loader Identification"),
 DataRecord(0xF1DF,1,"ECU Programming Information"),
 DataRecord(0xF1F1,1,"Tuning Protection SO2"),
 DataRecord(0xF1E0,1,""),
 DataRecord(0x12FC,1,""),
 DataRecord(0x12FF,1,""),
 DataRecord(0xFD52,1,""),
 DataRecord(0xFD83,1,""),
 DataRecord(0xFDFA,1,""),
 DataRecord(0xFDFC,1,""),
 DataRecord(0x295A,1,"Vehicle Mileage"),
 DataRecord(0x295B,1,"Control Module Mileage"),
 DataRecord(0xF190,0,"VIN Vehicle Identification Number"),
 DataRecord(0xF19E,0,"ASAM/ODX File Identifier"),
 DataRecord(0xF1A2,0,"ASAM/ODX File Version"),
 DataRecord(0xF15B,1,"Fingerprint and Programming Date"),
 DataRecord(0xF191,0,"VW ECU Hardware Number"),
 DataRecord(0xF1A3,0,"VW ECU Hardware Version Number"),
 DataRecord(0xF187,0,"VW Spare Part Number"),
 DataRecord(0xF189,0,"VW Application Software Version Number"),
 DataRecord(0xF1F4,0,"Boot Loader Identification"),
 DataRecord(0xF197,0,"VW System Name Or Engine Type"),
 DataRecord(0xF1AD,0,"Engine Code Letters"),
 DataRecord(0xF17C,0,"VW FAZIT Identification String"),
 DataRecord(0xF1A5,1,"VW Coding Repair Shop Code Or Serial Number (Coding Fingerprint),"),
 DataRecord(0x0405,1,"State Of Flash Memory"),
 DataRecord(0xF1AB,0,"VW Logical Software Block Version"),
 DataRecord(0xF804,0,"Calibration ID"),
 DataRecord(0xF17E,0,"ECU Production Change Number")
]




# When we're performing WriteWithoutErase, we need to write 8 bytes at a time in "patch areas" to allow the ECC operation to be performed correctly across the patched data.
# But, when we're just "writing" 0s (which we can't actually do), we can go faster and fill an entire 256-byte Assembly Page in the flash controller as ECC will not work anyway.
# Internally, we're basically stuffing the Assembly Page for the flash controller and the method return does not wait for controller readiness, so we will also need to resend data repeatedly.
def block_transfer_sizes_patch(block_number: int, address: int) -> int:
  if(block_number != 4):
    print("Only patching H__0001's Block 4 / ASW3 using a provided patch is supported at this time! If you have a patch for another block, please fill in its data areas here.")
    exit()
  if(address < 0x95FF):
    return 0x100
  if(address >= 0x95FF and address < 0x9800):
    return 0x8
  if(address >= 0x9800 and address < 0x7DD00):
    return 0x100
  if(address >= 0x7DD00 and address < 0x7E200):
    return 0x8
  if(address >= 0x7E200):
    return 0x100
  return 0x8

