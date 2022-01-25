import struct


def fill_bits(count):
    num = 0
    for i in range(count):
        num |= 1 << i
    return num


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
