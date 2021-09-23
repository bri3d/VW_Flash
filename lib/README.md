# VW_Flash libraries
lib directory for scripts used at different times throughout the flashing process

[simos_flash_utils.py](simos_flash_utils.py) is the main "controller" file for Simos flashing. This controller compresses, encrypts, and controls the overall flashing process.

[dsg_flash_utils.py](dsg_flash_utils.py) is the main "controller" file for DSG flashing. This controller compresses, encrypts, and controls the overall flashing process.

[flash_uds.py](flash_uds.py) implements the actual data-flashing actions over UDS.

[constants.py](constants.py) contains constants used throughout the program.

[modules](modules) contains definitions for the flash layout, checksum locations, addresses, encryption keys, and SA2 scripts for specific control modules.

[checksum.py](checksum.py) provides CRC checksum verification and correction for Simos18 block payloads, as well as ECM3->ECM2 summation verification and correction.

[encrypt.py](encrypt.py) provides AES encryption for Simos18 ECU block payloads.

[lzss](lzss) is a directory that contains an implementation of lzss Thanks tinytuning!

[lzss_helper.py](lszz_helper.py) is a wrapper to call the `lzss` binary

[lzss.py](lzss.py) is a python implementation of lzss. this turned out to be quite slow and isn't currently used.

[j2534_connection.py](j2534_connection.py) provides support for the J2534 connection type to UDSonCAN

[j2534.py](j2534.py) wraps the J2534 standard with Python, using `ctypes`

[patch_cboot.py](patch_cboot.py) automatically patches the Customer Bootloader block (CBOOT) for Simos ECUs to Sample Mode, using a very naive hex patching algorithm that against all odds, seems to work great.

[simos_hsl.py](simos_hsl.py) , brought to you by Joedubs, provides High Speed Logging using one of several backends (all which require ECU-side software patches): $23 ReadMemoryByAddress, $2C DynamicallyDefineLocalIdentifier, or a proprietary handler attached to $3E TesterPresent.

[fastcrc.py](fastcrc.py) contains a calculated-table "fast CRC32" implementation to checksum blocks.

[extract_flash.py](extract_flash.py) provides a wrapper to decrypt an FRF file, unzip it, extract flash blocks from the ODX file within, and decrypt and decompress those blocks.