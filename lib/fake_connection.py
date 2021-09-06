from udsoncan.connections import BaseConnection
from udsoncan.exceptions import TimeoutException

import queue
import threading
import logging


class FakeConnection(BaseConnection):
    def __init__(self, name=None, debug=False, testdata=None, *args, **kwargs):

        BaseConnection.__init__(self, name)

        self.rxqueue = queue.Queue()

        self.exit_requested = False
        self.opened = False

        self.response_data = testdata

    def open(self):
        self.opened = True
        self.logger.info("Fake Connection opened")
        return self

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def is_open(self):
        return self.opened

    def close(self):
        self.exit_requested = True
        self.opened = False
        self.logger.info("Fake Connection closed")

    def get_response_payload(self, payload):
        if payload in self.response_data:
            return self.response_data[payload]

    def specific_send(self, payload):
        self.logger.debug("Received payload: " + str(payload.hex()))
        self.rxqueue.put(self.get_response_payload(payload))

    def specific_wait_frame(self, timeout=4):
        if not self.opened:
            raise RuntimeError("Fake Connection is not open")

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
