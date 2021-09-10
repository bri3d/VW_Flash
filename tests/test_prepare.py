from pathlib import Path
import unittest
from lib import simos_flash_utils
from lib import dsg_flash_utils
from lib import constants
from lib import extract_flash
import zlib


class SimosFlashUtilsTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        frf_file = Path("frf_test/FL_8V0906259H__0001.frf")
        frf_data = frf_file.read_bytes()
        cls.frf_raw_blocks = extract_flash.extract_flash_from_frf(frf_data)

    def setUp(self):
        self.flash_utils = simos_flash_utils
        self.flash_info = constants.s18_flash_info
        frf_raw_blocks = SimosFlashUtilsTestCase.frf_raw_blocks
        input_blocks = {}
        for i in self.flash_info.block_names_frf.keys():
            filename = self.flash_info.block_names_frf[i]
            input_blocks[filename] = constants.BlockData(
                i, frf_raw_blocks[filename].copy()
            )
        self.flash_data = input_blocks

    def test_with_correct_checksum(self):
        output_blocks = self.flash_utils.prepare_blocks(
            self.flash_info, self.flash_data
        )

    def test_incorrect_checksum(self):
        block: constants.BlockData = self.flash_data["FD_4"]
        block.block_bytes[0x500] = 0xB
        output_blocks = self.flash_utils.prepare_blocks(
            self.flash_info, self.flash_data
        )
        output_block: constants.PreparedBlockData = output_blocks["FD_4"]
        crc32_cal = zlib.crc32(output_block.block_encrypted_bytes)
        self.assertEqual(crc32_cal, 4173559587)

    def test_ecm3_checksum(self):
        block: constants.BlockData = self.flash_data["FD_4"]
        block.block_bytes[0x1800] = 0xB
        output_blocks = self.flash_utils.prepare_blocks(
            self.flash_info, self.flash_data
        )
        output_block: constants.PreparedBlockData = output_blocks["FD_4"]
        crc32_cal = zlib.crc32(output_block.block_encrypted_bytes)
        self.assertEqual(crc32_cal, 273589659)

    def test_cboot_patch(self):
        output_blocks = self.flash_utils.prepare_blocks(
            self.flash_info, self.flash_data, None, True
        )
        output_block: constants.PreparedBlockData = output_blocks["FD_0"]
        crc32_cboot = zlib.crc32(output_block.block_encrypted_bytes)
        self.assertEqual(crc32_cboot, 2487058965)
