import udsoncan
import volkswagen_security
from udsoncan.connections import IsoTPSocketConnection
from udsoncan.client import Client
from udsoncan import configs
from udsoncan import exceptions
from udsoncan import services

class DataRecord:
  address: int
  parse_type: int
  description:  str
  def __init__(self, address, parse_type, description):
    self.address = address
    self.parse_type = parse_type
    self.description = description

class GenericStringCodec(udsoncan.DidCodec):
  def encode(self, val):
    return bytearray(val)

  def decode(self, payload):
    return str(payload, "ascii")

  def __len__(self):
    raise udsoncan.DidCodec.ReadAllRemainingData

class GenericBytesCodec(udsoncan.DidCodec):
  def encode(self, val):
    return bytearray(val)

  def decode(self, payload):
    return payload.hex()

  def __len__(self):
    raise udsoncan.DidCodec.ReadAllRemainingData

data_records = [
  DataRecord(0xF190, 0, "VIN Vehicle Identification Number"),
  DataRecord(0xF19E, 0, "ASAM/ODX File Identifier"),
  DataRecord(0xF1A2, 0, "ASAM/ODX File Version"),
  DataRecord(0xF40D, 1, "Vehicle Speed"),
  DataRecord(0xF806, 1, "Calibration Verification Numbers"),
  DataRecord(0xF187, 0, "VW Spare Part Number"),
  DataRecord(0xF189, 0, "VW Application Software Version Number"),
  DataRecord(0xF191, 0, "VW ECU Hardware Number"),
  DataRecord(0xF1A3, 0, "VW ECU Hardware Version Number"),
  DataRecord(0xF197,0,"VW System Name Or Engine Type"),
  DataRecord(0xF1AD,0,"Engine Code Letters"),
  DataRecord(0xF1AA,0,"VW Workshop System Name"),
  DataRecord(0x0405,1,"State Of Flash Memory"),
  DataRecord(0x0407,1,"VW Logical Software Block Counter Of Programming Attempts"),
  DataRecord(0x0408,1,"VW Logical Software Block Counter Of Successful Programming Attempts"),
  DataRecord(0x0600,1,"VW Coding Value"),
  DataRecord(0xF186,1,"Active Diagnostic Session"),
  DataRecord(0xF18C,0,"ECU Serial Number"),
  DataRecord(0xF17C,0,"VW FAZIT Identification String"),
  DataRecord(0xF442,1,"Control Module Voltage"),
  DataRecord(0xEF90,1,"Immobilizer Status SHE"),
  DataRecord(0xF1F4,0,"Boot Loader Identification"),
  DataRecord(0xF1DF,1,"ECU Programming Information"),
  DataRecord(0xF1F1,1,"Tuning Protection SO2"),
  DataRecord(0xF1E0,1,""),
  DataRecord(0x12FC,1,""),
  DataRecord(0x12FF,1,""),
  DataRecord(0xFD52,1,""),
  DataRecord(0xFD83,1,""),
  DataRecord(0xFDFA,1,""),
  DataRecord(0xFDFC,1,""),
  DataRecord(0x295A,1,"Vehicle Mileage"),
  DataRecord(0x295B,1,"Control Module Mileage"),
  DataRecord(0xF190,0,"VIN Vehicle Identification Number"),
  DataRecord(0xF19E,0,"ASAM/ODX File Identifier"),
  DataRecord(0xF1A2,0,"ASAM/ODX File Version"),
  DataRecord(0xF15B,1,"Fingerprint and Programming Date"),
  DataRecord(0xF191,0,"VW ECU Hardware Number"),
  DataRecord(0xF1A3,0,"VW ECU Hardware Version Number"),
  DataRecord(0xF187,0,"VW Spare Part Number"),
  DataRecord(0xF189,0,"VW Application Software Version Number"),
  DataRecord(0xF1F4,0,"Boot Loader Identification"),
  DataRecord(0xF197,0,"VW System Name Or Engine Type"),
  DataRecord(0xF1AD,0,"Engine Code Letters"),
  DataRecord(0xF17C,0,"VW FAZIT Identification String"),
  DataRecord(0xF1A5,1,"VW Coding Repair Shop Code Or Serial Number (Coding Fingerprint),"),
  DataRecord(0x0405,1,"State Of Flash Memory"),
  DataRecord(0xF1AB,0,"VW Logical Software Block Version"),
  DataRecord(0xF804,0,"Calibration ID"),
  DataRecord(0xF17E,0,"ECU Production Change Number")
]

def volkswagen_security(self, level, seed, params=None):
  simos18_sa2_script = bytearray([0x68, 0x02, 0x81, 0x4A, 0x10, 0x68, 0x04, 0x93, 0x08, 0x08, 0x20, 0x09, 0x4A, 0x05, 0x87, 0x22, 0x12, 0x19, 0x54, 0x82, 0x49, 0x93, 0x07, 0x12, 0x20, 0x11, 0x82, 0x4A, 0x05, 0x87, 0x03, 0x11, 0x20, 0x10, 0x82, 0x4A, 0x01, 0x81, 0x49, 0x4C])
  vs = volkswagen_security.VolkswagenSecurity(simos18_sa2_script, seed.to_bytes(4, 'big'))
  return vs.execute().to_bytes(4, 'big')

tuner_tag = ""

block_lengths = {
  5: 0x07fc00
}
block_transfer_sizes = {
  5: 0xFFD
}

block_number = 5

data = open("calibration_block.bin", "rb").read()

udsoncan.setup_logging()

params = {
  'tx_padding': 0x55
}

conn = IsoTPSocketConnection('can0', rxid=0x7E8, txid=0x7E0, params=params)
conn.tpsock.set_opts(txpad=0x55, tx_stmin=2500000)

with Client(conn, request_timeout=2, config=configs.default_client_config) as client:
   try:
      client.config['security_algo'] = volkswagen_security

      client.config['data_identifiers'] = {}
      for data_record in data_records:
        if(data_record.parse_type == 0):
          client.config['data_identifiers'][data_record.address] = GenericStringCodec
        else:
          client.config['data_identifiers'][data_record.address] = GenericBytesCodec

      # Open Extended Diagnostic Session
      print("Opening extended diagnostic session...")
      client.change_session(services.DiagnosticSessionControl.Session.extendedDiagnosticSession)

      print("Reading ECU information, first set...")
      for i in range(0, 16):
        did = data_records[i]
        response = client.read_data_by_identifier_first(did.address)
        print(did.description + " : " + response)

      # Check Programming Precondition (load CBOOT)
      print("Checking programming precondition, routine 0x0203...")
      client.start_routine(0x0203)

      print("Reading ECU information, second set...")
      for i in range(16, 32):
        did = data_records[i]
        response = client.read_data_by_identifier_first(did.address)
        print(did.description + " : " + response)

      print("Clearing Emisssions DTCs via OBD-II")
      conn2 = IsoTPSocketConnection('can0', rxid=0x7E8, txid=0x700, params=params)
      conn2.open()
      conn2.send(bytes(0x4))
      conn2.close()

      print("Clearing DTCs...")
      client.control_dtc_setting(udsoncan.services.ControlDTCSetting.SettingType.off, data=bytes([0xFF, 0xFF, 0xFF]))

      client.tester_present()

      # Upgrade to Programming Session
      print("Upgrading to programming session...")
      client.change_session(services.DiagnosticSessionControl.Session.programmingSession)  

      client.tester_present()

      # Perform Seed/Key Security Level 17
      print("Performing Seed/Key authentication...")
      client.unlock_security_access(17)

      print("Writing flash tool log to LocalIdentifier 0xF1...")
      # Write Flash Tool Workshop Log (TODO real/fake date/time)
      client.write_data_by_identifier(0xF1, bytes([
          0x5a,
          0x14,
          0x7,
          0x17,
          0x0,
          0x7,
          0xe6,
          0x2c,
          0x0,
          0x42
      ]))

      print("Erasing block " + str(block_number) + ", routine 0xFF00...")
      # Erase Flash
      client.start_routine(0xFF00, bytes(0x1, block_number))
      
      print("Requesting download for block " + str(block_number) + " of length " + str(block_lengths[block_number]) + " ...")
      # Request Download
      dfi = udsoncan.DataFormatIdentifier(compression=0xA, encryption=0xA)
      memloc = udsoncan.MemoryLocation(block_number, block_lengths[block_number])
      client.request_download(memlock=memloc, dfi=dfi)

      print("Transferring data... " + len(data) + " bytes to write")
      # Transfer Data
      counter = 0
      for block_base_address in range(0, len(data), block_transfer_sizes[block_number]):
        print("Transferring " + block_base_address + " of " + len(data) + " bytes")
        block_end = min(len(data), block_base_address+block_transfer_sizes[block_number])
        client.transfer_data(counter, data[block_base_address:block_end])
        if(counter == 0xFF):
          counter = 0
        else:
          counter += 1
      
      print("Exiting transfer...")
      # Exit Transfer
      client.request_transfer_exit()

      print("Sending tuner ASW magic number...")
      # Send Magic
      # In the case of a tuned ASW, send 6 tune-specific magic bytes after this 3E to force-overwrite the CAL validity area
      def tuner_payload(payload):
        return payload + bytes(tuner_tag)

      with client.payload_override(tuner_payload): 
        client.tester_present()
      
      print("Checksumming block " + block_number + " , routine 0x0202...")
      # Checksum
      client.start_routine(0x0202, data=bytes([0x01, block_number, 0, 0x04, 0, 0, 0, 0]))

      print("Verifying programming dependencies, routine 0xFF01...")
      # Verify Programming Dependencies
      client.start_routine(0xFF01)

      client.tester_present()

      print("Rebooting ECU...")
      # Reboot
      client.ecu_reset(services.ECUReset.ResetType.hardReset)
      
      print("Clearing Emisssions DTCs via OBD-II")
      conn2 = IsoTPSocketConnection('can0', rxid=0x7E8, txid=0x700, params=params)
      conn2.open()
      conn2.send(bytes(0x4))
      conn2.close()

      print("Clearing DTC...")
      client.change_session(services.DiagnosticSessionControl.Session.extendedDiagnosticSession)
      client.tester_present()
      client.control_dtc_setting(udsoncan.services.ControlDTCSetting.SettingType.off, data=bytes([0xFF, 0xFF, 0xFF]))
      
      print("Done!")
   except exceptions.NegativeResponseException as e:
      print('Server refused our request for service %s with code "%s" (0x%02x)' % (e.response.service.get_name(), e.response.code_name, e.response.code))
   except exceptions.InvalidResponseException as e:
      print('Server sent an invalid payload : %s' % e.response.original_payload)
   except exceptions.UnexpectedResponseException as e:
      print('Server sent an invalid payload : %s' % e.response.original_payload)
