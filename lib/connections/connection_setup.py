import math

from udsoncan.connections import IsoTPSocketConnection
from .fake_connection import FakeConnection

from typing import Union

try:
    from .j2534_connection import J2534Connection
except Exception as e:
    print(e)

from lib import constants


def stmin_to_isotp(st_min):
    if st_min > 1000000:
        # Greater than 1ms; divide by ms and pass through
        return math.ceil(st_min / 1000000)
    hundreds_of_us = math.ceil(st_min / 100000)
    return 0xF0 + hundreds_of_us


# st_min is in us
def connection_setup(
    interface,
    txid,
    rxid,
    interface_path=None,
    st_min: Union[int, None] = 350000,
    dq3xx_hack=False,
):
    if st_min is None:
        st_min = 350000

    params = {"tx_padding": 0x55}

    if interface.startswith("SocketCAN"):
        if interface_path:
            can_interface = interface_path
        else:
            can_interface = interface.split("_")[1]
        conn = IsoTPSocketConnection(can_interface, rxid=rxid, txid=txid, params=params)
        conn.tpsock.set_opts(txpad=0x55, tx_stmin=st_min)
    elif interface == "J2534":
        if interface_path:
            conn = J2534Connection(
                windll=interface_path,
                rxid=rxid,
                txid=txid,
                st_min=stmin_to_isotp(st_min),
            )
        else:
            conn = J2534Connection(
                windll=constants.j2534DLL,
                rxid=rxid,
                txid=txid,
                st_min=stmin_to_isotp(st_min),
            )

    elif interface.startswith("BLEISOTP"):

        from .ble_isotp_connection import BLEISOTPConnection

        if interface_path:
            device_address = interface_path
        else:
            device_address = interface.split("_")[1]
        # tx STMin for this interface is in us.
        interface_name = (
            interface_path if interface_path is not None else "BLE_TO_ISOTP20"
        )
        conn = BLEISOTPConnection(
            ble_service_uuid=constants.BLE_SERVICE_IDENTIFIER,
            ble_notify_uuid="0000abf2-0000-1000-8000-00805f9b34fb",
            ble_write_uuid="0000abf1-0000-1000-8000-00805f9b34fb",
            rxid=rxid,
            txid=txid,
            interface_name=interface_name,
            device_address=device_address,
            tx_stmin=int(st_min / 1000),
            dq3xx_hack=dq3xx_hack,
        )
    elif interface.startswith("USBISOTP"):
        from .usb_isotp_connection import USBISOTPConnection

        if interface_path:
            device_address = interface_path
        else:
            device_address = interface.split("_")[1]

        conn = USBISOTPConnection(
            interface_name=device_address,
            rxid=rxid,
            txid=txid,
            tx_stmin=int(st_min / 1000),
            dq3xx_hack=dq3xx_hack,
        )
    else:
        conn = FakeConnection(testdata=constants.testdata)

    return conn
