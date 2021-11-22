import serial
import esptool


def flash_esp(
    bootloader_path, firmware_path, partition_table_path, port=None, callback=None
):
    try:
        command = []
        if port:
            command.append("--port")
            command.append(port)

        command.extend(
            [
                "--chip",
                "esp32",
                "--baud",
                "921600",
                "--before",
                "default_reset",
                "--after",
                "hard_reset",
                "write_flash",
                "--flash_size",
                "detect",
                "--flash_mode",
                "dio",
                "0x1000",
                bootloader_path,
                "0x10000",
                firmware_path,
                "0x8000",
                partition_table_path,
            ]
        )

        print("Command: esptool.py %s\n" % " ".join(command))

        esptool.main(command)
        if callback:
            callback(100)
        return True
    except serial.SerialException as e:
        print(e)
        return False
