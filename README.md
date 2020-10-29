# VW_Flash
VW Flashing Tools over ISO-TP / UDS

# Current tools
volkswagen_security.py provides an implementation of the "SA2" Seed/Key algorithm for VW Auto Group vehicles. The SA2 script can be found in the ODX flash container for the vehicle. The bytecode from the SA2 script is executed against the Security Access Seed to generate the Security Access Key. This script has been tested against a range of SA2 bytecodes and should be quite robust.

flashsimos18.py provides a rudimentary flasher for Simos18 ECUs. The supplied BIN file should be pre-compressed and pre-encrypted for now. I have documented the compresssion and encryption here: http://nefariousmotorsports.com/forum/index.php?topic=10364.msg122889#msg122889 . 

You can pass a tunertag into flashsimos18 if you have a tuned Simos18 ECU with protection re-enabled in CBOOT and a special 0x3E handler to write the validity flags for your CAL. If you have left tune protection / RSA disabled in CBOOT, this is unnecessary.

checksumsimos18 provides CRC checksum verification and correction for Simos18 block payloads.

encryptsimos18.py provides encryption for Simos18 ECU block payloads.

The `lzss` directory contains an implementation of LZSS modified to use the correction dictionary size and window length for Simos18 ECUs. Thanks to `tinytuning` for this. 

[Docs.md](Docs.md) contains documentation about the Simos18 boot, trust chain, and exploit process. Tools to leverage this process and flash custom firmware are coming soon.

flashsimos18 requires a working SocketCAN and ISO-TP setup, including the out-of-tree kernel module at https://github.com/hartkopp/can-isotp and properly configured can0 interface. Please check the documentation for your CAN module to learn how to set up the interface.
