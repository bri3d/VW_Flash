from udsoncan.connections import BaseConnection
from udsoncan.exceptions import TimeoutException

from contextvars import ContextVar

from bleak import BleakClient
from bleak import BleakScanner

from datetime import datetime, timedelta

import time
import queue
import threading
import asyncio
import logging



class BLEISOTPConnection(BaseConnection):

    def __init__(self, ble_notify_uuid, ble_write_uuid, interface_name, rxid, txid, name=None, debug=False, *args, **kwargs):

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


        self.rxqueue = queue.Queue()
        self.exit_requested = False
        self.opened = False

        #this is the condition used for passing control between the thread running asyncio
        #  and the thread that's trying to get return values from the queue
        self.condition = threading.Condition()

    async def scan_for_ble_devices(self):
        #Get ble devices, we'll go through each one until we find one that
        #  matches the interface_name
        #  await will pause until it's done
        self.device_address = None

        #we'll try a couple times to scan (since the bridge can go dark 
        #if it was recently used and disconncted from)

        for i in range(8):
            self.logger.info("Scanning for BLE bridge, attempt number: " + str(i))
            devices = await BleakScanner.discover()
            self.logger.debug(str(devices))

            for d in devices:
                if d.name == self.interface_name:
                    self.device_address = d.address
                    return
            self.logger.info("BLE device not found, waiting")
            await asyncio.sleep(10)

        if not self.device_address:
            raise RuntimeError("BLE_ISOTP No Device Found")
       


    async def setup(self):

        await self.scan_for_ble_devices()

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
                self.logger.info("Exit requested from BLEISOTP loop")
                await self.client.stop_notify(self.ble_notify_uuid)
                self.logger.debug("stopped notify")
                await self.client.disconnect()
                self.logger.debug("Disconnected from client")
                self.opened = False
                self.logger.debug("Set opened flag to False")

                with self.condition:
                    #Pass control back to the main thread
                    self.condition.notifyAll()

                return self

            #if there's a payload that needs to be sent, write it 
            if self.payload is not None:
 
                #self.payload = bytes([0x22,0xF1,0x90])
                self.logger.debug("Sending payload via write_gatt_char to: " + str(self.ble_write_uuid) + " - " + str(self.payload))
                await self.client.write_gatt_char(self.ble_write_uuid, self.payload)
                self.logger.debug("Sent payload via write_gatt")
                self.payload = None

            #give the notifyhandler a change to be called
            await asyncio.sleep(.001)

            with self.condition:
                #Pass control back to the main thread
                self.condition.notifyAll()


            
        return self

    def asyncio_thread(self):
        #loop = asyncio.get_event_loop()
        loop = asyncio.new_event_loop()
        loop.set_debug(True)

        asyncio.set_event_loop(loop)

        asyncio.run(self.setup()) 

    def open(self):
        self.logger.debug("ble open function called")
        self.txthread = threading.Thread(target=self.asyncio_thread)
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

        while self.opened:

            with self.condition:
                #pass control back to the asyncio thread so that we can hopefully get a notification_handler callback
                self.condition.wait()

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
        #Force a timeout of 2 seconds
        timeout = 2
        if not self.opened:
            raise RuntimeError("BLE_ISOTP Connection is not open")

        timedout = False
        frame = None

        stop_time = datetime.now() + timedelta(seconds = timeout)

        while frame is None:
            if datetime.now() > stop_time:
                raise TimeoutException("Did not receive response from BLE_ISOTP rxqueue (timeout=%s sec)" % timeout)

            with self.condition:
                #pass control back to the asyncio thread so that we can hopefully get a notification_handler callback
                self.condition.wait()
 
            try: 
                frame = self.rxqueue.get(block = False)

            except:
                frame = None


        return frame

    async def async_empty_rxqueue(self):
        #rxqueue = self.rxqueue.get()
        #rxqueue.empty()
        return


    def empty_rxqueue(self):
        asyncio.run(self.async_empty_rxqueue())


