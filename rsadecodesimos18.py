import asn1
from Crypto.PublicKey.RSA import construct
from sys import argv
import sys
import binascii
import struct

# Simos18.1 VW AG first public key (extracted from OTP)

e = 65537
n = int.from_bytes(bytes.fromhex('2B C4 4D 61 35 D0 13 43 FB 6D DE 5D 61 AD 32 8E 57 73 05 90 D1 23 BA 5D 36 93 25 21 03 E2 8A 76 8E 11 18 2C C7 EA 44 7A BE 95 3A 47 05 11 5A 66 B2 75 D6 B3 98 04 CB D3 FE E4 34 C6 65 C1 C0 50 37 3A 3F 42 04 D9 0A B0 E6 B2 39 23 84 4E 5C 49 47 C0 B3 41 C1 70 BF 93 BF 8C 00 77 AD B6 D2 82 DF 3E 8A 80 E4 33 E4 A2 F8 8F 10 0D CD 6A D9 AC DA 97 50 49 E0 8C 84 68 96 24 F1 7A 02 C7 69 18 40 9C 5A 03 18 90 20 BA 44 AA 4D 76 77 DC 2A 35 13 3B 7D 91 7C 63 FB DB 73 90 F8 D2 CA 2D BB 7C ED BB C5 DC 72 D8 95 84 6A 33 44 41 13 B7 3B 31 5C 14 59 19 96 E3 91 D9 19 C7 EC 0F 6E 65 41 DF 10 CF 0C 11 C2 27 42 10 1D 76 D9 09 F9 0A 84 DB FA C9 08 45 1F 10 0E FD 8F 25 19 16 74 32 63 72 48 67 E5 B0 3D 02 A2 02 4A A3 57 53 02 70 55 FA B2 58 D5 2D DE 28 18 0C 1F AD 2C 75 BA 77 45 EA'), "little")
key = construct((n, e))

base_addresses = {
   0: 0x80000000, # SBOOT
   1: 0x8001C000, # CBOOT
   2: 0x80040000, # ASW1
   3: 0x80140000, # ASW2
   4: 0x80880000, # ASW3
   5: 0xA0800000 # CAL
}

checksum_block_location = {
   0: 0x300, # SBOOT
   1: 0x300, # CBOOT
   2: 0x300, # ASW1
   3: 0x0, # ASW2
   4: 0x0, # ASW3
   5: 0x300 # CAL
}

# From pyASN1

tag_id_to_string_map = {
    asn1.Numbers.Boolean: "BOOLEAN",
    asn1.Numbers.Integer: "INTEGER",
    asn1.Numbers.BitString: "BIT STRING",
    asn1.Numbers.OctetString: "OCTET STRING",
    asn1.Numbers.Null: "NULL",
    asn1.Numbers.ObjectIdentifier: "OBJECT",
    asn1.Numbers.PrintableString: "PRINTABLESTRING",
    asn1.Numbers.IA5String: "IA5STRING",
    asn1.Numbers.UTCTime: "UTCTIME",
    asn1.Numbers.Enumerated: "ENUMERATED",
    asn1.Numbers.Sequence: "SEQUENCE",
    asn1.Numbers.Set: "SET"
}

class_id_to_string_map = {
    asn1.Classes.Universal: "U",
    asn1.Classes.Application: "A",
    asn1.Classes.Context: "C",
    asn1.Classes.Private: "P"
}

object_id_to_string_map = {
    "1.2.840.113549.1.1.1": "rsaEncryption",
    "1.2.840.113549.1.1.5": "sha1WithRSAEncryption",
    "2.16.840.1.101.3.4.2.1": "sha-256 (NIST Algorithm)"
}


def tag_id_to_string(identifier):
    """Return a string representation of a ASN.1 id."""
    if identifier in tag_id_to_string_map:
        return tag_id_to_string_map[identifier]
    return '{:#02x}'.format(identifier)


def class_id_to_string(identifier):
    """Return a string representation of an ASN.1 class."""
    if identifier in class_id_to_string_map:
        return class_id_to_string_map[identifier]
    raise ValueError('Illegal class: {:#02x}'.format(identifier))


def object_identifier_to_string(identifier):
    if identifier in object_id_to_string_map:
        return object_id_to_string_map[identifier]
    return identifier


def value_to_string(tag_number, value):
    if tag_number == asn1.Numbers.ObjectIdentifier:
        return object_identifier_to_string(value)
    elif isinstance(value, bytes):
        return '0x' + str(binascii.hexlify(value).upper())
    elif isinstance(value, str):
        return value
    else:
        return repr(value)


def pretty_print(input_stream, output_stream, indent=0):
    """Pretty print ASN.1 data."""
    while not input_stream.eof():
        tag = input_stream.peek()
        if tag.typ == asn1.Types.Primitive:
            tag, value = input_stream.read()
            output_stream.write(' ' * indent)
            output_stream.write('[{}] {}: {}\n'.format(class_id_to_string(tag.cls), tag_id_to_string(tag.nr), value_to_string(tag.nr, value)))
        elif tag.typ == asn1.Types.Constructed:
            output_stream.write(' ' * indent)
            output_stream.write('[{}] {}\n'.format(class_id_to_string(tag.cls), tag_id_to_string(tag.nr)))
            input_stream.enter()
            pretty_print(input_stream, output_stream, indent + 2)
            input_stream.leave()

# here's the unpacker

blocknum = int(argv[2])

checksum_location = checksum_block_location[blocknum]
data_binary = open(argv[1], "rb").read()

current_checksum = struct.unpack("<I", data_binary[checksum_location+4:checksum_location+8])[0]
checksum_area_count = data_binary[checksum_location+8]
base_address = base_addresses[blocknum] 
   
addresses = []
for i in range(0, checksum_area_count * 2):
    address = struct.unpack('<I', data_binary[checksum_location+12+(i*4):checksum_location+16+(i*4)])
    offset = address[0] - base_address
    addresses.append(offset)

last_address = addresses[-1]
signature_material = data_binary[last_address + 5:last_address + 5 + 0x100]

decrypted_data = key._encrypt(int.from_bytes(signature_material, 'little'))
data = decrypted_data.to_bytes(256, 'big')
asn1_data = data[-0x33:]
try:
    decoder = asn1.Decoder()
    decoder.start(asn1_data)
    pretty_print(decoder, sys.stdout)
except Exception:
    print("Couldn't decode ASN.1!")