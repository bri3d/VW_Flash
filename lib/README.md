# VW_Flash libraries
lib directory for scripts used at different times throughout the flashing process
[simos_flash_utils.py](simos_flash_utils.py) most importantly is supposed to be used as the main entry into the other utilities.  ../VW_Flash.py essentially provides a CLI to THIS.  Ultimately, this will provide an entry point for the Web GUI and/or other controllers.

[constants.py](constants.py) is a python file for constants used throughout the program

[checksum.py](checksum.py) provides CRC checksum verification and correction for Simos18 block payloads.

[encrypt.py](encrypt.py) provides AES encryption for Simos18 ECU block payloads.

[lzss](lzss) is a directory that contains an implementation of lzss Thanks tinytuning!

[lzssHelper.py](lszzHelper.py) is a python lib that just calls the c program

[lzss.py](lzss.py) is a python implementation of lzss - hasn't been tested except to know that it might be too slow for what we want to accomplish
