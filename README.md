# VW_Flash
VW Flashing Tools over ISO-TP / UDS

# More Information
[docs.md](docs.md) contains documentation about the Simos18 ECU architecture, boot, trust chain, and exploit process, including an exploit chain to enable unsigned code to be injected in ASW.

[patch.md](patch.md) and patch.bin provide a worked example of an ASW patch which "pivots" into an in-memory CBOOT with signature checking turned off. This CBOOT will write the "Security Keys" / "OK Flags" for an arbitrary CBOOT regardless of signature validity, which will cause this CBOOT to be "promoted" to the real CBOOT position by SBOOT. In this way a complete trust chain bypass can be installed on a Simos18.1 ECU.

# Current tools
[sa2-seed-key](https://github.com/bri3d/sa2_seed_key) provides an implementation of the "SA2" Seed/Key algorithm for VW Auto Group vehicles. The SA2 script can be found in the ODX flash container for the vehicle. The bytecode from the SA2 script is executed against the Security Access Seed to generate the Security Access Key. This script has been tested against a range of SA2 bytecodes and should be quite robust.

[VW_Flash.py](VW_Flash.py) provides a command line interface which has the capability of performing various operations.  The help output is:

```bash
pi@raspberrypi:~/VW_Flash $ python3 VW_Flash.py --help
usage: VW_Flash.py [-h] --action
                   {checksum,checksum_fix,lzss,encrypt,prepare,flash_bin,flash_prepared}
                   [--infile INFILE] [--outfile] --block
                   {CBOOT,1,ASW1,2,ASW2,3,ASW3,4,CAL,5,PATCH_ASW1,7,PATCH_ASW2,8,PATCH_ASW3,9}
                   [--simos12]

VW_Flash CLI

optional arguments:
  -h, --help            show this help message and exit
  --action {checksum,checksum_fix,lzss,encrypt,prepare,flash_bin,flash_prepared}
                        The action you want to take
  --infile INFILE       the absolute path of an inputfile
  --outfile             the absolutepath of a file to output
  --block {CBOOT,1,ASW1,2,ASW2,3,ASW3,4,CAL,5,PATCH_ASW1,7,PATCH_ASW2,8,PATCH_ASW3,9}
                        The block name or number
  --simos12             specify simos12, available for checksumming

The MAIN CLI interface for using the tools herein
```

[flashsimos18.py](flashsimos18.py) provides a flasher for Simos18 ECUs. I have documented the compresssion and encryption here: http://nefariousmotorsports.com/forum/index.php?topic=10364.msg122889#msg122889 . You can pass a tunertag into flashsimos18 if you have a tuned Simos18 ECU with protection re-enabled in CBOOT and a special 0x3E handler to write the validity flags for your CAL. If you have left tune protection / RSA disabled in CBOOT, this is unnecessary. flashsimos18 requires a working SocketCAN and ISO-TP setup, including the out-of-tree kernel module at https://github.com/hartkopp/can-isotp and properly configured can0 interface. Please check the documentation for your CAN module to learn how to set up the interface.

[extractodxsimos18.py](extractodxsimos18.py) extracts a factory ODX container to decompressed, decrypted blocks suitable for modification and re-flashing.

The `lzss` directory contains an implementation of LZSS modified to use the correction dictionary size and window length for Simos18 ECUs. Thanks to `tinytuning` for this. 

prepareblock.sh automates the checksum, compression, and encryption process necessary to make a block flashable.
