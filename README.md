# VW_Flash
VW Flashing Tools over ISO-TP / UDS

# More Information
[docs.md](docs.md) contains documentation about the Simos18 ECU architecture, boot, trust chain, and exploit process, including an exploit chain to enable unsigned code to be injected in ASW.

[patch.md](patch.md) and patch.bin provide a worked example of an ASW patch which "pivots" into an in-memory CBOOT with signature checking turned off. This CBOOT will write the "Security Keys" / "OK Flags" for an arbitrary CBOOT regardless of signature validity, which will cause this CBOOT to be "promoted" to the real CBOOT position by SBOOT. In this way a complete trust chain bypass can be installed on a Simos18.1 ECU.

# Current tools
[sa2-seed-key](https://github.com/bri3d/sa2_seed_key) provides an implementation of the "SA2" Seed/Key algorithm for VW Auto Group vehicles. The SA2 script can be found in the ODX flash container for the vehicle. The bytecode from the SA2 script is executed against the Security Access Seed to generate the Security Access Key. This script has been tested against a range of SA2 bytecodes and should be quite robust.

[flashsimos18.py](flashsimos18.py) provides a flasher for Simos18 ECUs. I have documented the compresssion and encryption here: http://nefariousmotorsports.com/forum/index.php?topic=10364.msg122889#msg122889 . You can pass a tunertag into flashsimos18 if you have a tuned Simos18 ECU with protection re-enabled in CBOOT and a special 0x3E handler to write the validity flags for your CAL. If you have left tune protection / RSA disabled in CBOOT, this is unnecessary. flashsimos18 requires a working SocketCAN and ISO-TP setup, including the out-of-tree kernel module at https://github.com/hartkopp/can-isotp and properly configured can0 interface. Please check the documentation for your CAN module to learn how to set up the interface.

[checksumsimos18.py](checksumsimos18.py) provides CRC checksum verification and correction for Simos18 block payloads.

[encryptsimos18.py](encryptsimos18.py) provides AES encryption for Simos18 ECU block payloads.

[extractodxsimos18.py](extractodxsimos18.py) extracts a factory ODX container to decompressed, decrypted blocks suitable for modification and re-flashing.

The `lzss` directory contains an implementation of LZSS modified to use the correction dictionary size and window length for Simos18 ECUs. Thanks to `tinytuning` for this. 

prepareblock.sh automates the checksum, compression, and encryption process necessary to make a block flashable.
