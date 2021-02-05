import logging
import time
import udsoncan
from typing import List, Union
from tqdm import tqdm
from udsoncan.connections import IsoTPSocketConnection
from udsoncan.client import Client
from udsoncan.client import Routine
from udsoncan import configs
from udsoncan import exceptions
from udsoncan import services

from . import constants 


logger = logging.getLogger('SimosUDS')
consoleLogger = logging.getLogger('SimosUDSPrint')

def next_counter(counter: int) -> int:
    if(counter == 0xFF):
       return 0
    else:
       return (counter + 1)

def flash_block(client: Client, filename: str, data, block_number: int, vin: str, tuner_tag: str = "", callback = None):

  if callback:
    callback(flasher_step = 'FLASHING', flasher_status = "Flashing block..." , flasher_progress = 0)

 
  logger.info(vin + ": Flashing block: " + str(block_number) + " from file " + filename)
  consoleLogger.info("Beginning block flashing process for block " + str(block_number) + " : " + constants.int_to_block_name[block_number] + " - with file named " + filename + " ...")

  if callback:
    callback(flasher_step = 'FLASHING', flasher_status = "Flashing block " + str(block_number), flasher_progress = 0)

 
  consoleLogger.info("Erasing block " + str(block_number) + ", routine 0xFF00...")
  # Erase Flash
  client.start_routine(Routine.EraseMemory, data=bytes([0x1, block_number]))

  if callback:
    callback(flasher_step = 'FLASHING', flasher_status = "Requesting Download for block " + str(block_number), flasher_progress = 0)


  consoleLogger.info("Requesting download for block " + str(block_number) + " of length " + str(constants.block_lengths[block_number]) + " ...")
  # Request Download
  dfi = udsoncan.DataFormatIdentifier(compression=0xA, encryption=0xA)
  memloc = udsoncan.MemoryLocation(block_number, constants.block_lengths[block_number])
  client.request_download(memloc, dfi=dfi)

  if callback:
    callback(flasher_step = 'FLASHING', flasher_status = "Transferring data... " + str(len(data)), flasher_progress = 0)



  consoleLogger.info("Transferring data... " + str(len(data)) + " bytes to write")
  # Transfer Data
  counter = 1
  for block_base_address in tqdm(range(0, len(data), constants.block_transfer_sizes[block_number]), unit_scale=True, unit="B"):
    if callback:
      callback("flasher_step" = 'FLASHING', flasher_status = "Transferring data... ", flasher_progress = (counter * constants.block_transfer_sizes[block_number] / len(data)))

    block_end = min(len(data), block_base_address+constants.block_transfer_sizes[block_number])
    client.transfer_data(counter, data[block_base_address:block_end])
    counter = next_counter(counter)

  if callback:
    callback("flasher_step" = 'FLASHING', flasher_status = "Exiting transfer... ", flasher_progress = 100)
  consoleLogger.info("Exiting transfer...")
  # Exit Transfer
  client.request_transfer_exit()

  if((len(tuner_tag) > 0) and (block_number > 1)):
    consoleLogger.info("Sending tuner ASW magic number...")
    # Send Magic
    # In the case of a tuned CBOOT, send tune-specific magic bytes after this 3E to force-overwrite the CAL validity area.
    def tuner_payload(payload, tune_block_number=block_number):
      return payload + bytes(tuner_tag, "ascii") + bytes([tune_block_number])

    with client.payload_override(tuner_payload):
      client.tester_present()
  else:
    client.tester_present()
  if callback:
    callback("flasher_step" = 'FLASHING', flasher_status = "Checksumming block... ", flasher_progress = 100)

  consoleLogger.info("Checksumming block " + str(block_number) + " , routine 0x0202...")
  # Checksum
  client.start_routine(0x0202, data=bytes([0x01, block_number, 0, 0x04, 0, 0, 0, 0]))

  if callback:
    callback("flasher_step" = 'FLASHING', flasher_status = "Success flashing block... ", flasher_progress = 100)

  logger.info(vin + ": Success flashing block: " + str(block_number) + " with " + filename)
  consoleLogger.info("Successfully flashed " + filename + " to block " + str(block_number))
  

# patch_block takes a block index and subtracts 5 to pick the block to actually patch.
# for example [1: file1, 2: file2, 3: file3, 4: file4, 9: file4_patch, 5: file5]
def patch_block(client: Client, filename: str, data, block_number: int, vin: str):

  block_number = block_number - 5

  consoleLogger.info("Erasing next block for PATCH process - erasing block " + str(block_number + 1) + " to patch " + str(block_number) + " routine 0xFF00...")
  # Erase Flash
  client.start_routine(Routine.EraseMemory, data=bytes([0x1, block_number + 1]))

  logger.info(vin + ": PATCHING block: " + str(block_number) + " with " + filename)
  consoleLogger.info("Requesting download to PATCH block " + str(block_number) + " of length " + str(constants.block_lengths[block_number]) + " using file " + filename + " ...")
  # Request Download
  dfi = udsoncan.DataFormatIdentifier(compression=0x0, encryption=0xA)
  memloc = udsoncan.MemoryLocation(block_number, constants.block_lengths[block_number], memorysize_format=32)
  client.request_download(memloc, dfi=dfi)

  consoleLogger.info("Transferring PATCH data... " + str(len(data)) + " bytes to write")

  # Transfer Data
  counter = 1
  transfer_address = 0
  progress = tqdm(total=len(data), unit="B", unit_scale=True)
  while(transfer_address < len(data)):
    transfer_size = constants.block_transfer_sizes_patch(block_number, transfer_address)
    block_end = min(len(data), transfer_address+transfer_size)
    transfer_data = data[transfer_address:block_end]

    success = False

    while(success == False):
      try:
        client.transfer_data(counter, transfer_data)
        success = True
        progress.update(block_end)
        counter = next_counter(counter)
      except exceptions.NegativeResponseException:
        success = False
        counter = next_counter(counter)

    transfer_address += transfer_size
  progress.close()
  consoleLogger.info("Exiting PATCH transfer...")
  # Exit Transfer
  client.request_transfer_exit()
  consoleLogger.info("PATCH successful.")
  logger.info(vin + ": PATCHED block: " + str(block_number) + " with " + filename)
  

#This is the main entry point
def flash_blocks(block_files, tuner_tag = None, callback = None):
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
  
  consoleLogger.info("Preparing to flash the following blocks:\n" + "\n".join([' = '.join([filename, str(block_files[filename]['blocknum'])]) for filename in block_files])) 
 
  params = {
    'tx_padding': 0x55
  }
  
  def send_obd(data):
    conn2 = IsoTPSocketConnection('can0', rxid=0x7E8, txid=0x700, params=params)
    conn2.tpsock.set_opts(txpad=0x55, tx_stmin=2500000)
    conn2.open()
    conn2.send(data)
    conn2.wait_frame()
    conn2.wait_frame()
    conn2.close()

  conn = IsoTPSocketConnection('can0', rxid=0x7E8, txid=0x7E0, params=params)
  conn.tpsock.set_opts(txpad=0x55, tx_stmin=2500000)


  
  with Client(conn, request_timeout=5, config=configs.default_client_config) as client:
     try:
        if callback:
          callback(flasher_step = 'SETUP', flasher_status = "Clearing DTCs ", flasher_progress = 0)
      
        consoleLogger.info("Sending 0x4 Clear Emissions DTCs over OBD-2")
        send_obd(bytes([0x4]))
        

        client.config['security_algo'] = constants.volkswagen_security_algo
  
        client.config['data_identifiers'] = {}
        for data_record in constants.data_records:
          if(data_record.parse_type == 0):
            client.config['data_identifiers'][data_record.address] = GenericStringCodec
          else:
            client.config['data_identifiers'][data_record.address] = GenericBytesCodec
  
        client.config['data_identifiers'][0xF15A] = GenericBytesCodec
  
        consoleLogger.info("Opening extended diagnostic session...")
        client.change_session(services.DiagnosticSessionControl.Session.extendedDiagnosticSession)
  
        vin_did = constants.data_records[0]
        vin: str = client.read_data_by_identifier_first(vin_did.address)
       
        if callback:
          callback(flasher_step = 'SETUP', flasher_status = "Connected to vehicle with VIN: " + vin, flasher_progress = 0)


        consoleLogger.info("Extended diagnostic session connected to vehicle with VIN: " + vin)
        logger.info(vin + " Connected: Flashing blocks: " + str([block_files[filename]['blocknum'] for filename in block_files]))
  
        consoleLogger.info("Reading ECU information...")
        for i in range(33, 47):
          did = constants.data_records[i]
          response = client.read_data_by_identifier_first(did.address)
          consoleLogger.info(did.description + " : " + response)
          logger.info(vin + " " + did.description + " : " + response)
  
        # Check Programming Precondition
        if callback:
          callback(flasher_step = 'SETUP', flasher_status = "Checking programming precondition" , flasher_progress = 0)

        consoleLogger.info("Checking programming precondition, routine 0x0203...")
        client.start_routine(0x0203)
  
        client.tester_present()
  
        # Upgrade to Programming Session
        if callback:
          callback(flasher_step = 'SETUP', flasher_status = "Upgrading to programming session..." , flasher_progress = 0)

        consoleLogger.info("Upgrading to programming session...")
        client.change_session(services.DiagnosticSessionControl.Session.programmingSession)
  
        # Fix timeouts to work around overly smart library
        client.session_timing['p2_server_max'] = 30
        client.config['request_timeout'] = 30
  
        client.tester_present()

        if callback:
          callback(flasher_step = 'SETUP', flasher_status = "Performing Seed/Key authentication..." , flasher_progress = 0)
  
        # Perform Seed/Key Security Level 17. This will call volkswagen_security_algo above to perform the Seed/Key auth against the SA2 script.
        consoleLogger.info("Performing Seed/Key authentication...")
        client.unlock_security_access(17)
  
        client.tester_present()
  
        consoleLogger.info("Writing flash tool log to LocalIdentifier 0xF15A...")
        # Write Flash Tool Workshop Log (TODO real/fake date/time, currently hardcoded to 2014/7/17)
        client.write_data_by_identifier(0xF15A, bytes([
            0x20, # Year (BCD/HexDecimal since 2000)
            0x7, # Month (BCD)
            0x17, # Day (BCD)
            0x42, # Workshop code
            0x04,
            0x20,
            0x42,
            0xB1,
            0x3D
        ]))
  
        client.tester_present()

        for filename in block_files:
          #pull the relevent filename, blocknum, and binary_data from the dict
          binary_data = block_files[filename]['binary_data']
          blocknum = block_files[filename]['blocknum']

          if blocknum <= 5:
            flash_block(client = client, filename = filename, data = binary_data, block_number = blocknum, vin = vin, callback = callback)
          if blocknum > 5:
            patch_block(client, filename, binary_data, blocknum, vin)

        consoleLogger.info("Verifying programming dependencies, routine 0xFF01...")
        # Verify Programming Dependencies
        client.start_routine(Routine.CheckProgrammingDependencies)
  
        client.tester_present()
  
        # If a periodic task was patched or altered as part of the process, let's give it a few seconds to run
        time.sleep(5)
  
        consoleLogger.info("Rebooting ECU...")
        # Reboot
        client.ecu_reset(services.ECUReset.ResetType.hardReset)
  
        consoleLogger.info("Sending 0x4 Clear Emissions DTCs over OBD-2")
        send_obd(bytes([0x4]))
  
        client.tester_present()
  
        consoleLogger.info("Done!")
     except exceptions.NegativeResponseException as e:
        logger.error('Server refused our request for service %s with code "%s" (0x%02x)' % (e.response.service.get_name(), e.response.code_name, e.response.code))
     except exceptions.InvalidResponseException as e:
        logger.error('Server sent an invalid payload : %s' % e.response.original_payload)
     except exceptions.UnexpectedResponseException as e:
        logger.error('Server sent an invalid payload : %s' % e.response.original_payload)
     except exceptions.TimeoutException as e:
        logger.error('Service request timed out! : %s' % repr(e))
