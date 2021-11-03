# VW_Flash

VW Flashing Tools over ISO-TP / UDS

Currently supports Continental/Siemens Simos12, Simos18.1/4/6, and Simos18.10 as used in VW AG vehicles, as well as the Temic DQ250-MQB DSG. RSA-bypass/"unlock" patches are provided for Simos 18.1/4/6 (SC8 project identifier) and Simos18.10 (SCG project identifier). 

# Technical Information and Documentation

[docs/docs.md](docs/docs.md) contains detailed documentation about the Simos18 ECU architecture, boot, trust chain, and exploit process, including an exploit chain to enable unsigned code to be injected in ASW.

[docs/patch.md](docs/patch.md) and patch.bin provide a worked example of an ASW patch which "pivots" into an in-memory CBOOT with signature checking turned off (Sample Mode). This CBOOT will write the "Security Keys" / "OK Flags" for another arbitrary CBOOT regardless of signature validity, which will cause this final CBOOT to be "promoted" to the real CBOOT position by SBOOT. In this way a complete persistent trust chain bypass can be installed on a Simos18.1 ECU.

[docs/dsg.md](docs/dsg.md) documents the extremely simple protections applied for the Temic DQ250 DSG.

# Getting Started

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

Will yield

```
8V0906259K__0003 % ls
FD_0.CBOOT.bin		FD_1.ASW1.bin		FD_2.ASW2.bin		FD_3.ASW3.bin		FD_4.CAL.bin
```

This works for all supported files - Simos12, Simos18.10, and DSG files too:

```
mkdir 0D9300012_4938 && cd 0D9300012_4938
python3 ../VW_Flash.py --dsg --action prepare --frf ../frf/FL_0D9300012_4938_RcJQ_sw.frf
```

Yields

```
0D9300012_4938 % ls
FD_2.DRIVER.bin		FD_3.ASW.bin		FD_4.CAL.bin
```

# Tools

[VW_Flash.py](VW_Flash.py) provides a complete "port flashing" toolchain - it's a command line interface which has the capability of performing various operations, including fixing checksums for Application Software and Calibration blocks, fixing ECM2->ECM3 monitoring checksums for CAL, encrypting, compressing, and finally, flashing blocks to the ECU.

[VW_Flash_GUI.py](VW_Flash_GUI.py) provides a WXPython GUI for "simple" flashing of "flash package" containers and calibration blocks.

[Simos18_SBOOT](https://github.com/bri3d/Simos18_SBOOT) and [TC1791_CAN_BSL](https://github.com/bri3d/TC1791_CAN_BSL) together form a complete "bench flashing" toolchain, including a password recovery exploit in SBOOT and a bootstrap loader with the ability to read/write/erase Flash.

[simos_hsl.py](https://github.com/joeFischetti/SimosHighSpeedLogger) , brought to you by `Joedubs`, provides a high-speed logger with support for various backends ($23 ReadMemoryByAddress, $2C DynamicallyDefineLocalIdentifier, and a proprietary $3E patch used by an aftermarket tool). All of these backends require application software patches. 

[sa2-seed-key](https://github.com/bri3d/sa2_seed_key) provides an implementation of the "SA2" Programming Session Seed/Key algorithm for VW Auto Group vehicles. The SA2 script can be found in the ODX flash container for the vehicle. The bytecode from the SA2 script is executed against the Security Access Seed to generate the Security Access Key. This script has been tested against a range of SA2 bytecodes and should be quite robust.

[extractodx.py](extractodx.py) extracts a factory Simos12/Simos18.1/Simos18.10 ODX container to decompressed, decrypted blocks suitable for modification and re-flashing. It supports the "AUDI AES" (0xA) encryption and "AUDI LZSS" (0xA) compression used in Simos ECUs, and the DQ250-MQB encryption scheme used in MQB DSGs. Other ECUs use different flash container mechanisms within ODX files.

[frf](frf) provides an FRF flash container extractor. This should work to extract an ODX from any and all FRF flash containers as the format has not changed since it was introduced.

[a2l2xdf](https://github.com/bri3d/a2l2xdf) provides a method to extract specific definitions from A2L files and convert them to TunerPro XDF files. This is useful to 'cut down' an A2L file into something that's useful for tuning, and get it into a free tuning-focused UI. The `a2l2xdf.csv` in this directory provides a good "getting started" list of data to edit to prepare a basic Simos18.1 tune, as well.

The `lib/lzss` directory contains an implementation of LZSS modified to use the correction dictionary size and window length for Simos18 ECUs. Thanks to `tinytuning` for this.

# Notes on the various interfaces that are available:
`--interface J2534` (the default for the GUI) is used to communicate with a J2534 PassThru interface.  Development was done using a Tactrix OpenPort 2 cable (available direct from Tactrix). This interface will connect to a Windows DLL by default, defined in constants.py. With some tweaking and a J2534 shared library like https://github.com/bri3d/j2534 , this can also be made to work on OSX or Linux. Unfortunately due to a quirk of Simos18 control units, flashing with a J2534 cable requires support for the STMIN_TX J2534 IOCTL, which many non-OpenPort devices (like Panda) do not yet support. 

`--interface BLEISOTP` is used to communicate via Bluetooth Low Energy firmware for an ESP32 (Macchina A0), which is available from the following repo: [[https://github.com/Switchleg1/esp32-isotp-ble-bridge/tree/BridgeLEG/main]]

`--interface SocketCAN` (the default for the command-line tools) is used to communicate via the `can0` SocketCAN interface on Linux only.

Other interfaces supported by `python-can` should be fairly easy to add. 

# VW_Flash Use Output

```
usage: VW_Flash.py [-h] --action {checksum,checksum_ecm3,lzss,encrypt,prepare,flash_cal,flash_bin,flash_frf,flash_raw,flash_unlock,get_ecu_info} [--infile INFILE]
                   [--block {CBOOT,1,ASW1,2,ASW2,3,ASW3,4,CAL,5,CBOOT_TEMP,6,PATCH_ASW1,7,PATCH_ASW2,8,PATCH_ASW3,9}] [--frf FRF] [--dsg] [--patch-cboot] [--simos12] [--simos1810] [--is_early]
                   [--interface {J2534,SocketCAN, TEST}]

VW_Flash CLI

optional arguments:
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
  --is_early            specify an early car for ECM3 checksumming
  --interface {J2534,SocketCAN,BLEISOTP,TEST}
                        specify an interface type

```


