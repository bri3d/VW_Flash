# VW_Flash libraries
lib directory for scripts used at different times throughout the flashing process

[simos_flash_utils.py](simos_flash_utils.py) is the main "controller" file for the project. Most actions are implemented using this file as an entry point.

[simos_uds.py](simos_uds.py) implements the actual data-flashing actions over UDS.

[constants.py](constants.py) is a python file for constants used throughout the program. This contains the AES keys and memory layouts for Simos ECUs, as well as the SA2 scripts and miscellaneous useful memory addresses.

[checksum.py](checksum.py) provides CRC checksum verification and correction for Simos18 block payloads.

[encrypt.py](encrypt.py) provides AES encryption for Simos18 ECU block payloads.

[lzss](lzss) is a directory that contains an implementation of lzss Thanks tinytuning!

[lzss_helper.py](lszz_helper.py) is a wrapper to call the `lzss` binary

[lzss.py](lzss.py) is a python implementation of lzss. this turned out to be quite slow and isn't currently used.