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

int_to_block_name = dict((reversed(item) for item in block_name_to_int.items()))

block_lengths = {
  1: 0x23e00, # CBOOT
  2: 0xffc00, # ASW1
  3: 0xbfc00, # ASW2
  4: 0x7fc00, # ASW3
  5: 0x7fc00 # CAL
}


