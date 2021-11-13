import logging
from pathlib import Path
from .constants import FlashInfo
from .constants import BlockData
from .modules import simosshared

logger = logging.getLogger("VWFlash")


def input_block_info(
    input_blocks: dict,
    flash_info: FlashInfo,
    int_block_names=simosshared.int_to_block_name,
):
    return "\n".join(
        [
            " : ".join(
                [
                    filename,
                    str(input_blocks[filename].block_number),
                    int_block_names[input_blocks[filename].block_number],
                    str(
                        input_blocks[filename]
                        .block_bytes[
                            flash_info.software_version_location[
                                input_blocks[filename].block_number
                            ][0] : flash_info.software_version_location[
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
                            flash_info.box_code_location[
                                input_blocks[filename].block_number
                            ][0] : flash_info.box_code_location[
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


def filter_blocks(input_blocks: dict, flash_info: FlashInfo):
    remove_blocks = []
    for filename in input_blocks:
        try:
            block_info = str(
                input_blocks[filename]
                .block_bytes[
                    flash_info.software_version_location[
                        input_blocks[filename].block_number
                    ][0] : flash_info.software_version_location[
                        input_blocks[filename].block_number
                    ][
                        1
                    ]
                ]
                .decode()
            )
            if not str.startswith(block_info, flash_info.project_name):
                logger.warning(
                    "Discarding block "
                    + filename
                    + " because project ID "
                    + block_info
                    + " does not match "
                    + flash_info.project_name
                )
                remove_blocks.append(filename)
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


def blocks_from_bin(bin_path: str, flash_info: FlashInfo) -> dict:
    bin_data = Path(bin_path).read_bytes()
    input_blocks = {}

    for i in flash_info.block_names_frf.keys():
        filename = flash_info.block_names_frf[i]
        input_blocks[filename] = BlockData(
            i,
            bin_data[
                flash_info.binfile_layout[i] : flash_info.binfile_layout[i]
                + flash_info.block_lengths[i]
            ],
        )

    input_blocks = filter_blocks(input_blocks, flash_info)

    return input_blocks
