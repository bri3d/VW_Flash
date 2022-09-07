#!/usr/bin/env python3

# import datetime so we can put something in the CSV, and import timedelta
# which will help us calculate the time to stop WOT logging
from datetime import datetime, timedelta
from .connections.connection_setup import connection_setup

# yaml is used to define the logged parameters, bytes is for byte stuff, and
#  threading is so we can handle multiple threads (start the reader thread)
#  time is used so I could put pauses in various places
#  argparse is used to handle the argument parser
#  os does various filesystem/path checks
#  logging is used so we can log to an activity log
#  struct is used for some of the floating point conversions from the ECU
import yaml, threading, time, os, logging, socket, struct, random, csv
import json

# import the udsoncan stuff
from udsoncan.client import Client
from udsoncan import configs
from udsoncan import exceptions
from udsoncan import services

try:
    from dashing import *
except:
    print("dashing module not loaded")

class hsl_logger:
    def __init__(
        self,
        runserver=False,
        interactive=False,
        mode="22",
        level=None,
        path="./",
        callback_function=None,
        interface="J2534",
        singlecsv=False,
        interface_path=None
    ):
        #set defaults
        self.activityLogger = logging.getLogger("SimosHSL")
        self.dataStream = {}
        self.datalogging = False
        self.RUNSERVER = runserver
        self.INTERACTIVE = interactive
        self.INTERFACE = interface
        self.INTERFACE_PATH = interface_path
        self.callback_function = callback_function
        self.MODE = mode
        self.FILEPATH = path
        self.stopTime = None
        self.SINGLECSV = singlecsv
        self.CURRENTTIME = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.kill = False
        self.logPrefix = "Logging_"

        # Set up the activity logging
        self.logfile = self.FILEPATH + "simos_hsl.log"
        f_handler = logging.FileHandler(self.logfile)

        if level is not None:
            loglevels = {
                "DEBUG": logging.DEBUG,
                "INFO": logging.INFO,
                "WARNING": logging.WARNING,
                "ERROR": logging.ERROR,
                "CRITICAL": logging.CRITICAL,
            }

            self.activityLogger.setLevel(level)

        else:
            self.activityLogger.setLevel(logging.INFO)

        if self.callback_function:
            self.callback_function(logger_status="Setting up logger")

        f_handler.setLevel(logging.DEBUG)
        c_handler = logging.StreamHandler()

        self.activityLogger.addHandler(f_handler)
        self.activityLogger.addHandler(c_handler)
        self.activityLogger.debug("Current path arg: " + path)
        self.activityLogger.debug("Current filepath: " + self.FILEPATH)
        self.activityLogger.debug("Activity log file: " + self.logfile)
        self.activityLogger.info("Activity log level: " + str(level))

        #open config file
        if self.MODE == "22":
            logType = "22"
        else:
            logType = "3E"
        configuration = {}
        fps = 0
        param_file = "log_parameters_"+logType+".csv"
        self.CONFIGFILE = self.FILEPATH + "log_config.yaml"
        self.activityLogger.info("Configuration file: " + self.CONFIGFILE)
        if os.path.exists(self.CONFIGFILE) and os.access(self.CONFIGFILE, os.R_OK):
            try:
                self.activityLogger.debug("Loading configuration file: " + self.CONFIGFILE)
                with open(self.CONFIGFILE, "r") as configFile:
                    configuration = yaml.safe_load(configFile)

                if "logprefix" in configuration:
                    self.logPrefix = configuration["logprefix"]
                    self.activityLogger.debug("  Logprefix: " + self.logPrefix)

                logType = "Mode" + logType
                if logType in configuration:
                    self.activityLogger.debug("  " + logType)
                    if "fps" in configuration[logType]:
                        fps = configuration[logType]["fps"]
                        self.activityLogger.debug("    FPS: " + str(fps))
                    if "param_file" in configuration[logType]:
                        param_file = configuration[logType]["param_file"]
                        self.activityLogger.debug("    Parameter File: " + param_file)

            except Exception as e:
                self.activityLogger.info("No configuration file loaded: " + str(e))
                configuration = None
        else:
            self.activityLogger.info("No configuration file found")
            configuration = None

        #display current settings
        self.activityLogger.info("Connection type:  " + self.MODE)
        self.activityLogger.info("App server: " + str(self.RUNSERVER))
        self.activityLogger.info("Interactive mode: " + str(self.INTERACTIVE))
        if fps < 1:
            self.delay = 0.0
            self.activityLogger.info("Max frame rate: unlimited")
        else:
            self.delay = 1/fps
            self.activityLogger.info("Max frame rate: " + str(fps))

        #open params file
        self.PARAMFILE = self.FILEPATH + param_file
        self.activityLogger.info("Parameter file: " + self.PARAMFILE)
        self.logParams = {}
        self.three_3ParamList = ""
        self.csvHeader = "Time"
        self.csvDivider = "0"
        pid_counter = 0
        if os.path.exists(self.PARAMFILE) and os.access(self.PARAMFILE, os.R_OK):
            try:
                self.activityLogger.debug("Loading parameters from: " + self.PARAMFILE)
                with open(self.PARAMFILE, "r") as parameterFile:
                    csvParams = csv.DictReader(parameterFile)
                    csv_header = True
                    for param in csvParams:
                        if csv_header:
                            csv_header = False
                        else:
                            param_address = param["Address"].lstrip("0x").lower()
                            if param_address != "ffff" and param_address != "ffffffff":
                                self.logParams[pid_counter] = {}
                                self.logParams[pid_counter]["Name"] = param["Name"]
                                self.logParams[pid_counter]["Address"] = param["Address"]
                                self.logParams[pid_counter]["Length"] = int(param["Length"])
                                self.logParams[pid_counter]["Equation"] = param["Equation"]
                                self.logParams[pid_counter]["Signed"] = bool(param["Signed"])
                                self.logParams[pid_counter]["Value"] = 0.0

                                self.csvHeader += "," + param["Name"]
                                self.csvDivider += ",0"
                                self.activityLogger.debug(
                                    "Logging parameter: "
                                    + param["Name"]
                                    + "|"
                                    + str(param["Address"])
                                    + "|"
                                    + str(param["Length"])
                                )
                                self.three_3ParamList += "0"
                                self.three_3ParamList += str(param["Length"])
                                self.three_3ParamList += param["Address"].lstrip("0x")

                                pid_counter += 1
                                
            except Exception as e:
                self.activityLogger.info("Error loading parameter file: " + str(e))
                exit()
        else:
            self.activityLogger.info("Parameter file not found")
            exit()

        self.activityLogger.info("CSV Header for log files will be: " + self.csvHeader)

        # If we're only going to be writing to a single CSV file, create that file and put the header in it
        if self.SINGLECSV:
            self.filename = (
                self.FILEPATH
                + self.logPrefix
                + self.CURRENTTIME
                + ".csv"
            )
            self.activityLogger.debug("Opening logfile at: " + self.filename)
            self.logFile = open(self.filename, "a")
            self.logFile.write(self.csvHeader + "\n")
            self.logFile.write(self.csvDivider + "\n")
            self.logFile.close()

        #start connection to ecu
        self.conn = connection_setup(self.INTERFACE, txid=0x7E0, rxid=0x7E8, interface_path=self.INTERFACE_PATH)

    def start_logger(self):
        with Client(self.conn, request_timeout=2, config=configs.default_client_config) as client:
            try:
                self.main(client=client)

            except exceptions.NegativeResponseException as e:
                self.activityLogger.critical(
                    'Server refused our request for service %s with code "%s" (0x%02x)'
                    % (
                        e.response.service.get_name(),
                        e.response.code_name,
                        e.response.code,
                    )
                )

            except exceptions.InvalidResponseException as e:
                self.activityLogger.critical(
                    "Server sent an invalid payload : %s"
                    % e.response.original_payload
                )

            except exceptions.UnexpectedResponseException as e:
                self.activityLogger.critical(
                    "Server sent an invalid payload : %s"
                    % e.response.original_payload
                )

            except exceptions.TimeoutException as e:
                self.activityLogger.critical(
                    "Timeout waiting for response on can: " + str(e)
                )

            except Exception as e:
                self.activityLogger.critical("Unhandled exception: " + str(e))
                raise

    def stop(self):
        self.activityLogger.critical("Recieved kill signal")
        if self.callback_function:
            self.callback_function(logger_status="Killing logger process")
        self.kill = True

    def main(self, client=None, callback=None):
        if client is not None:
            if self.MODE != "22":
                memoryOffset = 0xB001E700
                self.payload = {}

                self.payload[memoryOffset] = ""

                maxSize = 0x8F * 2

                while len(self.three_3ParamList) != 0:
                    self.payload[memoryOffset] += self.three_3ParamList[0:2]
                    if len(self.payload[memoryOffset]) >= 0x8F * 2:
                        memoryOffset += 0x8F
                        self.payload[memoryOffset] = ""
                    self.three_3ParamList = self.three_3ParamList[2:]

                    if len(self.three_3ParamList) == 0:
                        self.payload[memoryOffset] += "00"

                hslPrefix = "3E32"
                if self.MODE == "HSL":
                    hslPrefix = "3E02"
                for request in self.payload:
                    fullRequest = (
                        hslPrefix
                        + str(hex(request)).lstrip("0x")
                        + str(hex(int(len(self.payload[request]) / 2)))
                        .lstrip("0x")
                        .zfill(4)
                        + self.payload[request]
                    )
                    self.activityLogger.debug("sending 3E request to set up logging: ")
                    self.activityLogger.debug(fullRequest)
                    results = self.send_raw(bytes.fromhex(fullRequest))
                    self.activityLogger.debug(
                        "Created 3E identifier: " + str(results.hex())
                    )

        try:
            self.activityLogger.info("Starting the data polling thread")
            readData = threading.Thread(target=self.getValuesFromECU)
            readData.daemon = True
            readData.start()
        except (KeyboardInterrupt, SystemExit):
            sys.exit()
        except:
            self.activityLogger.critical("Error starting the data reading thread")

        if self.RUNSERVER is True:
            try:
                streamData = threading.Thread(target=stream_data)
                streamData.daemon = True
                streamData.start()
                self.activityLogger.info("Started data streaming thread")
            except (KeyboardInterrupt, SystemExit):
                sys.exit()
            except:
                self.activityLogger.critical("Error starting data streamer")

        if self.INTERACTIVE is True:
            # Start the loop that listens for the enter key
            while True:
                global datalogging
                log = input()
                self.activityLogger.debug("Input from user: " + log)
                datalogging = not datalogging
                self.activityLogger.debug("Logging is: " + str(datalogging))

        while 1:
            if self.kill:
                del logging.Logger.manager.loggerDict["SimosHSL"]
                exit()
            if self.callback_function:
                self.callback_function(
                    logger_status="Logger Running", dataStream=self.dataStream
                )

            time.sleep(0.2)

    def getValuesFromECU(self):
        self.activityLogger.debug("In the ECU Polling thread")
        self.logFile = None
        self.stopTime = None
        self.activityLogger.info("Starting the ECU poller")

        # Start logging
        while True:
            if self.stopTime is not None:
                if datetime.now() > self.stopTime:
                    self.stopTime = None
                    self.datalogging = False

            if self.MODE == "22":
                self.getParams22()
            else:
                self.getParamsHSL()    

            if self.logFile:
                self.logFile.flush()

            time.sleep(self.delay)

    def writeCSV(self, row):
        self.dataStream = self.dataStreamBuffer
        self.datalogging = True
        self.stopTime = None

        if self.datalogging is True:
            if self.logFile is None:
                if self.SINGLECSV:
                    self.filename = (
                        self.FILEPATH
                        + self.logPrefix
                        + self.CURRENTTIME
                        + ".csv"
                    )
                else:
                    self.filename = (
                        self.FILEPATH
                        + self.logPrefix
                        + datetime.now().strftime("%Y%m%d-%H%M%S")
                        + ".csv"
                    )
                self.activityLogger.debug("Opening logfile at: " + self.filename)
                self.logFile = open(self.filename, "a")
                if not self.SINGLECSV:
                    self.logFile.write(self.csvHeader + "\n")
            self.logFile.write(row + "\n")
            self.activityLogger.debug(row)

    def getParamsHSL(self):
        for address in self.payload:
            if address % 256 == 0:
                loggerPrefix = "3e33"
                loggerSufix = ""
                if self.MODE == "HSL":
                    loggerPrefix = "3e04"
                    loggerSufix = "FFFF"

                requestString = loggerPrefix + str(hex(address)).lstrip("0x") + loggerSufix
                self.activityLogger.debug("Sending request for: " + requestString)
                results = self.send_raw(bytes.fromhex(requestString))

                if results is not None:
                    results = results.hex()
                else:
                    results = "No Response from ECU"
                self.activityLogger.debug(str(results))

                # Make sure the result starts with an affirmative
                if results:
                    self.dataStreamBuffer = {}

                    # Set the datetime for the beginning of the row
                    row = str(datetime.now().time())
                    self.dataStreamBuffer["Time"] = {
                        "value": str(datetime.now().time()),
                        "raw": "",
                    }
                    self.dataStreamBuffer["datalogging"] = {
                        "value": str(self.datalogging),
                        "raw": "",
                    }

                    # Strip off the first 2 bytes so we only have the data
                    results = results[2:]

                    # The data comes back as raw data, so we need the size of each variable and its
                    #  factor so that we can actually parse it.  In here, we'll pull X bytes off the
                    #  front of the result, process it, add it to the CSV row, and then remove it from
                    #  the result
                    for parameter in self.logParams:
                        val = results[: self.logParams[parameter]["Length"] * 2]
                        self.activityLogger.debug(str(parameter) + " raw from ecu: " + str(val))
                        rawval = int.from_bytes(
                            bytearray.fromhex(val),
                            "little",
                            signed=self.logParams[parameter]["Signed"],
                        )
                        self.activityLogger.debug(str(parameter) + " pre-function: " + str(rawval))
                        val = round(
                            eval(
                                self.logParams[parameter]["Equation"],
                                {"x": rawval, "struct": struct},
                            ),
                            2,
                        )
                        row += "," + str(val)
                        self.activityLogger.debug(str(parameter) + " scaling applied: " + str(val))
                        results = results[self.logParams[parameter]["Length"] * 2 :]
                        self.logParams[parameter]["Value"] = val
                        self.dataStreamBuffer[parameter] = {
                            "value": str(val),
                            "raw": str(rawval),
                        }
                    self.writeCSV(row)

    def getParamAddress(self, address):
        for parameter in self.logParams:
            if address == self.logParams[parameter]["Address"].lstrip("0x"):
                return parameter

    def reqParams22(self, parameterString):
        self.activityLogger.debug("Sending: " + parameterString)
        results = ((self.send_raw(bytes.fromhex(parameterString))).hex())
        self.activityLogger.debug("Received: " + results)
        if results.startswith("62"):
            # Strip off the first 2 characters so we only have the data
            results = results[2:]
            while results != "":
                address = results[0:4]
                results = results[4:]
                pid = self.getParamAddress(address)
                if pid is not None:
                    if address == self.logParams[pid]["Address"].lstrip("0x"):
                        pidLength = self.logParams[pid]["Length"] * 2
                        val = results[0: pidLength]
                        results = results[pidLength:]
                        self.activityLogger.debug(self.logParams[pid]["Name"] + " raw from ecu: " + str(val))
                        rawval = int.from_bytes(bytearray.fromhex(val), "big", signed=self.logParams[pid]["Signed"])
                        self.activityLogger.debug(self.logParams[pid]["Name"] + " pre-function: " + str(rawval))
                        val = round(eval(self.logParams[pid]["Equation"], {"x": rawval, "struct": struct}),2)
                        self.logParams[pid]["Value"] = val
                        self.activityLogger.debug(self.logParams[pid]["Name"] + " scaling applied: " + str(val))
                        self.dataStreamBuffer[pid] = {"value": str(val), "raw": str(rawval)}
                else:
                   results = ""

    def getParams22(self):
        self.activityLogger.debug("Getting values via 0x22")
        self.dataStreamBuffer = {}
        
        # Set the datetime for the beginning of the row
        row = str(datetime.now().time())
        self.dataStreamBuffer["Time"] = {"value": str(datetime.now().time()), "raw": ""}
        self.dataStreamBuffer["datalogging"] = {"value": str(self.datalogging), "raw": ""}

        parameterPosition = 0
        parameterString = "22"
        for parameter in self.logParams:
            if parameterPosition < 8:
                parameterString += self.logParams[parameter]["Address"].lstrip("0x")
                parameterPosition += 1
            else:
                self.reqParams22(parameterString)
                parameterPosition = 1
                parameterString = "22" + self.logParams[parameter]["Address"].lstrip("0x")

        if parameterPosition > 0:
            self.reqParams22(parameterString)

        for parameter in self.logParams:
            row += ","+str(self.logParams[parameter]["Value"])

        self.writeCSV(row)

    # A function used to send raw data (so we can create the dynamic identifier etc), since udsoncan can't do it all
    def send_raw(self, data):

        results = None

        while results is None:
            self.conn.send(data)
            results = self.conn.wait_frame(timeout=4)
            if results is None:
                self.activityLogger.critical("No response from ECU")

            if self.kill:
                exit()

        return results

# Stream data over a socket connection.
# Open the socket, and if it happens to disconnect or fail, open it again
# This is used for the android app
def stream_data(callback=None):
    HOST = "0.0.0.0"  # Standard loopback interface address (localhost)
    PORT = 65432  # Port to listen on (non-privileged ports are > 1023)

    while 1:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((HOST, PORT))
                s.listen()
                conn, addr = s.accept()
                activityLogger.info("Listening on " + str(HOST) + ":" + str(PORT))
                with conn:
                    print("Connected by", addr)
                    while True:
                        json_data = json.dumps(dataStream) + "\n"
                        activityLogger.debug("Sending json to app: " + json_data)
                        conn.sendall(json_data.encode())
                        time.sleep(0.1)
        except:
            activityLogger.info("socket closed due to error or client disconnect")
