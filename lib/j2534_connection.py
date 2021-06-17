from udsoncan.connections import BaseConnection
from udsoncan.exceptions import TimeoutException

import queue
import threading

from .j2534 import J2534
from .j2534 import Protocol_ID
from .j2534 import Ioctl_ID
from .j2534 import Ioctl_Flags
from .j2534 import Ioctl_Parameters
from .j2534 import SCONFIG
from .j2534 import Error_ID

import ctypes


class J2534Connection(BaseConnection):
    """
    Sends and receives data through an ISO-TP socket. Makes cleaner code than SocketConnection but offers no additional functionality.
    The `can-isotp module <https://github.com/pylessard/python-can-isotp>`_ must be installed in order to use this connection

    :param interface: The can interface to use (example: `can0`)
    :type interface: string
    :param rxid: The reception CAN id
    :type rxid: int
    :param txid: The transmission CAN id
    :type txid: int
    :param name: This name is included in the logger name so that its output can be redirected. The logger name will be ``Connection[<name>]``
    :type name: string
    :param tpsock: An optional ISO-TP socket to use instead of creating one.
    :type tpsock: isotp.socket
    :param args: Optional parameters list passed to ISO-TP socket binding method.
    :type args: list
    :param kwargs: Optional parameters dictionary passed to ISO-TP socket binding method.
    :type kwargs: dict

    """

    def __init__(self, dll, rxid, txid, name=None, debug=False, *args, **kwargs):

        BaseConnection.__init__(self, name)
        self.txid = txid
        self.rxid = rxid

        # Set up a J2534 interface using the DLL provided
        self.interface = J2534(dll=dll, rxid=rxid, txid=txid)

        # Set the protocol to ISO15765, Baud rate to 500000
        self.protocol = Protocol_ID.ISO15765
        self.baudrate = 500000

        # Open the interface (connect to the DLL)
        result, self.devID = self.interface.PassThruOpen()

        if debug:
            result = self.interface.PassThruIoctl(
                Handle=0,
                IoctlID=Ioctl_Flags.TX_IOCTL_SET_DLL_DEBUG_FLAGS,
                ioctlInput=Ioctl_Flags.TX_IOCTL_DLL_DEBUG_FLAG_J2534_CALLS,
            )

        # Get the firmeware and DLL version etc, mainly for debugging output
        (
            self.result,
            self.firmwareVersion,
            self.dllVersion,
            self.apiVersion,
        ) = self.interface.PassThruReadVersion(self.devID)
        self.logger.info(
            "J2534 FirmwareVersion: "
            + str(self.firmwareVersion.value)
            + ", dllVersoin: "
            + str(self.dllVersion.value)
            + ", apiVersion"
            + str(self.apiVersion.value)
        )

        # get the channel ID of the interface (used for subsequent communication)
        self.result, self.channelID = self.interface.PassThruConnect(
            self.devID, self.protocol.value, self.baudrate
        )

        # Set the filters and clear the read buffer (filters will be set based on tx/rxids)
        self.result = self.interface.PassThruStartMsgFilter(
            self.channelID, self.protocol.value
        )
        self.result = self.interface.PassThruIoctl(
            self.channelID, Ioctl_ID.CLEAR_RX_BUFFER
        )

        stmin = SCONFIG()
        stmin.Parameter = Ioctl_Parameters.ISO15765_STMIN.value
        stmin.Value = ctypes.c_ulong(0)
        self.result = self.interface.PassThruIoctl(
            Handle=self.channelID, IoctlID=Ioctl_ID.SET_CONFIG, ioctlInput=stmin
        )

        if self.result == Error_ID.ERR_SUCCESS:
            self.logger.info("Set ISO15665_STMIN to 0xF8")
        else:
            self.logger.info("Failed to set ISO15765_STMIN to 0xF8")

        blocksize = SCONFIG()
        blocksize.Parameter = Ioctl_Parameters.ISO15765_BS.value
        stmin.Value = ctypes.c_ulong(0)
        self.result = self.interface.PassThruIoctl(
            Handle=self.channelID, IoctlID=Ioctl_ID.GET_CONFIG, ioctlInput=blocksize
        )

        stmin = SCONFIG()
        stmin.Parameter = Ioctl_Parameters.STMIN_TX.value
        stmin.Value = ctypes.c_ulong(0xF2)
        self.result = self.interface.PassThruIoctl(
            Handle=self.channelID, IoctlID=Ioctl_ID.SET_CONFIG, ioctlInput=stmin
        )

        if self.result == Error_ID.ERR_SUCCESS:
            self.logger.info("Set STMIN_TX to 0xF8")
        else:
            self.logger.info("Failed to set STMIN_TX to 0xF8")

        self.rxqueue = queue.Queue()
        self.exit_requested = False
        self.opened = False

    def resetCable(self):
        self.logger.info("Resetting cable/filter with Txid: " + str(hex(self.txid)))
        self.logger.info("Resetting cable/filter with rxid: " + str(hex(self.rxid)))

        self.result = self.interface.PassThruStartMsgFilter(
            self.channelID, self.protocol.value
        )
        self.result = self.interface.PassThruIoctl(
            self.channelID, Ioctl_ID.CLEAR_RX_BUFFER
        )

    def open(self):
        self.exit_requested = False
        self.rxthread = threading.Thread(target=self.rxthread_task)
        self.rxthread.daemon = True
        self.rxthread.start()
        self.opened = True
        self.logger.info("J2534 Connection opened")
        return self

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def is_open(self):
        return self.opened

    def rxthread_task(self):

        while not self.exit_requested:

            try:
                result, data, numMessages = self.interface.PassThruReadMsgs(
                    self.channelID, self.protocol.value, 1, 1
                )

                if data is not None:
                    self.rxqueue.put(data)
            except Exception:
                self.logger.critical("Exiting J2534 rx thread")
                self.exit_requested = True

    def close(self):
        self.exit_requested = True
        self.rxthread.join()
        result = self.interface.PassThruDisconnect(self.channelID)
        result = self.interface.PassThruClose(self.devID)
        self.opened = False
        self.logger.info("J2534 Connection closed")

    def specific_send(self, payload):
        result = self.interface.PassThruWriteMsgs(
            self.channelID, payload, self.protocol.value
        )

    def specific_wait_frame(self, timeout=4):
        if not self.opened:
            raise RuntimeError("J2534 Connection is not open")

        timedout = False
        frame = None
        try:
            frame = self.rxqueue.get(block=True, timeout=timeout)
            # frame = self.rxqueue.get(block=True, timeout=5)

        except queue.Empty:
            timedout = True

        if timedout:
            raise TimeoutException(
                "Did not received response from J2534 RxQueue (timeout=%s sec)"
                % timeout
            )

        return frame

    def empty_rxqueue(self):
        while not self.rxqueue.empty():
            self.rxqueue.get()
