import sys
import logging
import time
import udsoncan
from . import constants
from . import dtc_handler
from .connections.connection_setup import connection_setup
from datetime import date
from sa2_seed_key.sa2_seed_key import Sa2SeedKey
from typing import List, Union
from udsoncan.client import Client
from udsoncan.client import Routine
from udsoncan import configs
from udsoncan import exceptions
from udsoncan import services
from udsoncan import Dtc

from .workshop_code import WorkshopCodeCodec

from typing import Union

if sys.platform == "win32":
    from .connections.j2534_connection import J2534Connection

logger = logging.getLogger("SimosFlashHistory")
detailedLogger = logging.getLogger("SimosUDSDetail")


def read_data_or_empty(client: Client, didlist):
    try:
        return client.read_data_by_identifier_first(didlist)
    except exceptions.NegativeResponseException as e:
        logger.error(
            'Server refused our request for service %s with code "%s" (0x%02x)'
            % (e.response.service.get_name(), e.response.code_name, e.response.code)
        )
        return ""
    except exceptions.InvalidResponseException as e:
        logger.error(
            "Server sent an invalid payload : %s" % e.response.original_payload
        )
        return ""
    except exceptions.UnexpectedResponseException as e:
        logger.error(
            "Server sent an invalid payload : %s" % e.response.original_payload
        )
        return ""
    except exceptions.TimeoutException as e:
        logger.error("Service request timed out! : %s" % repr(e))
        return ""


def next_counter(counter: int) -> int:
    if counter == 0xFF:
        return 0
    else:
        return counter + 1


def flash_block(
    client: Client,
    filename: str,
    block: constants.PreparedBlockData,
    vin: str,
    flash_info: constants.FlashInfo,
    tuner_tag: str = "",
    callback=None,
):
    block_number = block.block_number
    data = block.block_encrypted_bytes
    block_identifier = flash_info.block_identifiers[block_number]

    logger.info(
        vin + ": Flashing block: " + str(block_number) + " from file " + filename
    )
    detailedLogger.info(
        "Beginning block flashing process for block "
        + str(block_number)
        + " : "
        + block.block_name
        + " - with file named "
        + filename
        + " ..."
    )

    if callback:
        callback(
            flasher_step="FLASHING",
            flasher_status="Erasing block " + str(block_number),
            flasher_progress=0,
        )

    # Erase Flash
    if block.should_erase:
        detailedLogger.info(
            "Erasing block " + str(block_number) + ", routine 0xFF00..."
        )
        client.start_routine(Routine.EraseMemory, data=bytes([0x1, block_identifier]))

    if callback:
        callback(
            flasher_step="FLASHING",
            flasher_status="Requesting Download for block " + str(block_number),
            flasher_progress=0,
        )

    detailedLogger.info(
        "Requesting download for block "
        + str(block_number)
        + " of length "
        + str(flash_info.block_lengths[block_number])
        + " with block identifier: "
        + str(block_identifier)
    )
    # Request Download
    dfi = udsoncan.DataFormatIdentifier(
        compression=block.compression_type, encryption=block.encryption_type
    )
    memloc = udsoncan.MemoryLocation(
        block_identifier,
        flash_info.block_lengths[block_number],
        address_format=8,
        memorysize_format=32,
    )
    client.request_download(memloc, dfi=dfi)

    if callback:
        callback(
            flasher_step="FLASHING",
            flasher_status="Transferring data... " + str(len(data)),
            flasher_progress=0,
        )

    detailedLogger.info("Transferring data... " + str(len(data)) + " bytes to write")
    # Transfer Data
    counter = 1
    for block_base_address in range(
        0, len(data), flash_info.block_transfer_sizes[block_number]
    ):
        block_end = min(
            len(data),
            block_base_address + flash_info.block_transfer_sizes[block_number],
        )
        progress = round(100 * (block_end / len(data)), 1)
        if callback:
            callback(
                flasher_step="FLASHING",
                flasher_status="Transferring data... ",
                flasher_progress=str(progress),
            )

        client.transfer_data(counter, data[block_base_address:block_end])
        counter = next_counter(counter)

    if callback:
        callback(
            flasher_step="FLASHING",
            flasher_status="Exiting transfer... ",
            flasher_progress=100,
        )
    detailedLogger.info("Exiting transfer...")
    # Exit Transfer
    client.request_transfer_exit()

    if (len(tuner_tag) > 0) and (block_number > 1):
        detailedLogger.info("Sending tuner ASW magic number...")
        # Send Magic
        # In the case of a tuned CBOOT, send tune-specific magic bytes after this 3E to force-overwrite the CAL validity area.
        def tuner_payload(payload, tune_block_number=block_number):
            return payload + bytes(tuner_tag, "ascii") + bytes([tune_block_number])

        with client.payload_override(tuner_payload):
            client.tester_present()
    else:
        client.tester_present()
    if callback:
        callback(
            flasher_step="FLASHING",
            flasher_status="Checksumming block... ",
            flasher_progress=100,
        )

    detailedLogger.info(
        "Checksumming block " + str(block_number) + " , routine 0x0202..."
    )
    # Checksum
    checksum_data = bytearray([0x01, block_identifier, 0, 0x4])
    checksum_data.extend(block.uds_checksum)

    client.start_routine(0x0202, data=bytes(checksum_data))

    if callback:
        callback(
            flasher_step="FLASHING",
            flasher_status="Success flashing block... ",
            flasher_progress=100,
        )

    logger.info(
        vin + ": Success flashing block: " + str(block_number) + " with " + filename
    )
    detailedLogger.info(
        "Successfully flashed " + filename + " to block " + str(block_number)
    )


# patch_block takes a block index and subtracts 5 to pick the block to actually patch.
# for example [1: file1, 2: file2, 3: file3, 4: file4, 9: file4_patch, 5: file5]
# This patching process is only useful for Simos ECUs


def patch_block(
    client: Client,
    filename: str,
    block: constants.PreparedBlockData,
    vin: str,
    flash_info: constants.FlashInfo,
    callback=None,
):
    block_number = block.block_number
    block_number = block_number - 5
    data = block.block_encrypted_bytes

    detailedLogger.info(
        "Erasing next block for PATCH process - erasing block "
        + str(block_number + 1)
        + " to patch "
        + str(block_number)
        + " routine 0xFF00..."
    )
    # Erase Flash
    # Hardcoded to erase block 5 (CAL) prior to patch. This means we must ALWAYS flash CAL after patching.

    client.start_routine(Routine.EraseMemory, data=bytes([0x1, 5]))

    logger.info(vin + ": PATCHING block: " + str(block_number) + " with " + filename)
    detailedLogger.info(
        "Requesting download to PATCH block "
        + str(block_number)
        + " of length "
        + str(flash_info.block_lengths[block_number])
        + " using file "
        + filename
        + " ..."
    )
    # Request Download
    dfi = udsoncan.DataFormatIdentifier(compression=0x0, encryption=0xA)
    memloc = udsoncan.MemoryLocation(
        block_number, flash_info.block_lengths[block_number], memorysize_format=32
    )
    client.request_download(memloc, dfi=dfi)

    detailedLogger.info(
        "Transferring PATCH data... " + str(len(data)) + " bytes to write"
    )

    # Transfer Data
    counter = 1
    transfer_address = 0
    while transfer_address < len(data):
        transfer_size = flash_info.patch_info.block_transfer_sizes_patch(
            block_number, transfer_address
        )
        block_end = min(len(data), transfer_address + transfer_size)
        transfer_data = data[transfer_address:block_end]
        if callback:
            progress = transfer_address * 100 / len(data)
            callback(
                flasher_step="PATCHING",
                flasher_status="Patching data... ",
                flasher_progress=str(progress),
            )
        success = False

        while not success:
            try:
                time.sleep(0.025)
                client.transfer_data(counter, transfer_data)
                success = True
                counter = next_counter(counter)
            except exceptions.NegativeResponseException:
                success = False
                counter = next_counter(counter)

        transfer_address += transfer_size
    detailedLogger.info("Exiting PATCH transfer...")
    # Exit Transfer
    client.request_transfer_exit()
    detailedLogger.info("PATCH successful.")
    logger.info(vin + ": PATCHED block: " + str(block_number) + " with " + filename)


# This is the main entry point
def flash_blocks(
    flash_info: constants.FlashInfo,
    block_files: dict[str, constants.PreparedBlockData],
    tuner_tag=None,
    callback=None,
    interface: str = "CAN",
    interface_path: Union[str, None] = None,
    workshop_code=bytes(
        [
            0x20,  # Year (BCD/HexDecimal since 2000)
            0x4,  # Month (BCD)
            0x20,  # Day (BCD)
            0x42,  # Workshop code
            0x04,
            0x20,
            0x42,
            0xB1,
            0x3D,
        ]
    ),
    stmin_override: Union[int, None] = None,
    dq3xx_hack=False,
):
    class GenericStringCodec(udsoncan.DidCodec):
        def encode(self, val):
            return bytes(val)

        def decode(self, payload):
            return str(payload, "ascii")

        def __len__(self):
            raise udsoncan.DidCodec.ReadAllRemainingData

    class GenericBytesCodec(udsoncan.DidCodec):
        def encode(self, val):
            return bytes(val)

        def decode(self, payload):
            return payload.hex()

        def __len__(self):
            raise udsoncan.DidCodec.ReadAllRemainingData

    if callback:
        callback(
            flasher_step="SETUP",
            flasher_status="In Flasher util ",
            flasher_progress=100,
        )
    else:
        detailedLogger.info(
            "No callback function specified, only local feedback provided"
        )

    logger.info(
        "Preparing to flash the following blocks:\n     "
        + "     \n".join(
            [
                " : ".join(
                    [
                        filename,
                        str(block_files[filename].block_number),
                        str(block_files[filename].boxcode),
                    ]
                )
                for filename in block_files
            ]
        )
    )

    def send_obd(data):

        conn2 = connection_setup(
            interface=interface, rxid=0x7E8, txid=0x700, interface_path=interface_path
        )

        conn2.open()
        conn2.send(data)
        conn2.wait_frame()
        conn2.wait_frame()
        conn2.close()

    if callback:
        callback(
            flasher_step="SETUP", flasher_status="Clearing DTCs ", flasher_progress=100
        )

    detailedLogger.info("Sending 0x4 Clear Emissions DTCs over OBD-2")
    send_obd(bytes([0x4]))

    conn = connection_setup(
        interface=interface,
        rxid=flash_info.control_module_identifier.rxid,
        txid=flash_info.control_module_identifier.txid,
        interface_path=interface_path,
        st_min=stmin_override,
        dq3xx_hack=dq3xx_hack,
    )

    with Client(
        conn, request_timeout=5, config=configs.default_client_config
    ) as client:
        try:

            def volkswagen_security_algo(level: int, seed: bytes, params=None) -> bytes:
                vs = Sa2SeedKey(flash_info.sa2_script, int.from_bytes(seed, "big"))
                return vs.execute().to_bytes(4, "big")

            client.config["security_algo"] = volkswagen_security_algo

            client.config["data_identifiers"] = {}
            for data_record in constants.data_records:
                if data_record.parse_type == 0:
                    client.config["data_identifiers"][
                        data_record.address
                    ] = GenericStringCodec
                else:
                    client.config["data_identifiers"][
                        data_record.address
                    ] = GenericBytesCodec

            client.config["data_identifiers"][0xF15A] = GenericBytesCodec

            if callback:
                callback(
                    flasher_step="SETUP",
                    flasher_status="Entering extended diagnostic session... ",
                    flasher_progress=0,
                )

            detailedLogger.info("Opening extended diagnostic session...")
            client.change_session(
                services.DiagnosticSessionControl.Session.extendedDiagnosticSession
            )

            vin_did = constants.data_records[0]
            vin: str = read_data_or_empty(client, vin_did.address)

            if callback:
                callback(
                    flasher_step="SETUP",
                    flasher_status="Connected to vehicle with VIN: " + vin,
                    flasher_progress=100,
                )

            detailedLogger.info(
                "Extended diagnostic session connected to vehicle with VIN: " + vin
            )
            logger.info(
                vin
                + " Connected: Flashing blocks: "
                + str([block_files[filename].block_number for filename in block_files])
            )

            # Check Programming Precondition
            if callback:
                callback(
                    flasher_step="SETUP",
                    flasher_status="Checking programming precondition",
                    flasher_progress=100,
                )

            detailedLogger.info("Checking programming precondition, routine 0x0203...")
            client.start_routine(0x0203)

            client.tester_present()

            # Upgrade to Programming Session
            if callback:
                callback(
                    flasher_step="SETUP",
                    flasher_status="Upgrading to programming session...",
                    flasher_progress=100,
                )

            detailedLogger.info("Upgrading to programming session...")
            client.change_session(
                services.DiagnosticSessionControl.Session.programmingSession
            )

            # Fix timeouts to work around setups which lie about their response speed
            client.session_timing["p2_server_max"] = 30
            client.config["request_timeout"] = 30

            client.tester_present()

            if callback:
                callback(
                    flasher_step="SETUP",
                    flasher_status="Performing Seed/Key authentication...",
                    flasher_progress=100,
                )

            # Perform Seed/Key Security Level 17. This will call volkswagen_security_algo above to perform the Seed/Key auth against the SA2 script.
            detailedLogger.info("Performing Seed/Key authentication...")
            client.unlock_security_access(17)

            client.tester_present()

            if callback:
                callback(
                    flasher_step="SETUP",
                    flasher_status="Writing Workshop data...",
                    flasher_progress=100,
                )

            detailedLogger.info("Writing flash tool log to LocalIdentifier 0xF15A...")

            # Write Flash Tool Workshop Log
            client.write_data_by_identifier(0xF15A, workshop_code)

            client.tester_present()

            for filename in block_files:
                block = block_files[filename]
                blocknum = block.block_number

                if blocknum <= 5:
                    flash_block(
                        client=client,
                        filename=filename,
                        block=block,
                        vin=vin,
                        callback=callback,
                        flash_info=flash_info,
                    )
                if blocknum > 5:
                    patch_block(
                        client=client,
                        filename=filename,
                        block=block,
                        vin=vin,
                        callback=callback,
                        flash_info=flash_info,
                    )

            if callback:
                callback(
                    flasher_step="SETUP",
                    flasher_status="Verifying reprogramming dependencies...",
                    flasher_progress=100,
                )

            detailedLogger.info("Verifying programming dependencies, routine 0xFF01...")
            # Verify Programming Dependencies
            client.start_routine(Routine.CheckProgrammingDependencies)

            client.tester_present()

            # If a periodic task was patched or altered as part of the process, let's give it a few seconds to run
            time.sleep(5)
            if callback:
                callback(
                    flasher_step="SETUP",
                    flasher_status="Finalizing...",
                    flasher_progress=100,
                )

            detailedLogger.info("Rebooting ECU...")
            # Reboot
            client.ecu_reset(services.ECUReset.ResetType.hardReset)

            conn.close()

            detailedLogger.info("Sending 0x4 Clear Emissions DTCs over OBD-2")
            send_obd(bytes([0x4]))

            if callback:
                callback(
                    flasher_step="SETUP",
                    flasher_status="DONE!...",
                    flasher_progress=100,
                )

            detailedLogger.info("Done!")
        except exceptions.NegativeResponseException as e:
            logger.error(
                'Server refused our request for service %s with code "%s" (0x%02x)'
                % (e.response.service.get_name(), e.response.code_name, e.response.code)
            )
        except exceptions.InvalidResponseException as e:
            logger.error(
                "Server sent an invalid payload : %s" % e.response.original_payload
            )
        except exceptions.UnexpectedResponseException as e:
            logger.error(
                "Server sent an invalid payload : %s" % e.response.original_payload
            )
        except exceptions.TimeoutException as e:
            logger.error("Service request timed out! : %s" % repr(e))


def read_dtcs(
    flash_info: constants.FlashInfo,
    interface="CAN",
    callback=None,
    interface_path=None,
    status_mask=None,
):
    if status_mask is None:
        # Try to filter to reasonable failures only.
        status_mask = Dtc.Status(
            test_failed=True,
            test_failed_this_operation_cycle=True,
            pending=False,
            confirmed=True,
            test_not_completed_since_last_clear=False,
            test_failed_since_last_clear=True,
            test_not_completed_this_operation_cycle=False,
            warning_indicator_requested=True,
        )
    conn = connection_setup(
        interface=interface,
        rxid=flash_info.control_module_identifier.rxid,
        txid=flash_info.control_module_identifier.txid,
        interface_path=interface_path,
    )
    with Client(
        conn, request_timeout=5, config=configs.default_client_config
    ) as client:
        if callback:
            callback(
                flasher_step="READING",
                flasher_status="Connected",
                flasher_progress=50,
            )
        client.change_session(
            services.DiagnosticSessionControl.Session.extendedDiagnosticSession
        )
        response = client.get_dtc_by_status_mask(status_mask.get_byte_as_int())
        if callback:
            callback(
                flasher_step="DONE",
                flasher_status="Read " + str(len(response.service_data.dtcs)) + " DTCs",
                flasher_progress=100,
            )
        return dtc_handler.dtcs_to_human(response.service_data.dtcs)


def read_ecu_data(
    flash_info: constants.FlashInfo, interface="CAN", callback=None, interface_path=None
):
    class GenericStringCodec(udsoncan.DidCodec):
        def encode(self, val):
            return bytes(val)

        def decode(self, payload):
            return str(payload, "ascii")

        def __len__(self):
            raise udsoncan.DidCodec.ReadAllRemainingData

    class GenericBytesCodec(udsoncan.DidCodec):
        def encode(self, val):
            return bytes(val)

        def decode(self, payload):
            return payload.hex()

        def __len__(self):
            raise udsoncan.DidCodec.ReadAllRemainingData

    conn = connection_setup(
        interface=interface,
        rxid=flash_info.control_module_identifier.rxid,
        txid=flash_info.control_module_identifier.txid,
        interface_path=interface_path,
    )

    with Client(
        conn, request_timeout=5, config=configs.default_client_config
    ) as client:
        ecuInfo = {}

        client.config["data_identifiers"] = {}
        for data_record in constants.data_records:
            if data_record.parse_type == 0:
                client.config["data_identifiers"][
                    data_record.address
                ] = GenericStringCodec
            elif data_record.parse_type == 2:
                client.config["data_identifiers"][
                    data_record.address
                ] = WorkshopCodeCodec
            else:
                client.config["data_identifiers"][
                    data_record.address
                ] = GenericBytesCodec

        client.config["data_identifiers"][0xF15A] = GenericBytesCodec

        if callback:
            callback(
                flasher_step="READING",
                flasher_status="Entering extended diagnostic session... ",
                flasher_progress=0,
            )

        detailedLogger.info("Opening extended diagnostic session...")
        client.change_session(
            services.DiagnosticSessionControl.Session.extendedDiagnosticSession
        )

        # Fix timeouts to work around setups which lie about their response speed
        client.session_timing["p2_server_max"] = 30
        client.config["request_timeout"] = 30

        vin_did = constants.data_records[0]
        vin: str = read_data_or_empty(client, vin_did.address)

        if callback:
            callback(
                flasher_step="READING",
                flasher_status="Connected to vehicle with VIN: " + vin,
                flasher_progress=100,
            )

        detailedLogger.info(
            "Extended diagnostic session connected to vehicle with VIN: " + vin
        )

        detailedLogger.info("Reading ECU information...")
        for i in range(33, 48):
            did = constants.data_records[i]
            response = read_data_or_empty(client, did.address)
            detailedLogger.info(did.description + " : " + response)
            logger.info(vin + " " + did.description + " : " + response)
            ecuInfo[did.description] = response

        if callback:
            callback(
                flasher_step="READING",
                flasher_status="GET INFO COMPLETE...",
                flasher_progress=100,
            )

        return ecuInfo
