# Here we look for

# da 00           mov        d15,#0x0
# 3c 02           j          +2
# da 01           mov        d15,#0x1
# 02 f2           mov        d2,d15

# And patch it to
# 00 00           nop
# 00 00           nop
# da 01           mov        d15,#0x1
# 02 f2           mov        d2,d15

# This forces the return value of the method with this pattern to "1". If the needle worked correctly, this will only match the is_sample_mode function.

NEEDLE = "DA00 3C02 DA01 02F2"
PATCH = "00 00 00 00 DA01 02F2"


def patch_cboot(cboot_binary: bytes):
    needle_bytes = bytes.fromhex(NEEDLE)
    patch_bytes = bytes.fromhex(PATCH)
    cboot_binary = bytearray(cboot_binary)
    first_address = cboot_binary.find(needle_bytes)
    second_address = cboot_binary.find(needle_bytes, first_address + len(needle_bytes))
    third_address = cboot_binary.find(needle_bytes, second_address + len(needle_bytes))
    if third_address != -1:
        print("Too many matches")
        return cboot_binary
    else:
        cboot_binary[first_address : first_address + len(needle_bytes)] = patch_bytes
        cboot_binary[second_address : second_address + len(needle_bytes)] = patch_bytes
        return bytes(cboot_binary)
