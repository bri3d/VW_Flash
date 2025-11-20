import logging
import struct
from lib.constants import BlockData
from lib import binfile

logger = logging.getLogger("VWFlash")


class HaldexBinFileHandler(binfile.BinFileHandler):
    def blocks_from_data(self, data: bytes) -> dict[str, BlockData]:
        input_blocks = {}

        for i in self.flash_info.block_names_frf.keys():
            filename = self.flash_info.block_names_frf[i]
            block_length = self.flash_info.block_lengths[i]

            if filename == "FD_1DATA":
                logger.info("Dynamically getting CAL length for Haldex...")
                length = data[
                    (self.flash_info.binfile_layout[i] + 0x14) : (
                        self.flash_info.binfile_layout[i] + 0x18
                    )
                ]
                logger.info("Set Haldex CAL length to: " + length.hex())
                block_length = struct.unpack("<I", length)[0]

            if filename == "FD_2DATA":
                logger.info("Dynamically getting ASW length for Haldex...")
                length = data[
                    (self.flash_info.binfile_layout[i] + 0x204) : (
                        self.flash_info.binfile_layout[i] + 0x208
                    )
                ]
                logger.info("Set Haldex ASW length to: " + length.hex())
                block_length = struct.unpack("<I", length)[0]

            if filename == "FD_3DATA":
                logger.info("Dynamically getting VERSION length for Haldex...")
                length = data[
                    (self.flash_info.binfile_layout[i] + 0x4) : (
                        self.flash_info.binfile_layout[i] + 0x8
                    )
                ]
                logger.info("Set Haldex VERSION length to: " + length.hex())
                block_length = struct.unpack("<I", length)[0]

            self.flash_info.block_lengths[i] = block_length

            input_blocks[filename] = BlockData(
                i,
                data[
                    self.flash_info.binfile_layout[i] : self.flash_info.binfile_layout[
                        i
                    ]
                    + block_length
                ],
            )

        input_blocks = self.filter_blocks(input_blocks)

        return input_blocks
