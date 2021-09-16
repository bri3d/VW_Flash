from udsoncan.connections import BaseConnection
from udsoncan.exceptions import TimeoutException

from contextvars import ContextVar

from bleak import BleakClient
from bleak import BleakScanner

import time
import queue
import threading
import asyncio
import logging



class BLEISOTPConnection(BaseConnection):

    def __init__(self, ble_notify_uuid, ble_write_uuid, interface_name, rxid, txid, name=None, debug=False, *args, **kwargs):

        '''This is just a logging config for standalone usage'''
        # create logger
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.DEBUG)
        
        # create console handler and set level to debug
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        
        # add ch to logger
        self.logger.addHandler(ch)
        '''This is the end of the standalone logging config '''

        BaseConnection.__init__(self, name)
        self.txid = txid
        self.rxid = rxid

        # Set up the ble specific propertires
        self.ble_notify_uuid = ble_notify_uuid
        self.ble_write_uuid = ble_write_uuid
        self.interface_name = interface_name
        self.client = None
        self.payload = None

        #print out debug stuff
        self.logger.debug(
            "BLE connection info: "
            + "NOTIFY_UUID: "
            + str(self.ble_notify_uuid)
            + ", WRITE_UUID: "
            + str(self.ble_write_uuid)
            + ", RXID: "
            + str(hex(self.rxid))
            + ", TXID: " 
            + str(hex(self.txid))
        )

        loop = asyncio.get_event_loop()
        loop.set_debug(True)

        
        self.rxqueue = queue.Queue()
        self.exit_requested = False
        self.opened = False

        self.condition = threading.Condition()


    async def setup(self):

        #Get ble devices, we'll go through each one until we find one that
        #  matches the interface_name
        #  await will pause until it's done
        devices = await BleakScanner.discover()
        self.device_address = None

        for d in devices:
            if d.name == self.interface_name:
                self.device_address = d.address
        if not self.device_address:
            raise RuntimeError("BLE_ISOTP No Device Found")

        self.logger.debug("Found device with address: " + str(self.device_address))
        self.logger.debug("Attempting to open a connection to: " + str(self.device_address))

        #Define the BleakClient, and then wait while we connect to it
        self.client = BleakClient(self.device_address)
        await self.client.connect()

        #Once we've gotten this close - we should be connected to it
        #Start the notify for our rx characteristic. Callback should be to a local function that
        #  will stick the response in our rxqueue
        await self.client.start_notify(self.ble_notify_uuid, self.notification_handler)
        self.logger.debug("BLE_ISOTP start_notify for uuid: " + str(self.ble_notify_uuid) + " with callback " + str(self.notification_handler))


        #This is our txthread, we'll log some things as it's set up and then enter the main
        # loop
        self.logger.debug("Starting thread for ble client connection")
        self.exit_requested = False

        #set the opened variable so data can start to be sent 
        self.opened = True
        self.logger.info("BLE_ISOTP Connection opened to: " + str(self.device_address))

        #main tx loop 
        while True:

            #If we've been asked to exit, exit
            if self.exit_requested:
                self.logger.info("Exit requested from BLE_ISOTP loop")
                #await self.client.stop_notify(self.ble_notify_uuid)
                return self

            #if there's a payload that needs to be sent, write it 
            if self.payload is not None:
 
                #self.payload = bytes([0x22,0xF1,0x90])
                self.logger.debug("Sending payload via write_gatt_char to: " + str(self.ble_write_uuid) + " - " + str(self.payload))
                await self.client.write_gatt_char(self.ble_write_uuid, self.payload)
                self.logger.debug("Sent payload via write_gatt")
                self.payload = None
            await asyncio.sleep(.1)

            with self.condition:
                self.condition.notifyAll()


        await self.client.stop_notify(self.ble_notify_uuid)
            
        return self


    def open(self):
        self.logger.debug("ble open function called")
        self.txthread = threading.Thread(target=asyncio.run, args=[self.setup()])
        self.txthread.daemon = True
        self.txthread.start()

        self.logger.debug("Waiting for ble connection to be established")
        while not self.opened:
            time.sleep(1)

        return
        
    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        asyncio.run(self.asyncio_close())

    def is_open(self):
        return self.opened

    def notification_handler(self, sender, data):
        self.logger.debug("Received callback from notify: " + str(sender) + " - " + str(data))
        self.rxqueue.put(data)


    def close(self):
        self.exit_requested = True
        self.opened = False
        self.logger.info("BLE_ISOTP Connection closed")

    def specific_send(self, payload):

        self.logger.debug("[specific_send] - Sending payload: " + str(payload))

        while self.payload is not None:
            self.logger.debug("Sleeping while prior message is sent")
            time.sleep(1)
        
        self.payload = payload

    async def async_wait_frame(self, timeout=4):
        self.logger.debug("In async wait_frame")
        frame = None
        while frame is None:
            frame = self.rxqueue.get(timeout = timeout)

        return frame

    def specific_wait_frame(self, timeout=4):

        if not self.opened:
            raise RuntimeError("BLE_ISOTP Connection is not open")

        timedout = False
        frame = None

        while frame is None:
            with self.condition:
                #self.logger.debug("Waiting for queue to be ready")
                self.condition.wait()
 
            try:
                frame = self.rxqueue.get(block = False)

            except queue.Empty:
                timedout = True

            #if timedout:
            #    raise TimeoutException(
            #        "Did not receive response from BLE_ISOTP RxQueue (timeout=%s sec)"
            #        % timeout
            #    )

        return frame

    async def async_empty_rxqueue(self):
        #rxqueue = self.rxqueue.get()
        #rxqueue.empty()
        return


    def empty_rxqueue(self):
        asyncio.run(self.async_empty_rxqueue())

#txid = 0x7e0
#rxid = 0x7e8
#conn = BLEISOTPConnection(ble_notify_uuid = "0000abf2-0000-1000-8000-00805f9b34fb", ble_write_uuid = "0000abf1-0000-1000-8000-00805f9b34fb", rxid=rxid, txid=txid, interface_name="BLE_TO_ISOTP20")
#
#conn.open()
#
#if conn.opened:
#    conn.send(bytes([0x22,0xF1,0x90]))
#    response = conn.wait_frame()
#    print(response)
#    
#
#
#
#
#
#
#time.sleep(10)
