def convert_to_bcd(decimal):
    place, bcd = 0, 0
    while decimal > 0:
        nibble = int(decimal % 10)
        bcd += nibble << place
        decimal /= 10
        place += 4
    return bcd


def convert_from_bcd(hex):
    hex = hex.to_bytes(4, "big")
    result = 0
    for byte in hex:
        result = result * 100 + (byte >> 4) * 10 + (byte & 15)
    return result
