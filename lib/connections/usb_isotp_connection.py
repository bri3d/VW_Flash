from udsoncan.connections import BaseConnection
from udsoncan.exceptions import TimeoutException

import serial
import queue
import threading

import sys


class USBISOTPConnection(BaseConnection):
    def __init__(
        self,
        interface_name,
        rxid,
        txid,
        debug=False,
        tx_stmin=None,
        name=None,
        *args,
        **kwargs
    ):

        BaseConnection.__init__(self, name)
        self.txid = txid
        self.rxid = rxid
        self.tx_stmin = tx_stmin

        self.interface_name = interface_name

        # print out debug stuff
        self.logger.debug(
            "USB connection info: "
            + "Interface name: "
            + str(interface_name)
            + "RXID: "
            + str(hex(self.rxid))
            + ", TXID: "
            + str(hex(self.txid))
            + ", TX STMin (usec): "
            + str(self.tx_stmin)
        )

        self.rxqueue = queue.Queue()
        self.exit_requested = False
        self.opened = False

    def set_device_value(self, value_id, payload):
        cmd = bytes([value_id + 0x80])
        self.send_command_packet(cmd, payload)

    def send_command_packet(self, cmd, payload):
        cmd_payload = (
            b"\xF1"
            + cmd
            + self.rxid.to_bytes(2, "little")
            + self.txid.to_bytes(2, "little")
            + len(payload).to_bytes(2, "little")
            + payload
        )
        self.logger.debug("Sending a command packet: " + cmd_payload.hex())
        self.serial.write(cmd_payload)

    def rxthread_task(self):
        self.logger.debug("Started receive queue...")
        while not self.exit_requested:
            try:
                header = self.serial.read(8)  # Read header
                size = header[6:8]
                size = int.from_bytes(size, "little")
                self.logger.debug(
                    "Read header : "
                    + str(header)
                    + " waiting for bytes with size : "
                    + str(size)
                )
                data = self.serial.read(size)
                self.logger.debug("Read data : " + str(data))
                if data is not None:
                    self.rxqueue.put(data)
            except Exception:
                self.logger.info("Exiting USB-ISOTP thread")
                self.exit_requested = True

    def setup(self):
        # override the TRANSMIT STMin. This is the STMin which is used to space out message transmissions, NOT the stmin we send to the ISO-TP partner.
        # F1 -> Header, 0x20 -> "Set TX_STMIN", rxid, txid, size of command (2),
        if self.tx_stmin is not None:
            stmin = self.tx_stmin.to_bytes(2, "little")
            self.set_device_value(0x1, stmin)

    def disconnect(self):
        self.logger.info("Exit requested from USB-ISOTP")
        self.exit_requested = True
        self.serial.close()
        self.opened = False

    def open(self):
        if not self.opened:
            self.logger.debug("USB-ISOTP open function called. Opening serial port...")
            self.serial = serial.Serial(baudrate=250000)
            self.serial.port = self.interface_name
            # I can't explain this but it works. We need to avoid flipping DTR/RTS to avoid putting the A0 in programming mode.
            # But why 0 works on win32 and 1 on osx is anyone's guess.
            if sys.platform == "win32":
                self.serial.dtr = 0
                self.serial.rts = 0
            else:
                self.serial.dtr = 1
                self.serial.rts = 1
            self.serial.open()

            self.setup()

            self.rxthread = threading.Thread(target=self.rxthread_task)
            self.rxthread.daemon = True
            self.rxthread.start()

            self.opened = True

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.disconnect()

    def is_open(self):
        return self.opened

    def close(self):
        self.disconnect()

    def specific_send(self, payload):
        self.logger.debug("TXID: " + str(self.txid.to_bytes(2, "little")))
        self.logger.debug("RXID: " + str(self.rxid.to_bytes(2, "little")))

        header = (
            b"\xF1\x00"
            + self.rxid.to_bytes(2, "little")
            + self.txid.to_bytes(2, "little")
            + len(payload).to_bytes(2, "little")
        )

        self.logger.debug(header)
        payload = header + payload
        self.serial.write(payload)

    def specific_wait_frame(self, timeout=None):
        timeout = 10
        if not self.opened:
            raise RuntimeError("USB-ISOTP Connection is not open")
        try:
            frame = self.rxqueue.get(block=True, timeout=timeout)
        except queue.Empty:
            raise TimeoutException(
                "Did not receive frame from user queue in time (timeout=%s sec)"
                % timeout
            )
            frame = None
        return frame

    def empty_rxqueue(self):
        self.rxqueue.empty()
