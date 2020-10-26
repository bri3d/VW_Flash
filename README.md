# VW_Flash
VW Flashing Tools over ISO-TP / UDS

# Current tools
Volkswagen_Security provides an implementation of the "SA2" Seed/Key algorithm for VW Auto Group vehicles. The SA2 script can be found in the ODX flash container for the vehicle. The bytecode from the SA2 script is executed against the Security Access Seed to generate the Security Access Key.

flashsimos18.py provides a rudimentary flasher for the Calibration block in Simos18 ECUs. The supplied BIN file should be pre-compressed and pre-encrypted for now. I have documented the compresssion and encryption here: http://nefariousmotorsports.com/forum/index.php?topic=10364.msg122889#msg122889 .

Please update tuner_tag in flashsimos18 if you have a tuned Simos18 ECU with tuner protection re-enabled in CBOOT and a special 0x3E handler to write the validity flags for your CAL. If you have left tune protection disabled in CBOOT, this is unnecessary.

flashsimos18 requires a working SocketCAN and ISO-TP setup, including the out-of-tree kernel module at https://github.com/hartkopp/can-isotp and properly configured can0 interface. Please check the documentation for your CAN module to learn how to set up the interface.
