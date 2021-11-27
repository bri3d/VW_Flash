# This module constructs special VW_Flash Workshop Codes. They follow the following format:
# YY MM DD : BCD-coded bytes indicating the flash date, for decoding by ODIS/VCDS/other tools.
# AA : CRC8 checksum of the ASW blocks flashed to the ECU, appended in order.
# UU UU UU UU : 4 bytes of user-defined information. On Simos, this is pulled from the bytes after the identifier in the CAL.
# This is a way to identify what was flashed last without ASW patches or ReadMemory access.
# CC : CRC8 checksum of the Workshop Code.

from .bcd import convert_from_bcd, convert_to_bcd
from datetime import date
import udsoncan

crc8_table = [
    0x00,
    0x07,
    0x0E,
    0x09,
    0x1C,
    0x1B,
    0x12,
    0x15,
    0x38,
    0x3F,
    0x36,
    0x31,
    0x24,
    0x23,
    0x2A,
    0x2D,
    0x70,
    0x77,
    0x7E,
    0x79,
    0x6C,
    0x6B,
    0x62,
    0x65,
    0x48,
    0x4F,
    0x46,
    0x41,
    0x54,
    0x53,
    0x5A,
    0x5D,
    0xE0,
    0xE7,
    0xEE,
    0xE9,
    0xFC,
    0xFB,
    0xF2,
    0xF5,
    0xD8,
    0xDF,
    0xD6,
    0xD1,
    0xC4,
    0xC3,
    0xCA,
    0xCD,
    0x90,
    0x97,
    0x9E,
    0x99,
    0x8C,
    0x8B,
    0x82,
    0x85,
    0xA8,
    0xAF,
    0xA6,
    0xA1,
    0xB4,
    0xB3,
    0xBA,
    0xBD,
    0xC7,
    0xC0,
    0xC9,
    0xCE,
    0xDB,
    0xDC,
    0xD5,
    0xD2,
    0xFF,
    0xF8,
    0xF1,
    0xF6,
    0xE3,
    0xE4,
    0xED,
    0xEA,
    0xB7,
    0xB0,
    0xB9,
    0xBE,
    0xAB,
    0xAC,
    0xA5,
    0xA2,
    0x8F,
    0x88,
    0x81,
    0x86,
    0x93,
    0x94,
    0x9D,
    0x9A,
    0x27,
    0x20,
    0x29,
    0x2E,
    0x3B,
    0x3C,
    0x35,
    0x32,
    0x1F,
    0x18,
    0x11,
    0x16,
    0x03,
    0x04,
    0x0D,
    0x0A,
    0x57,
    0x50,
    0x59,
    0x5E,
    0x4B,
    0x4C,
    0x45,
    0x42,
    0x6F,
    0x68,
    0x61,
    0x66,
    0x73,
    0x74,
    0x7D,
    0x7A,
    0x89,
    0x8E,
    0x87,
    0x80,
    0x95,
    0x92,
    0x9B,
    0x9C,
    0xB1,
    0xB6,
    0xBF,
    0xB8,
    0xAD,
    0xAA,
    0xA3,
    0xA4,
    0xF9,
    0xFE,
    0xF7,
    0xF0,
    0xE5,
    0xE2,
    0xEB,
    0xEC,
    0xC1,
    0xC6,
    0xCF,
    0xC8,
    0xDD,
    0xDA,
    0xD3,
    0xD4,
    0x69,
    0x6E,
    0x67,
    0x60,
    0x75,
    0x72,
    0x7B,
    0x7C,
    0x51,
    0x56,
    0x5F,
    0x58,
    0x4D,
    0x4A,
    0x43,
    0x44,
    0x19,
    0x1E,
    0x17,
    0x10,
    0x05,
    0x02,
    0x0B,
    0x0C,
    0x21,
    0x26,
    0x2F,
    0x28,
    0x3D,
    0x3A,
    0x33,
    0x34,
    0x4E,
    0x49,
    0x40,
    0x47,
    0x52,
    0x55,
    0x5C,
    0x5B,
    0x76,
    0x71,
    0x78,
    0x7F,
    0x6A,
    0x6D,
    0x64,
    0x63,
    0x3E,
    0x39,
    0x30,
    0x37,
    0x22,
    0x25,
    0x2C,
    0x2B,
    0x06,
    0x01,
    0x08,
    0x0F,
    0x1A,
    0x1D,
    0x14,
    0x13,
    0xAE,
    0xA9,
    0xA0,
    0xA7,
    0xB2,
    0xB5,
    0xBC,
    0xBB,
    0x96,
    0x91,
    0x98,
    0x9F,
    0x8A,
    0x8D,
    0x84,
    0x83,
    0xDE,
    0xD9,
    0xD0,
    0xD7,
    0xC2,
    0xC5,
    0xCC,
    0xCB,
    0xE6,
    0xE1,
    0xE8,
    0xEF,
    0xFA,
    0xFD,
    0xF4,
    0xF3,
]


def crc8_hash(data: bytes):
    sum = 0
    for byte in data:
        sum = crc8_table[sum ^ byte]
    return sum


def date_bytes(date: date):
    year_bcd = convert_to_bcd(int(date.strftime("%y")))
    month_bcd = convert_to_bcd(int(date.month))
    day_bcd = convert_to_bcd(int(date.day))
    return bytes([year_bcd, month_bcd, day_bcd])


def workshop_code_crc(workshop_code):
    crc = crc8_hash(workshop_code)
    return crc


def workshop_code_is_valid(workshop_code: bytes):
    crc = workshop_code_crc(workshop_code[0:8])
    return int(workshop_code[8]) == crc


class WorkshopCode:
    cal_id: bytes
    asw_checksum: int
    flash_date: date
    is_valid: bool
    is_old: bool

    def __init__(self, asw_checksum=None, cal_id=None, workshop_code: bytes = None):
        self.is_old = False
        if workshop_code is None:
            self.asw_checksum = asw_checksum
            self.cal_id = cal_id
            self.flash_date = date.today()
            self.is_valid = True
        else:
            self.flash_date = date(
                convert_from_bcd(workshop_code[0]),
                convert_from_bcd(workshop_code[1]),
                convert_from_bcd(workshop_code[2]),
            )
            self.is_valid = workshop_code_is_valid(workshop_code)
            if self.is_valid:
                self.cal_id = workshop_code[4:8]
                self.asw_checksum = int(workshop_code[3])
            else:
                if workshop_code[3] == 0x42 and workshop_code[4] == 0x04:
                    self.is_old = True
                self.cal_id = b"UNKN"
                self.asw_checksum = 0

    def as_bytes(self):
        bytes = bytearray()
        bytes += date_bytes(self.flash_date)
        bytes += self.asw_checksum.to_bytes(1, "little")
        bytes += self.cal_id
        bytes += workshop_code_crc(bytes).to_bytes(1, "little")
        return bytes

    def human_readable(self):
        fingerprint = "Block fingerprint dated "
        fingerprint += self.flash_date.strftime("'%y %B %d")
        if self.is_valid:
            fingerprint += " is valid and was written by SimosTools or VW_Flash. "
        elif self.is_old:
            fingerprint += " was written by an older version of SimosTools or VW_Flash."
            return fingerprint
        else:
            fingerprint += " does not appear to be from SimosTools or VW_Flash."
            return fingerprint
        fingerprint += "It was written with ASW Checksum "
        fingerprint += str(self.asw_checksum)
        fingerprint += " and CAL ID : "
        fingerprint += self.cal_id.decode("us-ascii")
        return fingerprint


class WorkshopCodeCodec(udsoncan.DidCodec):
    def encode(self, val):
        return bytes(val)

    def decode(self, payload):
        description_text = payload.hex()
        description_text += "\n"
        chunks = [payload[i : i + 10] for i in range(0, len(payload), 10)]
        wscs = [WorkshopCode(workshop_code=chunk[0:9]) for chunk in chunks]
        description_text += "\n".join(map(lambda wsc: wsc.human_readable(), wscs))
        return description_text

    def __len__(self):
        raise udsoncan.DidCodec.ReadAllRemainingData
