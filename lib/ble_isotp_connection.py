from udsoncan.connections import BaseConnection
from udsoncan.exceptions import TimeoutException

from bleak import BleakClient
from bleak import BleakScanner

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

        #print out debug stuff
        self.logger.debug(
            "BLE connection info: "
            + "NOTIFY_UUID: "
            + str(self.ble_notify_uuid)
            + ", WRITE_UUID: "
            + str(self.ble_notify_uuid)
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
        devices = await BleakScanner.discover()

        for d in devices:
            if d.name == self.interface_name:
                self.device_address = d.address

        #Start the async loop with the client, and then start notify
        async with BleakClient(self.device_address) as self.client:
            self.logger.info("Connected to ble device using BleakClient")
            await self.client.start_notify(self.ble_notify_uuid, self.notification_handler)


    async def rxthread_task(self):
        await self.client.start_notify(self.ble_notify_uuid, self.notification_handler)

    def open(self):
        
        self.exit_requested = False
        self.opened = True
        self.logger.info("BLE_ISOTP Connection opened to: " + str(self.device_address))
        return self

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        asyncio.run(self.close())

    def is_open(self):
        return self.opened

    def notification_handler(sender, data):
        self.logger.debug("Received ble: " + str(sender) + " - " + str(data))
        self.rxqueue.put(data)


    async def close(self):
        self.exit_requested = True
        self.opened = False
        await self.client.stop_notify(self.ble_notify_uuid)
        self.logger.info("BLE_ISOTP Connection closed")

    def specific_send(self, payload):
        

        payload = self.rxid.to_bytes(4, 'little') + self.txid.to_bytes(4, 'little') + payload

        self.logger.debug("Sending payload: " + str(payload))
        if self.client:
            self.client.write_gatt_char(self.ble_write_uuid, payload)

    def specific_wait_frame(self, timeout=4):
        if not self.opened:
            raise RuntimeError("BLE_ISOTP Connection is not open")

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
