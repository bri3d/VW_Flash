from pathlib import Path
import unittest
from lib import simos_flash_utils
from lib import dsg_flash_utils
from lib import constants
from lib import extract_flash
from lib.modules import simos18, simos1810, dq250mqb
import zlib


class Simos18FlashUtilsTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        frf_file = Path("frf_test/FL_8V0906259H__0001.frf")
        frf_data = frf_file.read_bytes()
        cls.frf_raw_blocks = extract_flash.extract_flash_from_frf(frf_data)

    def setUp(self):
        self.flash_utils = simos_flash_utils
        self.flash_info = simos18.s18_flash_info
        frf_raw_blocks = Simos18FlashUtilsTestCase.frf_raw_blocks
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


class Simos1810FlashUtilsTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        frf_file = Path("frf_test/FL_5G0906259Q__0005.frf")
        frf_data = frf_file.read_bytes()
        cls.frf_raw_blocks = extract_flash.extract_flash_from_frf(frf_data)

    def setUp(self):
        self.flash_utils = simos_flash_utils
        self.flash_info = simos1810.s1810_flash_info
        frf_raw_blocks = Simos1810FlashUtilsTestCase.frf_raw_blocks
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
        block: constants.BlockData = self.flash_data["FD_05DATA"]
        block.block_bytes[0x500] = 0xB
        output_blocks = self.flash_utils.prepare_blocks(
            self.flash_info, self.flash_data
        )
        output_block: constants.PreparedBlockData = output_blocks["FD_05DATA"]
        crc32_cal = zlib.crc32(output_block.block_encrypted_bytes)
        self.assertEqual(crc32_cal, 348570407)

    def test_ecm3_checksum(self):
        block: constants.BlockData = self.flash_data["FD_05DATA"]
        block.block_bytes[0x1800] = 0xB
        output_blocks = self.flash_utils.prepare_blocks(
            self.flash_info, self.flash_data
        )
        output_block: constants.PreparedBlockData = output_blocks["FD_05DATA"]
        crc32_cal = zlib.crc32(output_block.block_encrypted_bytes)
        self.assertEqual(crc32_cal, 671125372)

    def test_cboot_patch(self):
        output_blocks = self.flash_utils.prepare_blocks(
            self.flash_info, self.flash_data, None, True
        )
        output_block: constants.PreparedBlockData = output_blocks["FD_01DATA"]
        crc32_cboot = zlib.crc32(output_block.block_encrypted_bytes)
        self.assertEqual(crc32_cboot, 3683823491)


class DsgFlashUtilsTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        frf_file = Path("frf_test/FL_0D9300012_4938_RcJQ_sw.frf")
        frf_data = frf_file.read_bytes()
        cls.frf_raw_blocks = extract_flash.extract_flash_from_frf(frf_data, True)

    def setUp(self):
        self.flash_utils = dsg_flash_utils
        self.flash_info = dq250mqb.dsg_flash_info
        frf_raw_blocks = DsgFlashUtilsTestCase.frf_raw_blocks
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
        block: constants.BlockData = self.flash_data["FD_3"]
        block.block_bytes[0x500] = 0xB
        output_blocks = self.flash_utils.prepare_blocks(
            self.flash_info, self.flash_data
        )
        output_block: constants.PreparedBlockData = output_blocks["FD_3"]
        crc32_cal = zlib.crc32(output_block.block_encrypted_bytes)
        self.assertEqual(crc32_cal, 458172227)
