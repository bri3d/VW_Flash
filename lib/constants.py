from enum import Enum

class ChecksumState(Enum):
   VALID_CHECKSUM = 1
   INVALID_CHECKSUM = 2
   FIXED_CHECKSUM = 3


#The location of each checksum in the bin
checksum_block_location = {
   0: 0x300, # SBOOT
   1: 0x300, # CBOOT
   2: 0x300, # ASW1
   3: 0x0, # ASW2
   4: 0x0, # ASW3
   5: 0x300, # CAL
   6: 0x340 # CBOOT_temp
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
   5: 0xA0800000, # CAL
   6: 0x80840000 # CBOOT_temp
}

#Conversion dict for block name to number
block_name_to_int = {
  'CBOOT': 1,
  'ASW1' : 2,
  'ASW2' : 3,
  'ASW3' : 4,
  'CAL' : 5,
  'CBOOT_TEMP': 6,
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
  5: 0x7fc00, # CAL
  6: 0x23e00 # CBOOT_temp
}
s18_key = bytes.fromhex('98D31202E48E3854F2CA561545BA6F2F')
s18_iv = bytes.fromhex('E7861278C508532798BCA4FE451D20D1')

s12_iv = bytes.fromhex('306e37426b6b536f316d4a6974366d34')
s12_key = bytes.fromhex('314d7536416e3047396a413252356f45')

int_to_block_name = dict((reversed(item) for item in block_name_to_int.items()))

def block_to_number(blockname: str) -> int:
  if blockname.isdigit():
    return int(blockname)
  else:
    return block_name_to_int[blockname.upper()]


