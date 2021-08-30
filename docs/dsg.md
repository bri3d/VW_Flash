
The DQ250-MQB DSG is fairly unprotected - [a simple 256-byte rolling-offset substitution cipher](https://github.com/bri3d/VW_Flash/blob/master/lib/decryptdsg.py) encrypts an LZSS compressed payload, and the controller will even accept uncompressed, unencrypted payloads as well. [Checksums are just JAMCRC / inverse CRC32 at the end of a file](https://github.com/bri3d/VW_Flash/blob/master/lib/dsg_checksum.py) .

A small flash driver module is uploaded as part of DQ250 flashing, which is protected only by an external checksum. This also allows for some clever payloads to be uploaded and used to dump DSG memory.

The Driver is uploaded to `0xD4000000` (Scratchpad RAM), and the first 4 bytes are checked and must be `00 00 2E A2` . Next, the full Driver's checksum must match the CRC32 sent in the UDS Checksum request.

When the Checksum request for the Driver block is invoked, the pointer at `0x4` in the Driver is read and executed - by default, the function at `d4000300` (`0x300` in the Driver). This can be trivially replaced with any custom code as desired, for example a Flash read primitive to dump/backup DSG firmware.