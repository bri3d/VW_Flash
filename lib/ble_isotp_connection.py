from udsoncan.connections import BaseConnection
from udsoncan.exceptions import TimeoutException

from bleak import BleakClient
from bleak import BleakScanner

import time
import queue
import threading
import asyncio

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

        
        asyncio.run(self.setup())


    async def setup(self):
        #Get ble devices, we'll go through each one until we find one that
        #  matches the interface_name
        #  await will pause until it's done
        devices = await BleakScanner.discover()

        for d in devices:
            if d.name == self.interface_name:
                self.device_address = d.address

        self.logger.debug("Found device with address: " + str(self.device_address))

    def txthread_start(self):
        self.logger.debug("Starting thread for ble client connection")
        asyncio.run(self.async_txthread())

        self.exit_requested = False

    async def async_txthread(self):

        self.logger.debug("Attempting to open a connection to: " + str(self.device_address))
        self.client = BleakClient(self.device_address)
        await self.client.connect()

        #Start the notify for our rx characteristic
        await self.client.start_notify(self.ble_notify_uuid, self.notification_handler)
        self.logger.debug("BLE_ISOTP start_notify for uuid: " + str(self.ble_notify_uuid) + " with callback " + str(self.notification_handler))

        #set the opened variable so data can start to be sent 
        self.opened = True
        self.logger.info("BLE_ISOTP Connection opened to: " + str(self.device_address))

        #main tx loop 
        while True:
            #If we've been asked to exit, exit
            if self.exit_requested:
                self.logger.info("Exit requested from BLE_ISOTP loop")
                await self.client.stop_notify(self.ble_notify_uuid)
                return self

            #if there's a payload that needs to be sent, write it 
            if self.payload is not None:
 
                self.payload = bytes([0x22,0xF1,0x90])
                self.logger.debug("Sending payload via write_gatt_char to: " + str(self.ble_write_uuid) + " - " + str(self.payload))
                await self.client.write_gatt_char(self.ble_write_uuid, self.payload)
                await asyncio.sleep(.1)
                self.payload = None

        await self.client.stop_notify(self.ble_notify_uuid)
            
        return self



    def open(self):
        self.txthread = threading.Thread(target=self.txthread_start)
        self.txthread.daemon = True
        self.txthread.start()
       
        return
        
    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        asyncio.run(self.asyncio_close())

    def is_open(self):
        return self.opened

    def notification_handler(self, sender, data):
        self.logger.debug("Received ble: " + str(sender) + " - " + str(data))
        self.rxqueue.put(data)


    #close function that needs to be included - just calls the sync
    #  version
    def close(self):

        self.exit_requested = True
        self.opened = False
        self.logger.info("BLE_ISOTP Connection closed")

    def specific_send(self, payload):
        #payload = self.rxid.to_bytes(4, 'little') + self.txid.to_bytes(4, 'little') + payload


        self.logger.debug("[specific_send] - Sending payload: " + str(payload))

        while self.payload is not None:
            self.logger.debug("Sleeping while prior message is sent")
            time.sleep(1)
        
        self.payload = payload


    def specific_wait_frame(self, timeout=4):
        for i in range(0,4):
            if i == 4:
                raise RuntimeError("BLE_ISOTP Connection is not open")

            if not self.opened:
                self.logger.debug("Sleeping while BLE_ISOTP connection is established")
                time.sleep(3)

        timedout = False
        frame = None
        try:
            frame = self.rxqueue.get(block=True, timeout=timeout)

        except queue.Empty:
            timedout = True

        if timedout:
            raise TimeoutException(
                "Did not received response from BLE_ISOTP RxQueue (timeout=%s sec)"
                % timeout
            )

        return frame

    def empty_rxqueue(self):
        while not self.rxqueue.empty():
            self.rxqueue.get()
