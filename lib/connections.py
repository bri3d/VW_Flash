import queue
import threading
import logging
import binascii
import sys
from abc import ABC, abstractmethod
import functools
import time

try:
    from .j2534 import J2534
    from .j2534 import Protocol_ID
    _import_j2534_err = None

except Exception as e:
    _import_j2534_err = e
    print(e)



from udsoncan.Request import Request
from udsoncan.Response import Response
from udsoncan.exceptions import TimeoutException

class BaseConnection(ABC):

    def __init__(self, name=None):
        if name is None:
            self.name = 'Connection'
        else:
            self.name = 'Connection[%s]' % (name)

        self.logger = logging.getLogger(self.name)

    def send(self, data):
        """Sends data to the underlying transport protocol

        :param data: The data or object to send. If a Request or Response is given, the value returned by get_payload() will be sent.
        :type data: bytes, Request, Response

        :returns: None
        """

        if isinstance(data, Request) or isinstance(data, Response):
            payload = data.get_payload()  
        else :
            payload = data

        self.logger.debug('Sending %d bytes : [%s]' % (len(payload), binascii.hexlify(payload) ))
        self.specific_send(payload)

    def wait_frame(self, timeout=2, exception=False):
        """Waits for the reception of a frame of data from the underlying transport protocol

        :param timeout: The maximum amount of time to wait before giving up in seconds
        :type timeout: int
        :param exception: Boolean value indicating if this function may return exceptions.
                When ``True``, all exceptions may be raised, including ``TimeoutException``
                When ``False``, all exceptions will be logged as ``DEBUG`` and ``None`` will be returned.
        :type exception: bool

        :returns: Received data
        :rtype: bytes or None
        """
        try:
            frame = self.specific_wait_frame(timeout=timeout)
        except Exception as e:
            self.logger.debug('No data received: [%s] - %s ' % (e.__class__.__name__, str(e)))

            if exception == True:
                raise
            else:
                frame = None

        if frame is not None:
            self.logger.debug('Received %d bytes : [%s]' % (len(frame), binascii.hexlify(frame) ))
        return frame

    def __enter__(self):
        return self

    @abstractmethod
    def specific_send(self, payload):
        """The implementation of the send method.

        :param payload: Data to send
        :type payload: bytes

        :returns: None
        """
        pass

    @abstractmethod
    def specific_wait_frame(self, timeout=2):
        """The implementation of the ``wait_frame`` method. 

        :param timeout: The maximum amount of time to wait before giving up
        :type timeout: int

        :returns: Received data
        :rtype: bytes or None
        """
        pass

    @abstractmethod
    def open(self):
        """ Set up the connection object. 

        :returns: None
        """
        pass

    @abstractmethod
    def close(self):
        """ Close the connection object

        :returns: None
        """
        pass	

    @abstractmethod
    def empty_rxqueue(self):
        """ Empty all unread data in the reception buffer.

        :returns: None
        """
        pass

    def __exit__(self, type, value, traceback):
        pass



class J2534Connection(BaseConnection):
    """
    Sends and receives data through an J2534 connection using CAN15765. 
    This will only work on a WINDOWS machine with a compatible J2534 interface and DLL installed.

    :param interface: The windows path of the DLL to load
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
    def __init__(self, interface, rxid, txid, name=None, tpsock=None, *args, **kwargs):

        BaseConnection.__init__(self, name)

        self.interface = J2534()
        self.protocol = Protocol_ID.ISO15765
        self.baudrate = 500000


        result, self.devID = self.interface.PassThruOpen()

        if result != 0:
            self.devID = 12345678
            self.opened = True
        else:
            self.opened = True

        self.result, self.firmwareVersion, self.dllVersion, self.apiVersion = self.interface.PassThruReadVersion(self.devID)
        self.result, self.channelID = self.interface.PassThruConnect(self.devID, self.protocol.value, self.baudrate)

        if result != 0:
            self.channelID = 87654321

        self.result = self.interface.PassThruStartMsgFilter(self.channelID, self.protocol.value)

        #below is unused right now
        self.rxid=rxid
        self.txid=txid
        self.rxqueue = queue.Queue()
        self.exit_requested = False

    def open(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def is_open(self):
        return self.opened


    def close(self):
        self.exit_requested = True
        self.rxthread.join()
        self.tpsock.close()
        self.opened = False
        self.logger.info('Connection closed')

    def specific_send(self, payload):
        self.interface.PassThruWriteMsgs(self.channelID, payload)

    def specific_wait_frame(self, timeout=2):
        self.interface.PassThruReadMsgs(self.channelID, 1, timeout)

    def empty_rxqueue(self):
        while not self.rxqueue.empty():
            self.rxqueue.get()
