# Getting Started with the CLI

To use these tools to flash a vehicle, we need to do two things: "unlock the ECU," and flash a patched ECU software matching the vehicle to be run. 

# USDM MQB Simos18.1/6 (GTI, Golf R, SportWagon, Alltrack, S3, A3, TT-S) Instructions

We need two files, which in some countries are available for free from VW and in others will require some searching to source:

`FL_8V0906259H__0001.frf` - This is the software which is patched to create the "unlocker."

A target file matching your vehicle. This can be the FRF file for your stock box code, or a compatible update file. For US market cars, we recommend update files with the `S50` software structure as we have good definitions and support for this box code:

* US Golf R / S3: `FL_8V0906259K__0003.frf`
* US GTI/A3 2.0: `FL_5G0906259L__0002.frf`
* US 1.8T (Sportwagen, Golf, A3 1.8): `FL_8V0906264K__0003.frf`
* US TT-S: `FL_8S0906259C__0004.frf`

You also need CAN hardware compatible with the application. Three devices are currently approved and recommended:

* Raspberry Pi with Raspbian and Seeed Studios CAN-FD hat. This can also be used as a "bench tool" if things go wrong.
* Macchina A0 with BridgeLEG firmware: https://github.com/Switchleg1/esp32-isotp-ble-bridge/tree/BridgeLEG/main. Supported on all platforms with a working Bluetooth Low Energy system supported by `bleak` .
* Tactrix OpenPort 2.0 and some clones. Easy on Windows, supported with custom drivers on Linux and OSX: https://github.com/bri3d/j2534 .

Other J2534 devices may be supported on Windows, but most (Panda, A0) do not yet support the necessary `stmin_tx` ioctl parameters to allow flashing to complete successfully.

# Installing, building, and running an initial flash process

Install a working C compiler (required for the compression library) and Python3 runtime.

Clone this repository:

`git clone https://github.com/bri3d/VW_Flash`

Install Python3 requirements:

`python3 -mpip install -r requirements.txt` or your preferred Python package installation process.

Build the compressor:

`cd lib/lzss && make`

Ensure you have a `can0` network up on Linux with SocketCAN - or, that you have the OpenPort J2534 DLL installed on Windows.

Flash the Unlock Loader. **After this file is flashed, your car will not start or run - it will be in a Customer Bootloader in Sample Mode, ready to accept the next, unlocked flash file.**

`python3 VW_Flash.py --action flash_unlock --frf FL_8V0906259H__0001.frf`

Check that the Loader was successful:

`python3 VW_Flash.py --action get_ecu_info | grep -a "VW ECU Hardware Version Number"`

You should see the Hardware Version Number change to `X13` from `H13`, meaning your ECU is now in Sample mode.

Now, flash your target FRF (replacing with the correct FRF for your car - very important!):

`python3 VW_Flash.py --action flash_frf --frf frf/FL_8V0906259K__0003.frf --patch-cboot`

And finally, extract the same FRF to find the Calibration to edit:

```
mkdir CurrentSoftware && cd CurrentSoftware
python3 ../VW_Flash.py --action prepare --frf ../frf/FL_8V0906259K__0003.frf 
```

Edit `FD_4.CAL.bin` to your liking with a calibration tool (TunerPro, hex editor, WinOLS, etc.). [a2l2xdf](https://github.com/bri3d/a2l2xdf) will help you in doing this.

Now you can flash a modified calibration - which will automatically fix checksums (CRC32 and ECM2->ECM3 summation):

`python3 VW_Flash.py --action flash_cal --infile CurrentSoftware/FD_4.CAL.bin --block CAL`

# For Simos18.10

Perform the above steps, but replacing `FL_8V0906259H__0001.frf` with `FL_5G0906259Q__0005.frf` and adding the `--simos1810` flag to all commands.

# DSG

All documented processes are supported for DSG using the `--dsg` flag, although currently the block names are not quite correct. To FRF a DSG: `python3 VW_Flash.py --frf FL_DSG_FRF.frf --action flash_bin --dsg` .

To flash a patched calibration: `python3 VW_Flash.py --infile FD_2.DRIVER.bin --block 2 --infile FD_4.CAL.bin --block 4` .

# FRF Extraction

The "prepare" function will extract and checksum binaries from any provided input file, including an FRF. This makes it an easy FRF extraction tool, used like so:

```
mkdir 8V0906259K__0003 && cd 8V0906259K__0003
python3 ../VW_Flash.py --action prepare --frf ../frf/FL_8V0906259K__0003.frf 
```

Will yield either

```
8V0906259K__0003 % ls
FD_0.CBOOT.bin		FD_1.ASW1.bin		FD_2.ASW2.bin		FD_3.ASW3.bin		FD_4.CAL.bin
```

or, if you want to make a single "bin file" compatible with commercial tools:

```
python3 ../VW_Flash.py --action prepare --frf ../frf/FL_8V0906259K__0003.frf --output_bin 8V0906259K__0003.bin
```

This `prepare` method works for all supported files - Simos12, Simos18.10, and DSG files too:

```
mkdir 0D9300012_4938 && cd 0D9300012_4938
python3 ../VW_Flash.py --dsg --action prepare --frf ../frf/FL_0D9300012_4938_RcJQ_sw.frf
```

Yields

```
0D9300012_4938 % ls
FD_2.DRIVER.bin		FD_3.ASW.bin		FD_4.CAL.bin
```

# Notes on the various interfaces that are available:
`--interface J2534` (the default for the GUI) is used to communicate with a J2534 PassThru interface.  Development was done using a Tactrix OpenPort 2 cable (available direct from Tactrix). This interface will connect to a Windows DLL by default, defined in constants.py. With some tweaking and a J2534 shared library like https://github.com/bri3d/j2534 , this can also be made to work on OSX or Linux. Unfortunately due to a quirk of Simos18 control units, flashing with a J2534 cable requires support for the STMIN_TX J2534 IOCTL, which many non-OpenPort devices (like Panda) do not yet support. 

`--interface BLEISOTP` is used to communicate via Bluetooth Low Energy firmware for an ESP32 (Macchina A0), which is available from the following repo: [[https://github.com/Switchleg1/esp32-isotp-ble-bridge/tree/BridgeLEG/main]]

`--interface SocketCAN` (the default for the command-line tools) is used to communicate via the `can0` SocketCAN interface on Linux only.

Other interfaces supported by `python-can` should be fairly easy to add. 

# VW_Flash Use Output

```
usage: VW_Flash.py [-h] --action {checksum,checksum_ecm3,lzss,encrypt,prepare,flash_cal,flash_bin,flash_frf,flash_raw,flash_unlock,get_ecu_info} [--infile INFILE]
                   [--block {CBOOT,1,ASW1,2,ASW2,3,ASW3,4,CAL,5,CBOOT_TEMP,6,PATCH_ASW1,7,PATCH_ASW2,8,PATCH_ASW3,9}] [--frf FRF] [--dsg] [--patch-cboot] [--simos12] [--simos1810] [--simos1841]
                   [--is_early] [--input_bin INPUT_BIN] [--output_bin OUTPUT_BIN] [--interface {J2534,SocketCAN,BLEISOTP,TEST}]

VW_Flash CLI

options:
  -h, --help            show this help message and exit
  --action {checksum,checksum_ecm3,lzss,encrypt,prepare,flash_cal,flash_bin,flash_frf,flash_raw,flash_unlock,get_ecu_info}
                        The action you want to take
  --infile INFILE       the absolute path of an inputfile
  --block {CBOOT,1,ASW1,2,ASW2,3,ASW3,4,CAL,5,CBOOT_TEMP,6,PATCH_ASW1,7,PATCH_ASW2,8,PATCH_ASW3,9}
                        The block name or number
  --frf FRF             An (optional) FRF file to source flash data from
  --dsg                 Perform DSG flash actions
  --patch-cboot         Automatically patch CBOOT into Sample Mode
  --simos12             specify simos12, available for checksumming
  --simos1810           specify simos18.10
  --simos1841           specify simos18.41
  --is_early            specify an early car for ECM3 checksumming
  --input_bin INPUT_BIN
                        An (optional) single BIN file to attempt to parse into flash data
  --output_bin OUTPUT_BIN
                        output a single BIN file, as used by some commercial tools
  --interface {J2534,SocketCAN,BLEISOTP,TEST}
                        specify an interface type

```