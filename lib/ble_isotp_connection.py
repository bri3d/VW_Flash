from udsoncan.connections import BaseConnection

from bleak import BleakClient
from bleak import BleakScanner

import queue
import threading
import asyncio


class BLEISOTPConnection(BaseConnection):

    def __init__(self, ble_notify_uuid, ble_write_uuid, interface_name, rxid, txid, name=None, debug=False, device_address = None, tx_stmin = None, *args, **kwargs):

        BaseConnection.__init__(self, name)
        self.txid = txid
        self.rxid = rxid
        self.tx_stmin = tx_stmin

        # Set up the ble specific propertires
        self.ble_notify_uuid = ble_notify_uuid
        self.ble_write_uuid = ble_write_uuid
        self.interface_name = interface_name
        self.client = None
        self.payload = None
        self.device_address = device_address

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
            + ", TX STMin (usec): "
            + str(self.tx_stmin)
        )


        self.rxqueue = queue.Queue()
        # We take this lock to wait on the main thread for the asyncio/coroutine thread to finish opening up the device. 
        self.connection_open_lock = threading.Condition()
        self.exit_requested = False
        self.opened = False

    async def scan_for_ble_devices(self):
        #Get ble devices, we'll go through each one until we find one that
        #  matches the interface_name
        #  await will pause until it's done

        #we'll try a couple times to scan (since the bridge can go dark 
        #if it was recently used and disconncted from)
        if(self.device_address is None):
            for i in range(8):
                self.logger.info("Scanning for BLE bridge, attempt number: " + str(i))
                devices = await BleakScanner.discover()

                for d in devices:
                    self.logger.debug("Found: " + str(d))
                    if d.name == self.interface_name:
                        self.device_address = d.address
                        return
                self.logger.info("BLE device not found, waiting")
                await asyncio.sleep(10)

            if not self.device_address:
                raise RuntimeError("BLE_ISOTP No Device Found")
       
            self.logger.debug("Found device with address: " + str(self.device_address))

    async def send_command_packet(self, cmd, payload):
        cmd_payload = b'\xF1' + cmd + self.rxid.to_bytes(2, 'little') + self.txid.to_bytes(2, 'little') + len(payload).to_bytes(2, 'little') + payload
        self.logger.debug("Sending a command packet: " + cmd_payload.hex())
        await self.client.write_gatt_char(self.ble_write_uuid, cmd_payload)

    async def setup(self):
        self.txqueue = asyncio.Queue()
        await self.scan_for_ble_devices()

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

        #override the TRANSMIT STMin. This is the STMin which is used to space out message transmissions, NOT the stmin we send to the ISO-TP partner.
        # F1 -> Header, 0x20 -> "Set TX_STMIN", rxid, txid, size of command (2), 
        if self.tx_stmin is not None:
            stmin = self.tx_stmin.to_bytes(2, 'little')
            await self.send_command_packet(bytes([0x20]), stmin)

        with self.connection_open_lock:
            self.connection_open_lock.notifyAll()
        #main tx loop 
        while True:
            #If we've been asked to exit, exit
            if self.exit_requested:
                return self
            #if there's a payload that needs to be sent, write it 
            payload: bytes = await self.txqueue.get()
            self.logger.debug("Sending payload via write_gatt_char to: " + str(self.ble_write_uuid) + " - " + str(payload.hex()))
            await self.client.write_gatt_char(self.ble_write_uuid, payload)
            self.logger.debug("Sent payload via write_gatt")

    async def disconnect(self):
        self.logger.info("Exit requested from BLEISOTP loop")
        await self.client.stop_notify(self.ble_notify_uuid)
        self.logger.debug("stopped notify")
        await self.client.disconnect()
        self.logger.debug("Disconnected from client")
        self.opened = False
        self.logger.debug("Set opened flag to False")

    def asyncio_thread(self):
        self.txloop = asyncio.new_event_loop()
        self.txloop.set_debug(True)
        asyncio.set_event_loop(self.txloop)
        asyncio.run_coroutine_threadsafe(self.setup(), self.txloop)
        self.txloop.run_forever()

    def open(self):
        self.logger.debug("ble open function called")
        self.txthread = threading.Thread(target=self.asyncio_thread)
        self.txthread.daemon = True
        self.txthread.start()

        self.logger.debug("Waiting for ble connection to be established")
        with self.connection_open_lock:
            self.connection_open_lock.wait_for(self.is_open)

        return
        
    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        asyncio.run(self.asyncio_close())

    def is_open(self):
        return self.opened

    def notification_handler(self, sender, data):
        self.logger.debug("Received callback from notify: " + str(sender) + " - " + str(data))
        self.rxqueue.put(data[8:])

    def close(self):
        self.exit_requested = True
        asyncio.run_coroutine_threadsafe(self.disconnect(), self.txloop)
        self.logger.info("BLE_ISOTP Connection closed")

    def specific_send(self, payload):
        self.logger.debug("TXID: " + str(self.txid.to_bytes(2, 'little')))
        self.logger.debug("RXID: " + str(self.rxid.to_bytes(2, 'little')))

        header = b'\xF1\x00' + self.rxid.to_bytes(2, 'little') + self.txid.to_bytes(2, 'little') + len(payload).to_bytes(2, 'little')

        self.logger.debug(header)
        payload = header + payload

        self.logger.debug("[specific_send] - Sending payload: " + str(payload.hex()))
        self.logger.debug("[specific-send] - TOTAL payload length is: " + str(len(payload)))

        if len(payload) > 0x150:
            payload = b'\xF1\x08' + payload[2:]
            sequence = 0
            
            self.logger.debug("[specific-send] - Breaking payload into smaller chunks for multiframe send")
            while(len(payload) > 0):
                if sequence == 0:
                    asyncio.run_coroutine_threadsafe(self.txqueue.put(payload[0:0x150]), self.txloop)
                    payload = payload[0x150:]
                    sequence += 1
                else:
                    self.logger.debug("[specific_send] - multiframe_queue size: " + str(self.txqueue.qsize()))
                    asyncio.run_coroutine_threadsafe(self.txqueue.put(b'\xF2' + sequence.to_bytes(1, 'little') + payload[0:0x150-2]), self.txloop)
                    sequence += 1
                    payload = payload[0x150 - 2:]

            self.logger.debug("Done enqueuing multiframe payload")
            return

        else:
            asyncio.run_coroutine_threadsafe(self.txqueue.put(payload), self.txloop)

    async def async_wait_frame(self, timeout=4):
        self.logger.debug("In async wait_frame")
        frame = None
        while frame is None:
            frame = self.rxqueue.get(timeout = timeout)

        return frame

    def specific_wait_frame(self, timeout=4):
        timeout = 10
        if not self.opened:
            raise RuntimeError("BLE_ISOTP Connection is not open")
        try: 
            frame = self.rxqueue.get(block = True, timeout = timeout)
        except:
            frame = None
        return frame

    async def async_empty_rxqueue(self):
        #rxqueue = self.rxqueue.get()
        #rxqueue.empty()
        return


    def empty_rxqueue(self):
        asyncio.run(self.async_empty_rxqueue())


