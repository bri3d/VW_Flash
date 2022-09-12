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
import yaml, threading, time, os, logging, socket, struct, random, csv, json, shutil

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
        runServer=False,
        interactive=False,
        mode="22",
        level=None,
        path="./",
        callbackFunction=None,
        interface="J2534",
        singleCSV=False,
        interfacePath=None,
        displayGauges=False
    ):
        #set defaults
        self.activityLogger = logging.getLogger("SimosHSL")
        self.dataStream = {}
        self.runServer = runServer
        self.interactive = interactive
        self.interface = interface
        self.interfacePath = interfacePath
        self.callbackFunction = callbackFunction
        self.mode = mode
        self.filePath = path
        self.singleCSV = singleCSV
        self.currentTime = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.kill = False
        self.logPrefix = "Logging_"
        self.displayGauges = displayGauges
        self.dataRow = None
        self.isLogging = False
        self.isPIDTriggered = False
        self.isKeyTriggered = False
        self.logTrigger = ""

        # Set up the activity logging
        self.logfile = self.filePath + "simos_hsl.log"
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

        if self.callbackFunction:
            self.callbackFunction(logger_status="Setting up logger")

        f_handler.setLevel(logging.DEBUG)
        self.activityLogger.addHandler(f_handler)
        self.activityLogger.debug("Current path arg: " + path)
        self.activityLogger.debug("Current filepath: " + self.filePath)
        self.activityLogger.debug("Activity log file: " + self.logfile)
        self.activityLogger.info("Activity log level: " + str(level))

        #open config file
        if self.mode == "22":
            logType = "22"
        else:
            logType = "3E"
        configuration = {}
        fps = 0
        param_file = "log_parameters_"+logType+".csv"
        self.CONFIGFILE = self.filePath + "log_config.yaml"
        self.activityLogger.info("Configuration file: " + self.CONFIGFILE)
        if os.path.exists(self.CONFIGFILE) and os.access(self.CONFIGFILE, os.R_OK):
            try:
                self.activityLogger.debug("Loading configuration file: " + self.CONFIGFILE)
                with open(self.CONFIGFILE, "r") as configFile:
                    configuration = yaml.safe_load(configFile)

                if "Log Prefix" in configuration:
                    self.activityLogger.debug("  Log Prefix: " + self.logPrefix)
                    self.logPrefix = str(configuration["Log Prefix"])

                if "Allow Display" in configuration:
                    self.activityLogger.debug("  Allow Display: " + str(configuration["Allow Display"]))
                    if bool(configuration["Allow Display"]) == False:
                        self.displayGauges = False

                if "Log Trigger" in configuration:
                    self.activityLogger.debug("  Log Trigger: " + str(configuration["Log Trigger"]))
                    self.logTrigger = str(configuration["Log Trigger"])

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
        self.activityLogger.info("Logging mode:  " + self.mode)
        self.activityLogger.info("Data server: " + str(self.runServer))
        self.activityLogger.info("Interactive mode: " + str(self.interactive))
        if fps < 1:
            self.delay = 0.0
            self.activityLogger.info("Max frame rate: unlimited")
        else:
            self.delay = 1/fps
            self.activityLogger.info("Max frame rate: " + str(fps))
        self.activityLogger.info("Display Gauges: " + str(self.displayGauges))
        self.activityLogger.info("Log Trigger: " + str(self.logTrigger))

        #open params file
        self.PARAMFILE = self.filePath + param_file
        self.activityLogger.info("Parameter file: " + self.PARAMFILE)
        self.logParams = {}
        self.assignments = {}
        self.assignmentValues = {}
        self.csvHeader = "Time"
        self.csvDivider = "0"
        pid_counter = 0
        if os.path.exists(self.PARAMFILE) and os.access(self.PARAMFILE, os.R_OK):
            try:
                self.activityLogger.debug("Loading parameters from: " + self.PARAMFILE)
                with open(self.PARAMFILE, "r") as parameterFile:
                    csvParams = csv.DictReader(parameterFile)
                    for param in csvParams:
                        self.logParams[pid_counter] = {}
                        self.logParams[pid_counter]["Name"] = param["Name"]
                        self.logParams[pid_counter]["Address"] = param["Address"]
                        self.logParams[pid_counter]["Length"] = int(param["Length"])
                        self.logParams[pid_counter]["Equation"] = param["Equation"]
                        self.logParams[pid_counter]["Signed"] = param["Signed"].lower() == "true"
                        self.logParams[pid_counter]["ProgMin"] = float(param["ProgMin"])
                        self.logParams[pid_counter]["ProgMax"] = float(param["ProgMax"])
                        self.logParams[pid_counter]["Value"] = 0.0
                        param_address = param["Address"].lstrip("0x").lower()
                        self.logParams[pid_counter]["Virtual"] = param_address == "ffff" or param_address == "ffffffff"

                        #check if we should be assigning this pid to an assignment
                        if str(param["Assign To"]) is not None:
                            assignTo = param["Assign To"][0:1].lower()
                            if assignTo != '' and assignTo != 'x' and assignTo != 'h' and assignTo != 't':
                                self.activityLogger.debug("Assignment: " + assignTo + " to: " + self.logParams[pid_counter]["Name"])
                                self.assignments[assignTo] = pid_counter
                                      
                        #add pid to csvheader
                        self.csvHeader += "," + param["Name"]
                        self.csvDivider += ",0"
                        self.activityLogger.debug("Logging parameter: " + param["Name"]+ "|" + str(param["Address"]) + "|" + str(param["Length"]) + "|" + str(self.logParams[pid_counter]["Signed"]))

                        pid_counter += 1
                                
            except Exception as e:
                self.activityLogger.info("Error loading parameter file: " + str(e))
                exit()
        else:
            self.activityLogger.info("Parameter file not found")
            exit()

        self.activityLogger.info("CSV Header for log files will be: " + self.csvHeader)

        # If we're only going to be writing to a single CSV file, create that file and put the header in it
        if self.singleCSV:
            self.filename = (
                self.filePath
                + self.logPrefix
                + self.currentTime
                + ".csv"
            )
            self.activityLogger.debug("Opening logfile at: " + self.filename)
            self.logFile = open(self.filename, "a")
            self.logFile.write(self.csvHeader + "\n")
            self.logFile.write(self.csvDivider + "\n")
            self.logFile.close()

        #start connection to ecu
        self.conn = connection_setup(self.interface, txid=0x7E0, rxid=0x7E8, interface_path=self.interfacePath)

    def startLogger(self):
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
        if self.callbackFunction:
            self.callbackFunction(logger_status="Killing logger process")
        self.kill = True

    def main(self, client=None, callback=None):
        if client is not None:
            #setup parameter lists
            if self.mode != "22":
                hslPrefix = "3E32"
                if self.mode == "HSL":
                    hslPrefix = "3E02"
                self.memoryOffset = 0xB001E700
                paramList = ""
                for parameter in self.logParams:
                    if self.logParams[parameter]["Virtual"] == False:
                        paramList += "0"
                        paramList += str(self.logParams[parameter]["Length"])[0:1]
                        paramList += self.logParams[parameter]["Address"].lstrip("0x")
                paramList += "00"

                fullRequest = (
                    hslPrefix
                    + str(hex(self.memoryOffset)).lstrip("0x")
                    + str(hex(int(len(paramList) / 2))).lstrip("0x").zfill(4)
                    + paramList
                )
                self.activityLogger.debug("Sending 3E request to set up logging: ")
                self.activityLogger.debug(fullRequest)
                results = self.sendRaw(bytes.fromhex(fullRequest))
                if str(results.hex())[0:2].lower() == "7e":
                    self.activityLogger.debug("Created 3E list: " + str(results.hex()))
                else:
                    self.activityLogger.critical("Failed to create 3E list: " + str(results.hex()))
                    exit()

        #start main polling thread
        try:
            self.activityLogger.debug("Starting the data polling thread")
            readData = threading.Thread(target=self.pollValues)
            readData.daemon = True
            readData.start()
        except (KeyboardInterrupt, SystemExit):
            sys.exit()
        except:
            self.activityLogger.critical("Error starting the data polling thread")

        #server mode: make datastream for GUI
        if self.runServer is True:
            try:
                self.activityLogger.debug("Starting data streaming thread")
                streamData = threading.Thread(target=self.streamData)
                streamData.daemon = True
                streamData.start()
            except (KeyboardInterrupt, SystemExit):
                sys.exit()
            except:
                self.activityLogger.critical("Error starting data streamer")

        #interactive mode: listen for enter key
        if self.interactive is True:
            try:
                self.activityLogger.debug("Starting the interactive thread")
                interactiveThread = threading.Thread(target=self.checkKeyboard)
                interactiveThread.daemon = True
                interactiveThread.start()
            except (KeyboardInterrupt, SystemExit):
                sys.exit()
            except:
                self.activityLogger.critical("Error starting the interactive thread")

        #main loop waiting for kill
        while self.kill == False:
            if self.displayGauges:
                self.drawGauges()

            if self.callbackFunction:
                self.callbackFunction(logger_status="Logger Running", dataStream=self.dataStream)

            time.sleep(0.2)

        del logging.Logger.manager.loggerDict["SimosHSL"]

    def checkKeyboard(self):
        self.activityLogger.info("Starting interactive thread [Enter: toggle logging, \'stop\': will stop logger]")
        
        while self.kill == False:
            log = input().lower()
            if log == "exit" or log == "stop":
                self.stop()
            else:
                self.activityLogger.debug("Input from user: " + log)
                self.isKeyTriggered = not self.isKeyTriggered

    def checkLogging(self):
        try:
            conditionsMet = False
            equationList = self.logTrigger.split("|")
            for currentEquation in equationList:
                if conditionsMet == False:
                    subConditionsMet = True
                    subEquationList = currentEquation.split("&")
                    for subEquation in subEquationList:
                        if subConditionsMet and len(subEquation) >= 3:
                            assignment = subEquation[0:1].lower()
                            if assignment > 'a' and assignment < 'z':
                                assignmentPID = self.assignments[assignment]
                                if assignmentPID is not None:
                                    value = self.logParams[assignmentPID]["Value"]
                                    function = subEquation[1:2]
                                    compareValue = float(subEquation[2:])
                                    if function == '>':
                                        if value <= compareValue:
                                            subConditionsMet = False
                                    elif function == '<':
                                        if value >= compareValue:
                                            subConditionsMet = False
                                    elif function == '=':
                                        if abs(value - compareValue) > 0.15:
                                            subConditionsMet = False
                                    else:
                                        subConditionsMet = True
                                
                    if subConditionsMet:
                        conditionsMet = True
                        
            self.isPIDTriggered = conditionsMet
        except:
            self.isPIDTriggered = False
                
        if self.isLogging:
            if self.isKeyTriggered == False and self.isPIDTriggered == False:
                self.isLogging = False
                self.logFile = None
                if self.displayGauges == False:
                    print("\033[F-Logging stopped-\033[0K")
        else:
            if self.isKeyTriggered or self.isPIDTriggered:
                self.isLogging = True
                if self.displayGauges == False:
                    print("\033[F-Logging started-\033[0K")

    def pollValues(self):
        self.activityLogger.info("Starting ECU poller")
        self.logFile = None

        # Start logging
        nextFrameTime = time.time()
        while self.kill == False:
            currentTime = time.time()
            if currentTime > nextFrameTime:
                nextFrameTime += self.delay
                if nextFrameTime < currentTime:
                    nextFrameTime = currentTime
                    
                if self.mode == "22":
                    self.getParams22()
                else:
                    self.getParamsHSL()

                self.setAssignmentValues()

                if self.logFile:
                    self.logFile.flush()

                self.checkLogging()

    def drawGauges(self):
        if self.dataRow is None:
            return
        
        header = self.csvHeader.split(",")
        values = self.dataRow.split(",")
        columnCount = int(shutil.get_terminal_size().columns / 15) - 1
        outString = "Status: "
        if self.isLogging:
            outString += "\033[1;31mLogging\033[1;37m"
        else:
            outString += "\033[1;32mPolling\033[1;37m"
        outString += "\033[0K\n"
        headerString = ""
        valuesString = ""
        seperationString = ""
        pos = 0
        row = 5
        for c in header:
            headerString += '{0:14s}'.format(header[pos])[0:14]+"|"
            valuesString += '{0:14s}'.format(values[pos])[0:14]+"|"
            seperationString += "---------------"
            pos += 1
            if pos % columnCount == 0:
                if pos == columnCount:
                    outString += seperationString+"\n"
                outString += headerString+"\033[0K\n"+valuesString+"\033[0K\n"+seperationString+"\033[0K\n"
                headerString = ""
                valuesString = ""
                seperationString = ""
                row += 3
                if row > shutil.get_terminal_size().lines - 3:
                    break
        if headerString != "":
            outString += headerString+"\033[0K\n"+valuesString+"\033[0K\n"+seperationString+"\033[0K\n"

        outString = "\033[H"+outString+"\033[0J"
        print(outString)

    def writeCSV(self, row):
        self.dataStream = self.dataStreamBuffer
        self.dataRow = row

        if self.isLogging:
            if self.logFile is None:
                if self.singleCSV:
                    self.filename = (
                        self.filePath
                        + self.logPrefix
                        + self.currentTime
                        + ".csv"
                    )
                else:
                    self.filename = (
                        self.filePath
                        + self.logPrefix
                        + datetime.now().strftime("%Y%m%d-%H%M%S")
                        + ".csv"
                    )
                self.activityLogger.debug("Opening logfile at: " + self.filename)
                self.logFile = open(self.filename, "a")
                if not self.singleCSV:
                    self.logFile.write(self.csvHeader + "\n")
            self.logFile.write(row + "\n")
            self.activityLogger.debug(row)

    def getParamsHSL(self):
        loggerPrefix = "3e33"
        loggerSufix = ""
        if self.mode == "HSL":
            loggerPrefix = "3e04"
            loggerSufix = "FFFF"

        requestString = loggerPrefix + str(hex(self.memoryOffset)).lstrip("0x") + loggerSufix
        self.activityLogger.debug("Sending request for: " + requestString)
        results = self.sendRaw(bytes.fromhex(requestString))

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

            self.dataStreamBuffer["Time"] = {"Name": "Time", "Value": str(datetime.now().time())}
            self.dataStreamBuffer["isLogging"] = {"Name": "isLogging", "Value": str(self.isLogging)}

            # Strip off the first 2 bytes so we only have the data
            results = results[2:]

            # The data comes back as raw data, so we need the size of each variable and its
            #  factor so that we can actually parse it.  In here, we'll pull X bytes off the
            #  front of the result, process it, add it to the CSV row, and then remove it from
            #  the result
            for parameter in self.logParams:
                if results == "":
                    break
                if self.logParams[parameter]["Virtual"]:
                    self.setPIDValue(parameter, 0.0)
                else:
                    val = results[: self.logParams[parameter]["Length"] * 2]
                    results = results[self.logParams[parameter]["Length"] * 2 :]
                    self.activityLogger.debug(str(parameter) + " raw from ecu: " + str(val))
                    rawval = int.from_bytes(
                        bytearray.fromhex(val),
                        "little",
                        signed=self.logParams[parameter]["Signed"],
                    )
                    if self.logParams[parameter]["Length"] == 4:
                        rawval = struct.unpack('f',int(rawval).to_bytes(4,'little'))[0]
                    self.activityLogger.debug(str(parameter) + " pre-function: " + str(rawval))
                    self.setPIDValue(parameter, rawval)
                    self.activityLogger.debug(str(parameter) + " scaling applied: " + str(val))
                    self.dataStreamBuffer[parameter] = {"Name": self.logParams[parameter]["Name"], "Value": str(self.logParams[parameter]["Value"])}
                row += "," + str(self.logParams[parameter]["Value"])
            self.writeCSV(row)

    def getParamAddress(self, address):
        for parameter in self.logParams:
            if address == self.logParams[parameter]["Address"].lstrip("0x"):
                return parameter

    def reqParams22(self, parameterString):
        self.activityLogger.debug("Sending: " + parameterString)
        results = ((self.sendRaw(bytes.fromhex(parameterString))).hex())
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
                        rawval = int.from_bytes(
                            bytearray.fromhex(val),
                            "big",
                            signed=self.logParams[pid]["Signed"]
                        )
                        self.activityLogger.debug(self.logParams[pid]["Name"] + " pre-function: " + str(rawval))
                        self.setPIDValue(pid, rawval)
                        self.activityLogger.debug(self.logParams[pid]["Name"] + " scaling applied: " + str(self.logParams[pid]["Value"]))
                        self.dataStreamBuffer[pid] = {"Name": self.logParams[pid]["Name"], "Value": str(self.logParams[pid]["Value"])}
                else:
                   results = ""

    def getParams22(self):
        self.activityLogger.debug("Getting values via 0x22")
        self.dataStreamBuffer = {}
        
        # Set the datetime for the beginning of the row
        row = str(datetime.now().time())

        self.dataStreamBuffer["Time"] = {"Name": "Time", "Value": str(datetime.now().time())}
        self.dataStreamBuffer["isLogging"] = {"Name": "isLogging", "Value": str(self.isLogging)}

        parameterPosition = 0
        parameterString = "22"
        for parameter in self.logParams:
            if self.logParams[parameter]["Virtual"]:
                self.setPIDValue(parameter, 0.0)
            else:
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
            row += "," + str(self.logParams[parameter]["Value"])

        self.writeCSV(row)

    def setAssignmentValues(self):
        for assign in self.assignments:
            self.assignmentValues[assign] = self.logParams[self.assignments[assign]]["Value"]

    def setPIDValue(self, parameter, raw):
        try:
            self.assignmentValues['x'] = raw
            self.logParams[parameter]["Value"] = round(eval(self.logParams[parameter]["Equation"], self.assignmentValues),2)
        except:
            self.logParams[parameter]["Value"] = 0.0

    # A function used to send raw data (so we can create the dynamic identifier etc), since udsoncan can't do it all
    def sendRaw(self, data):

        results = None

        while results is None:
            self.conn.send(data)
            results = self.conn.wait_frame(timeout=4)
            if results is None:
                self.activityLogger.critical("No response from ECU")

        return results

    # Stream data over a socket connection.
    # Open the socket, and if it happens to disconnect or fail, open it again
    # This is used for the android app
    def streamData(self, callback=None):
        self.activityLogger.info("Starting data server thread")
        HOST = "0.0.0.0"  # Standard loopback interface address (localhost)
        PORT = 65432  # Port to listen on (non-privileged ports are > 1023)

        while self.kill == False:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    s.bind((HOST, PORT))
                    s.listen()
                    conn, addr = s.accept()
                    self.activityLogger.info("Server listening on " + str(HOST) + ":" + str(PORT))
                    with conn:
                        print("Connected by", addr)
                        conn.sendall(b"HTTP/1.1 200 OK\n"
                            +b"Content-Type: stream\n"
                            +b"Access-Control-Allow-Origin: *\n"
                            +b"\n");
                        while self.kill == False:
                            json_data = json.dumps(self.dataStream) + "\n"
                            activityLogger.debug("Sending json to app: " + json_data)
                            conn.sendall(json_data.encode())
                            time.sleep(0.1)
            except:
                activityLogger.info("Socket closed due to error or client disconnect")
