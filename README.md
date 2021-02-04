# VW_Flash
VW Flashing Tools over ISO-TP / UDS

# More Information
[docs/docs.md](docs/docs.md) contains documentation about the Simos18 ECU architecture, boot, trust chain, and exploit process, including an exploit chain to enable unsigned code to be injected in ASW.

[docs/patch.md](docs/patch.md) and patch.bin provide a worked example of an ASW patch which "pivots" into an in-memory CBOOT with signature checking turned off. This CBOOT will write the "Security Keys" / "OK Flags" for an arbitrary CBOOT regardless of signature validity, which will cause this CBOOT to be "promoted" to the real CBOOT position by SBOOT. In this way a complete trust chain bypass can be installed on a Simos18.1 ECU.

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


# Flashing basics
VW_Flash.py has the capability of automated block prep and flashing.  As outlined elsewhere, blocks must be checksummed, compressed, and encrypted prior to being sent to the ECU.  VW_Flash.py will write compressed files to the /tmp/ space due to the way lzss compression is currently being handled.

While you *can* perform each step of the process manually, it's unneceessary.  If you want to perform a simple calibration flash to an already patched ECU, you'll need to provide --activity flash_bin --infile calibration.bin --block CAL:

```bash
pi@raspberrypi:~/VW_Flash $ python3 VW_Flash.py --action flash_bin --infile /home/pi/flashfiles/testdir/18tsi_MPI_IS38hybrid_FlexTiming_3000rpmscav_1.9bar_500nm.bin --block CAL
2021-02-01 18:31:40,618 - Preparing /home/pi/flashfiles/testdir/18tsi_MPI_IS38hybrid_FlexTiming_3000rpmscav_1.9bar_500nm.bin for flashing as block 5
2021-02-01 18:31:40,618 - Performing Checksum
2021-02-01 18:31:40,619 - Adding 0x0:0x2ff
2021-02-01 18:31:40,619 - Adding 0x400:0x7f9ff
2021-02-01 18:31:44,068 - Checksum = 0xb0fdc985
2021-02-01 18:31:44,068 - File is invalid! File checksum: 0x22a67813 does not match 0xb0fdc985
2021-02-01 18:31:44,072 - Fixed checksum in binary
compressedSize 3106a
0
2021-02-01 18:31:45,471 - No outfile specified
2021-02-01 18:31:45,471 - Encrypting binary data
Preparing to flash the following blocks:
/home/pi/flashfiles/testdir/18tsi_MPI_IS38hybrid_FlexTiming_3000rpmscav_1.9bar_500nm.bin = 5
Sending 0x4 Clear Emissions DTCs over OBD-2
2021-02-01 18:31:45,481 - Connection opened
2021-02-01 18:31:45,481 - Sending 1 bytes : [b'04']
...
...
...
```

Furthermore, you can flash *muliple* blocks via one command by providing additional --infile xxx --block params like so.

```bash
pi@raspberrypi:~/VW_Flash $ python3 VW_Flash.py --action flash_bin \
> --infile /home/pi/flashfiles/ASW/8v0906264M_ASW2_PerformanceFlex_checksummed.bin --block ASW2 \
> --infile /home/pi/flashfiles/tunes/18tsi_MPI_IS38hybrid_FlexTiming_3000rpmscav_1.9bar_500nm.bin --block CAL
2021-02-01 18:40:22,021 - Preparing /home/pi/flashfiles/ASW/8v0906264M_ASW2_PerformanceFlex_checksummed.bin for flashing as block 3
2021-02-01 18:40:22,021 - Performing Checksum
2021-02-01 18:40:22,022 - Adding 0x300:0xbf9ff
2021-02-01 18:40:27,196 - Checksum = 0x404e5bf3
2021-02-01 18:40:27,196 - File is valid!
2021-02-01 18:40:27,197 - Checksum in binary already valid
compressedSize 946ad
0
2021-02-01 18:40:30,420 - No outfile specified
2021-02-01 18:40:30,420 - Encrypting binary data
2021-02-01 18:40:30,438 - Preparing /home/pi/flashfiles/tunes/18tsi_MPI_IS38hybrid_FlexTiming_3000rpmscav_1.9bar_500nm.bin for flashing as block 5
2021-02-01 18:40:30,439 - Performing Checksum
2021-02-01 18:40:30,439 - Adding 0x0:0x2ff
2021-02-01 18:40:30,439 - Adding 0x400:0x7f9ff
2021-02-01 18:40:34,044 - Checksum = 0xb0fdc985
2021-02-01 18:40:34,044 - File is invalid! File checksum: 0x22a67813 does not match 0xb0fdc985
2021-02-01 18:40:34,046 - Fixed checksum in binary
compressedSize 3106a
0
2021-02-01 18:40:35,444 - No outfile specified
2021-02-01 18:40:35,444 - Encrypting binary data
Preparing to flash the following blocks:
/home/pi/flashfiles/ASW/8v0906264M_ASW2_PerformanceFlex_checksummed.bin = 3
/home/pi/flashfiles/tunes/18tsi_MPI_IS38hybrid_FlexTiming_3000rpmscav_1.9bar_500nm.bin = 5
Sending 0x4 Clear Emissions DTCs over OBD-2
2021-02-01 18:40:35,454 - Connection opened
2021-02-01 18:40:35,454 - Sending 1 bytes : [b'04']
...
...
...
```
