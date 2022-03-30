# VW_Flash

VW Flashing Tools over ISO-TP / UDS

Currently supports Continental/Siemens Simos12, Simos18.1/4/6, and Simos18.10 as used in VW AG vehicles, as well as the Temic DQ250-MQB DSG. RSA-bypass/"unlock" patches are provided for Simos 18.1/4/6 (SC8 project identifier) and Simos18.10 (SCG project identifier). 

# Use Information and Documentation

Prebuilt releases for Windows are available at : https://github.com/bri3d/VW_Flash/releases

[docs/windows.md](docs/windows.md) contains detailed setup instructions to use a point and click interface called VW_Flash_GUI to create a "virtual read" and unlock Simos18 for writing unsigned code and calibration.

[docs/cli.md](docs/cli.md) contains documentation about the command line interface VW_Flash. 

# Supported Interface Hardware

* Macchina A0 with BridgeLEG firmware, via both USB-Serial and Bluetooth Low Energy (BLE): https://github.com/Switchleg1/esp32-isotp-ble-bridge . Supported on Windows, Linux, and MacOS.
* Tactrix OpenPort 2.0 J2534. Other J2534 devices are supported, but only if they support the STMIN_TX IOCTL, which many do not. Clones and counterfeits have mixed results. Supported on Windows, possible to make work on Linux/OSX.
* SocketCAN on Linux, including MCP2517 Raspberry Pi Hats, slcan, and other interfaces. 

# Technical Information and Documentation

[docs/docs.md](docs/docs.md) contains detailed documentation about the Simos18 ECU architecture, boot, trust chain, and exploit process, including an exploit chain to enable unsigned code to be injected in ASW.

[docs/patch.md](docs/patch.md) and patch.bin provide a worked example of an ASW patch which "pivots" into an in-memory CBOOT with signature checking turned off (Sample Mode). This CBOOT will write the "Security Keys" / "OK Flags" for another arbitrary CBOOT regardless of signature validity, which will cause this final CBOOT to be "promoted" to the real CBOOT position by SBOOT. In this way a complete persistent trust chain bypass can be installed on a Simos18.1 ECU.

[docs/dsg.md](docs/dsg.md) documents the extremely simple protections applied for the Temic DQ250 DSG.

# Troubleshooting

Feel free to open a GitHub issue, but you MUST include the following 3 files if you want help:

`flash.log` , `flash_details.log`, and `udsoncan.log` . If you don't provide these 3 files (or you take phone pictures of your screen or some other ridiculous thing), I can't help you because I don't have information about what went wrong.

# Contributing

Pull Requests are welcome and appreciated. I will review them as I have time. Code is formatted using `black` - beyond this, there are limited code style and structure rules as the project is still evolving quickly. There are a few file preparation tests to verify basic file extraction and patching functionality, which you can run using python3 -munittest tests/test_prepare.py

# Tools

[VW_Flash.py](VW_Flash.py) provides a complete "port flashing" toolchain - it's a command line interface which has the capability of performing various operations, including fixing checksums for Application Software and Calibration blocks, fixing ECM2->ECM3 monitoring checksums for CAL, encrypting, compressing, and finally, flashing blocks to the ECU. [See the documentation here](docs/cli.md)

[VW_Flash_GUI.py](VW_Flash_GUI.py) provides a WXPython GUI for "simple" flashing of "flash package" containers, full BIN files, and calibration blocks. It also allows unlocking and FRF extraction. [See the documentation here](docs/windows.md)

[TC1791_CAN_BSL](https://github.com/bri3d/TC1791_CAN_BSL) and [Simos18_SBOOT](https://github.com/bri3d/Simos18_SBOOT) together form a complete "bench flashing" toolchain, including a password recovery exploit in SBOOT and a bootstrap loader with the ability to read/write/erase Flash.

[simos_hsl.py](https://github.com/joeFischetti/SimosHighSpeedLogger) , brought to you by `Joedubs`, provides a high-speed logger with support for various backends ($23 ReadMemoryByAddress, $2C DynamicallyDefineLocalIdentifier, and a proprietary $3E patch used by an aftermarket tool). All of these backends require application software patches. 

[sa2-seed-key](https://github.com/bri3d/sa2_seed_key) provides an implementation of the "SA2" Programming Session Seed/Key algorithm for VW Auto Group vehicles. The SA2 script can be found in the ODX flash container for the vehicle. The bytecode from the SA2 script is executed against the Security Access Seed to generate the Security Access Key. This script has been tested against a range of SA2 bytecodes and should be quite robust.

[extractodx.py](extractodx.py) extracts a factory Simos12/Simos18.1/Simos18.10 ODX container to decompressed, decrypted blocks suitable for modification and re-flashing. It supports the "AUDI AES" (0xA) encryption and "AUDI LZSS" (0xA) compression used in Simos ECUs, and the DQ250-MQB encryption scheme used in MQB DSGs. Other ECUs use different flash container mechanisms within ODX files.

[frf](frf) provides an FRF flash container extractor. This should work to extract an ODX from any and all FRF flash containers as the format has not changed since it was introduced.

[a2l2xdf](https://github.com/bri3d/a2l2xdf) provides a method to extract specific definitions from A2L files and convert them to TunerPro XDF files. This is useful to 'cut down' an A2L file into something that's useful for tuning, and get it into a free tuning-focused UI. The `a2l2xdf.csv` in this directory provides a good "getting started" list of data to edit to prepare a basic Simos18.1 tune, as well.

The `lib/lzss` directory contains an implementation of LZSS modified to use the correction dictionary size and window length for Simos18 ECUs. Thanks to `tinytuning` for this.

