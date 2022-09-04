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
#  smtplib, ssl, and socket are all used in support of sending email
#  struct is used for some of the floating point conversions from the ECU
import yaml, threading, time, os, logging, smtplib, ssl, socket, struct, random
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
        interface_path=None,
    ):

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
        self.configuration = {}
        self.defineIdentifier = None
        self.SINGLECSV = singlecsv
        self.CURRENTTIME = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.kill = False

        # Set up the activity logging
        self.logfile = self.FILEPATH + "activity_" + self.CURRENTTIME + ".log"

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

        self.logParams = None

        self.activityLogger.addHandler(f_handler)
        self.activityLogger.addHandler(c_handler)

        self.activityLogger.debug("Current path arg: " + path)
        self.activityLogger.debug("Current filepath: " + self.FILEPATH)
        self.activityLogger.debug("Activity log file: " + self.logfile)
        self.activityLogger.info("Activity log level: " + str(level))

        self.activityLogger.info("Connection type:  " + self.MODE)
        self.activityLogger.info("App server: " + str(self.RUNSERVER))
        self.activityLogger.info("Interactive mode: " + str(self.INTERACTIVE))

        self.PARAMFILE = self.FILEPATH + "parameters.yaml"
        self.activityLogger.info("Parameter file: " + self.PARAMFILE)

        self.CONFIGFILE = self.FILEPATH + "config.yaml"
        self.activityLogger.info("Configuration file: " + self.CONFIGFILE)
        self.conn = connection_setup(self.INTERFACE, txid=0x7E0, rxid=0x7E8, interface_path=self.INTERFACE_PATH)

        # try to open the parameter file, if we can't, we'll work with a static
        #  list of logged parameters for testing
        if os.path.exists(self.PARAMFILE) and os.access(self.PARAMFILE, os.R_OK):
            try:
                self.activityLogger.debug("Loading parameters from: " + self.PARAMFILE)
                with open(self.PARAMFILE, "r") as parameterFile:
                    self.logParams = yaml.safe_load(parameterFile)
            except:
                self.activityLogger.info(
                    "No parameter file found, or can't load file, setting defaults"
                )
                exit()

        if os.path.exists(self.CONFIGFILE) and os.access(self.CONFIGFILE, os.R_OK):
            try:
                self.activityLogger.debug(
                    "Loading configuration file: " + self.CONFIGFILE
                )
                with open(self.CONFIGFILE, "r") as configFile:
                    self.configuration = yaml.safe_load(configFile)

            except Exception as e:
                self.activityLogger.info("No configuration file loaded: " + str(e))
                self.configuration = None
        else:
            self.activityLogger.info("No configuration file found")
            self.configuration = None

        # Build the dynamicIdentifier request
        if self.logParams is not None:
            self.defineIdentifier = "2C02F20014"
            self.three_3ParamList = ""
            self.csvHeader = "Time"
            self.csvDivider = "0"
            for param in self.logParams:
                self.csvHeader += "," + param
                self.csvDivider += ",0"
                self.activityLogger.debug(
                    "Logging parameter: "
                    + param
                    + "|"
                    + str(self.logParams[param]["location"])
                    + "|"
                    + str(self.logParams[param]["length"])
                )
                self.defineIdentifier += self.logParams[param]["location"].lstrip("0x")
                self.defineIdentifier += "0"
                self.defineIdentifier += str(self.logParams[param]["length"])
                self.three_3ParamList += "0"
                self.three_3ParamList += str(self.logParams[param]["length"])
                self.three_3ParamList += self.logParams[param]["location"].lstrip("0x")

        self.activityLogger.info("CSV Header for log files will be: " + self.csvHeader)

        # If we're only going to be writing to a single CSV file, create that file and put the header in it
        if self.SINGLECSV:
            self.filename = (
                self.FILEPATH
                + self.configuration["logprefix"]
                + "_Logging_"
                + self.CURRENTTIME
                + ".csv"
            )

            self.activityLogger.debug("Opening logfile at: " + self.filename)
            self.logFile = open(self.filename, "a")
            self.logFile.write(self.csvHeader + "\n")
            self.logFile.write(self.csvDivider + "\n")
            self.logFile.close()

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
        # Define the global variables that we'll use...  They're the logging parameters
        # and the boolean used for whether or not we should be logging

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

            # time.sleep(0.05)

    def writeCSV(self):
        self.dataStream = self.dataStreamBuffer
        self.datalogging = True
        self.stopTime = None

        if self.datalogging is True:
            if self.logFile is None:
                if "logprefix" in self.configuration:
                    if self.SINGLECSV:
                        self.filename = (
                            self.FILEPATH
                            + self.configuration["logprefix"]
                            + "_Logging_"
                            + self.CURRENTTIME
                            + ".csv"
                        )
                    else:
                        self.filename = (
                            self.FILEPATH
                            + self.configuration["logprefix"]
                            + "_Logging_"
                            + datetime.now().strftime("%Y%m%d-%H%M%S")
                            + ".csv"
                        )
                else:
                    if self.SINGLECSV:
                        self.filename = (
                            self.FILEPATH
                            + "Logging_"
                            + self.CURRENTTIME
                            + ".csv"
                        )
                    else:
                        self.filename = (
                            self.FILEPATH
                            + "Logging_"
                            + datetime.now().strftime("%Y%m%d-%H%M%S")
                            + ".csv"
                                    )
                self.activityLogger.debug(
                    "Opening logfile at: " + self.filename
                )
                self.logFile = open(self.filename, "a")
                if not self.SINGLECSV:
                    self.logFile.write(self.csvHeader + "\n")
            self.logFile.write(row + "\n")

    def getParamsHSL(self):
        for address in self.payload:
            if address % 256 == 0:
                self.activityLogger.debug("Sending request for: " + str(hex(address)))

                loggerPrefix = "3e33"
                if self.MODE == "HSL":
                    loggerSyntax = "3e04"
                results = self.send_raw(bytes.fromhex(loggerPrefix + str(hex(address)).lstrip("0x")))

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
                        val = results[: self.logParams[parameter]["length"] * 2]
                        self.activityLogger.debug(
                            str(parameter) + " raw from ecu: " + str(val)
                        )
                        rawval = int.from_bytes(
                            bytearray.fromhex(val),
                            "little",
                            signed=self.logParams[parameter]["signed"],
                        )
                        self.activityLogger.debug(
                            str(parameter) + " pre-function: " + str(rawval)
                        )
                        val = round(
                            eval(
                                self.logParams[parameter]["function"],
                                {"x": rawval, "struct": struct},
                            ),
                            2,
                        )
                        row += "," + str(val)
                        self.activityLogger.debug(
                            str(parameter) + " scaling applied: " + str(val)
                        )

                        results = results[self.logParams[parameter]["length"] * 2 :]

                        self.dataStreamBuffer[parameter] = {
                            "value": str(val),
                            "raw": str(rawval),
                        }
        writeCSV()

    def getParamAddress(self, address):
        for parameter in self.logParams:
            if address == self.logParams[parameter]["location"].lstrip("0x"):
                return parameter

    def reqParams22(self, parameterString):
        global logParams
       
        results = ((self.send_raw(bytes.fromhex(parameterString))).hex())
        if results.startswith("62"):
            # Strip off the first 2 characters so we only have the data
            results = results[2:]

            while results != "":
                address = results[0:4]
                results = results[4:]
                pid = getParamAddress(address)
                if pid is not None:
                    if address == self.logParams[pid]["location"].lstrip("0x"):
                        pidLength = self.logParams[pid]["length"] * 2
                        val = results[0: pidLength]
                        results = results[pidLength:]
                        self.activityLogger.debug(str(pid) + " raw from ecu: " + str(val))
                        rawval = int.from_bytes(bytearray.fromhex(val), "big", signed=self.logParams[pid]["signed"])
                        self.activityLogger.debug(str(pid) + " pre-function: " + str(rawval))
                        val = round(eval(self.logParams[pid]["function"], {"x": rawval, "struct": struct}),2,)
                        row += "," + str(val)
                        self.activityLogger.debug(str(pid) + " scaling applied: " + str(val))
                        self.dataStreamBuffer[pid] = {"value": str(val), "raw": str(rawval)}
                else:
                   results = "" 

    def getParams22(self):
        global logParams
        global datalogging
        global HEADLESS
        global filepath
        global dataStream
        global logFile
        global stopTime

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
                parameterString += self.logParams[parameter]["location"].lstrip("0x")
                parameterPosition += 1
            else:
                reqParams22(parameterString)
                parameterPosition = 1
                parameterString = "22" + self.logParams[parameter]["location"].lstrip("0x")

        if parameterPosition > 0:
            reqParams22(parameterString)

        writeCSV()

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
