import logging
import struct
from pathlib import Path
from .constants import FlashInfo
from .constants import BlockData

logger = logging.getLogger("VWFlash")


def bin_from_blocks(output_blocks, flash_info: FlashInfo):
    outfile_data = bytearray(flash_info.binfile_size)
    for filename in output_blocks:
        output_block: BlockData = output_blocks[filename]
        binary_data = output_block.block_bytes
        block_number = output_block.block_number
        outfile_data[
            flash_info.binfile_layout[block_number] : flash_info.binfile_layout[
                block_number
            ]
            + flash_info.block_lengths[block_number]
        ] = binary_data
    return outfile_data


def input_block_info(
    input_blocks: dict[str, BlockData],
    flash_info: FlashInfo,
):
    return "\n".join(
        [
            " : ".join(
                [
                    filename,
                    str(input_blocks[filename].block_number),
                    flash_info.number_to_block_name[
                        input_blocks[filename].block_number
                    ],
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


def filter_blocks(input_blocks: dict[str, BlockData], flash_info: FlashInfo):
    remove_blocks = []
    for filename in input_blocks:
        try:
            if (
                flash_info.software_version_location[
                    input_blocks[filename].block_number
                ][1]
                > 0
            ):
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


def blocks_from_bin(bin_path: str, flash_info: FlashInfo, haldex_hack: bool = False) -> dict[str, BlockData]:
    bin_data = Path(bin_path).read_bytes()
    return blocks_from_data(bin_data, flash_info, haldex_hack)


def blocks_from_data(data: bytes, flash_info: FlashInfo, haldex_hack: bool = False) -> dict[str, BlockData]:
    input_blocks = {}


    for i in flash_info.block_names_frf.keys():
        filename = flash_info.block_names_frf[i]
        block_length = flash_info.block_lengths[i]

        # TODO: Make this less awful

        if haldex_hack:
            if filename == 'FD_1DATA':
                logger.info('Dynamically getting CAL length for Haldex...')
                length = data[ (flash_info.binfile_layout[i] + 0x14) : (flash_info.binfile_layout[i] + 0x18)]
                logger.info('Set Haldex CAL length to: '+length.hex())
                block_length = struct.unpack('<I', length)[0]

            if filename == 'FD_2DATA':
                logger.info('Dynamically getting ASW length for Haldex...')
                length = data[ (flash_info.binfile_layout[i] + 0x204) : (flash_info.binfile_layout[i] + 0x208)]
                logger.info('Set Haldex ASW length to: '+length.hex())
                block_length = struct.unpack('<I', length)[0]

            if filename == 'FD_3DATA':
                logger.info('Dynamically getting VERSION length for Haldex...')
                length = data[ (flash_info.binfile_layout[i] + 0x4) : (flash_info.binfile_layout[i] + 0x8)]
                logger.info('Set Haldex VERSION length to: '+length.hex())
                block_length = struct.unpack('<I', length)[0]

        input_blocks[filename] = BlockData(
            i,
            data[
                flash_info.binfile_layout[i] : flash_info.binfile_layout[i]
                + block_length
            ],
        )

    input_blocks = filter_blocks(input_blocks, flash_info)

    return input_blocks
