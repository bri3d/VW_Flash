import logging
from pathlib import Path
from .constants import FlashInfo
from .constants import BlockData

logger = logging.getLogger("VWFlash")


class BinFileHandler:
    def __init__(self, flash_info: FlashInfo):
        self.flash_info = flash_info

    def bin_from_blocks(self, output_blocks):
        outfile_data = bytearray(self.flash_info.binfile_size)
        for filename in output_blocks:
            output_block: BlockData = output_blocks[filename]
            binary_data = output_block.block_bytes
            block_number = output_block.block_number
            outfile_data[
                self.flash_info.binfile_layout[
                    block_number
                ] : self.flash_info.binfile_layout[block_number]
                + self.flash_info.block_lengths[block_number]
            ] = binary_data
        return outfile_data

    def input_block_info(
        self,
        input_blocks: dict[str, BlockData],
    ):
        return "\n".join(
            [
                " : ".join(
                    [
                        filename,
                        str(input_blocks[filename].block_number),
                        self.flash_info.number_to_block_name[
                            input_blocks[filename].block_number
                        ],
                        str(
                            input_blocks[filename]
                            .block_bytes[
                                self.flash_info.software_version_location[
                                    input_blocks[filename].block_number
                                ][0] : self.flash_info.software_version_location[
                                    input_blocks[filename].block_number
                                ][
                                    1
                                ]
                            ]
                            .decode()
                        ),
                        str(
                            input_blocks[filename]
                            .block_bytes[
                                self.flash_info.box_code_location[
                                    input_blocks[filename].block_number
                                ][0] : self.flash_info.box_code_location[
                                    input_blocks[filename].block_number
                                ][
                                    1
                                ]
                            ]
                            .decode()
                        ),
                    ]
                )
                for filename in input_blocks
            ]
        )

    def filter_blocks(self, input_blocks: dict[str, BlockData]):
        remove_blocks = []
        for filename in input_blocks:
            try:
                if (
                    self.flash_info.software_version_location[
                        input_blocks[filename].block_number
                    ][1]
                    > 0
                ):
                    block_info = str(
                        input_blocks[filename]
                        .block_bytes[
                            self.flash_info.software_version_location[
                                input_blocks[filename].block_number
                            ][0] : self.flash_info.software_version_location[
                                input_blocks[filename].block_number
                            ][
                                1
                            ]
                        ]
                        .decode()
                    )

                    if not str.startswith(block_info, self.flash_info.project_name):
                        logger.warning(
                            "Discarding block "
                            + filename
                            + " because project ID "
                            + block_info
                            + " does not match "
                            + self.flash_info.project_name
                        )
                        remove_blocks.append(filename)
                else:
                    logger.warning(
                        "Keeping block "
                        + filename
                        + " because it has no version specifier."
                    )
            except:
                logger.warning(
                    "Discarding block "
                    + filename
                    + " because it did not contain a project ID"
                )
                remove_blocks.append(filename)
        for block in remove_blocks:
            del input_blocks[block]
        return input_blocks

    def blocks_from_bin(self, bin_path: str) -> dict[str, BlockData]:
        bin_data = Path(bin_path).read_bytes()
        return self.blocks_from_data(bin_data)

    def blocks_from_data(self, data: bytes) -> dict[str, BlockData]:
        input_blocks = {}

        for i in self.flash_info.block_names_frf.keys():
            filename = self.flash_info.block_names_frf[i]
            block_length = self.flash_info.block_lengths[i]

            input_blocks[filename] = BlockData(
                i,
                data[
                    self.flash_info.binfile_layout[i] : self.flash_info.binfile_layout[
                        i
                    ]
                    + block_length
                ],
            )

        input_blocks = self.filter_blocks(input_blocks, self.flash_info)

        return input_blocks
