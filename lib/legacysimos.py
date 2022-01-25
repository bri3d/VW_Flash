import struct

# This is one of the silliest "encryption" methods I have ever seen.
# The code for this amazing algorithm was discovered at 80017168 in 03F906070AK.
# It could also have been found easily through some basic cryptanalysis.


def decrypt(data: bytes):
    output_data = bytearray()
    counter = 0
    for data_byte in data:
        if counter == 256:
            counter = 0
        output_data.append(data_byte ^ counter)
        counter += 1
    return bytes(output_data)


def encrypt(data):
    return decrypt(data)


def fill_bits(count):
    num = 0
    for i in range(count):
        num |= 1 << i
    return num


# I don't know what to call this compression algorithm, it's a weird LZ type thing.


def decompress(data: bytes):
    signifier = data[0]
    block_size = struct.unpack(">L", data[3:7])[0]
    count = struct.unpack(">H", data[1:3])[0]
    output_cursor = 0
    offset_size = int(data[1])
    dict_size = fill_bits(int(data[2]))
    output = bytearray(block_size)
    cursor = 11
    while cursor < len(data):
        if data[cursor] == signifier:
            cursor += 1
            offset_and_len = struct.unpack(">H", data[cursor : cursor + 2])[0]
            cursor += 2
            offset = offset_and_len >> (16 - offset_size)
            length = offset_and_len & dict_size
            block_offset = output_cursor
            for i in range(0, length):
                output[output_cursor] = output[block_offset - offset + i]
                output_cursor += 1
            output[output_cursor] = data[cursor]
            cursor += 1
            output_cursor += 1
        else:
            output[output_cursor] = data[cursor]
            cursor += 1
            output_cursor += 1
    return output
