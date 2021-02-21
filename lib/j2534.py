import ctypes
from ctypes import Structure, WINFUNCTYPE, POINTER, cast, c_long, c_void_p, c_ulong, byref

import pprint
from enum import Enum


class PASSTHRU_MSG(Structure):
    _fields_ = [("ProtocolID", c_ulong),
        ("RxStatus", c_ulong),
        ("TxFlags", c_ulong),
        ("Timestamp", c_ulong),
        ("DataSize", c_ulong),
        ("ExtraDataindex", c_ulong),
        ("Data", ctypes.c_ubyte * 4128)]

class J2534():
    dllPassThruOpen = None 
    dllPassThruClose = None
    dllPassThruConnect = None
    dllPassThruDisconnect  = None
    dllPassThruReadMsgs  = None
    dllPassThruWriteMsgs = None
    dllPassThruStartPeriodicMsg = None
    dllPassThruStopPeriodicMsg = None
    dllPassThruReadVersion = None
    dllPassThruStartMsgFilter = None


    def __init__(self, dllName = "op20pt32.dll", location = "C:/Program Files (x86)/OpenECU/OpenPort 2.0/drivers/openport 2.0/"):

        global dllPassThruOpen 
        global dllPassThruClose
        global dllPassThruConnect
        global dllPassThruDisconnect 
        global dllPassThruReadMsgs 
        global dllPassThruWriteMsgs
        global dllPassThruStartPeriodicMsg
        global dllPassThruStopPeriodicMsg
        global dllPassThruReadVersion
        global dllPassThruStartMsgFilter

        self.hDLL = ctypes.cdll.LoadLibrary(location + dllName)

        dllPassThruOpenProto = WINFUNCTYPE(
            c_long,
            c_void_p,
            POINTER(c_ulong))
        
        dllPassThruOpenParams = (1, "pName", 0),(1, "pDeviceID", 0)
        dllPassThruOpen = dllPassThruOpenProto(("PassThruOpen", self.hDLL), dllPassThruOpenParams)
        
        
        dllPassThruCloseProto = WINFUNCTYPE(
            c_long,
            c_ulong)
        
        dllPassThruCloseParams = (1, "DeviceID", 0),
        dllPassThruClose = dllPassThruCloseProto(("PassThruClose", self.hDLL), dllPassThruCloseParams) 
        
        dllPassThruConnectProto = WINFUNCTYPE(
            c_long,
            c_ulong,
            c_ulong,
            c_ulong,
            c_ulong,
            POINTER(c_ulong))
        
        dllPassThruConnectParams = (1, "DeviceID", 0), (1, "ProtocolID", 0), (1, "Flags", 0), (1, "BaudRate", 500000), (1, "pChannelID", 0)
        dllPassThruConnect = dllPassThruConnectProto(("PassThruConnect", self.hDLL), dllPassThruConnectParams)
        
        dllPassThruDisconnectProto = WINFUNCTYPE(
            c_long,
            c_ulong)
        
        dllPassThruDisconnectParams = (1, "ChannelID", 0),
        dllPassThruDisconnect = dllPassThruDisconnectProto(("PassThruDisconnect", self.hDLL), dllPassThruDisconnectParams) 
    
        dllPassThruReadMsgsProto = WINFUNCTYPE(
            c_long,
            c_ulong,
            POINTER(PASSTHRU_MSG),
            POINTER(c_ulong),
            c_ulong)
    
        dllPassThruReadMsgsParams = (1, "ChannelID", 0), (1, "pMsg", 0), (1, "pNumMsgs", 0), (1, "Timeout", 0)
        dllPassThruReadMsgs = dllPassThruReadMsgsProto(("PassThruReadMsgs", self.hDLL), dllPassThruReadMsgsParams)
    
        dllPassThruWriteMsgsProto = WINFUNCTYPE(
            c_long,
            c_ulong,
            POINTER(PASSTHRU_MSG),
            POINTER(c_ulong),
            c_ulong)
    
        dllPassThruWriteMsgsParams = (1, "ChannelID", 0), (1, "pMsg", 0), (1, "pNumMsgs", 0), (1, "Timeout", 0)
        dllPassThruWriteMsgs = dllPassThruWriteMsgsProto(("PassThruWriteMsgs", self.hDLL), dllPassThruWriteMsgsParams)
    
        dllPassThruStartPeriodicMsgProto = WINFUNCTYPE(
            c_long,
            c_ulong,
            POINTER(PASSTHRU_MSG),
            POINTER(c_ulong),
            c_ulong)
    
        dllPassThruStartPeriodicMsgParams = (1, "ChannelID", 0), (1, "pMsg", 0), (1, "pMsgID", 0), (1, "TimeInterval", 0)
        dllPassThruStartPeriodicMsg = dllPassThruStartPeriodicMsgProto(("PassThruStartPeriodicMsg", self.hDLL), dllPassThruStartPeriodicMsgParams)
    
        dllPassThruStopPeriodicMsgProto = WINFUNCTYPE(
            c_long,
            c_ulong,
            c_ulong)
    
        dllPassThruStopPeriodicMsgParams = (1, "ChannelID", 0), (1, "MsgID", 0)
        dllPassThruStopPeriodicMsg = dllPassThruStopPeriodicMsgProto(("PassThruStopPeriodicMsg", self.hDLL), dllPassThruStopPeriodicMsgParams)

        
        dllPassThruReadVersionProto = WINFUNCTYPE(
            c_long,
            c_ulong,
            POINTER(ctypes.c_char),
            POINTER(ctypes.c_char),
            POINTER(ctypes.c_char))

        dllPassThruReadVersionParams = (1, "DeviceID", 0), (1, "pFirmwareVersion", 0), (1, "pDllVersion", 0), (1, "pApiVersoin", 0)
        dllPassThruReadVersion = dllPassThruReadVersionProto(("PassThruReadVersion", self.hDLL), dllPassThruReadVersionParams)

        dllPassThruStartMsgFilterProto = WINFUNCTYPE(
            c_long,
            c_ulong,
            c_ulong,
            POINTER(PASSTHRU_MSG),
            POINTER(PASSTHRU_MSG),
            POINTER(PASSTHRU_MSG),
            POINTER(c_ulong)
        )

        dllPassThruStartMsgFilterParams = (1, "ChannelID", 0), (1, "FilterType", 0), (1, "pMaskMsg", 0), (1, "pPatternMsg", 0), (1, "pFlowControlMsg", 0), (1, "pMsgID", 0)

        dllPassThruStartMsgFilter = dllPassThruStartMsgFilterProto(("PassThruStartMsgFilter", self.hDLL), dllPassThruStartMsgFilterParams)
        

    def PassThruOpen(self, pDeviceID = None):
        if not pDeviceID:
            pDeviceID = ctypes.c_ulong()
    
        result = dllPassThruOpen(byref(ctypes.c_int()), byref(pDeviceID))
        return Error_ID(hex(result)), pDeviceID
    
    
    def PassThruConnect(self, deviceID, protocol, baudrate, pChannelID = None):
        if not pChannelID:
            pChannelID = c_ulong()
    
        result = dllPassThruConnect(deviceID, protocol, 0, baudrate, byref(pChannelID))
        return Error_ID(hex(result)), pChannelID
    
    
    def PassThruClose(self, DeviceID):
        result = dllPassThruClose(DeviceID)
        return Error_ID(hex(result))
    
    
    def PassThruDisconnect(self, ChannelID):
        result = dllPassThruDisconnect(ChannelID)
        return Error_ID(hex(result))
    
    
    def PassThruReadMsgs(self, ChannelID, pNumMsgs = 1, Timeout = 0):
        pMsg = PASSTHRU_MSG()
        
        pNumMsgs = c_ulong(pNumMsgs)
    
        result = dllPassThruReadMsgs(ChannelID, byref(pMsg), byref(pNumMsgs), c_ulong(Timeout))
        return Error_ID(hex(result)), pMsg.Data[0:pMsg.DataSize], pNumMsgs
    
    
    def PassThruWriteMsgs(self, ChannelID, Data, protocol, pNumMsgs = 1, Timeout = 100):
        txmsg = PASSTHRU_MSG()
        txmsg.TxFlags = TxStatusFlag.ISO15765_FRAME_PAD.value
        txmsg.ProtocolID = protocol;

        Data = b'\x00\x00\x07\x0E' + Data

        for i in range(0, len(Data)):
            txmsg.Data[i] = Data[i]
        
        txmsg.DataSize = len(Data)

        print(str(i) + ": " + str(txmsg.Data[0:len(Data)]), end=',')

        print()
        #print("data size to send: " + str(txmsg.DataSize))
    
        result = dllPassThruWriteMsgs(ChannelID, byref(txmsg), byref(c_ulong(pNumMsgs)), c_ulong(Timeout))
        return Error_ID(hex(result))
    
    
    def PassThruStartPeriodicMsg(self, ChannelID, Data, MsgID = 0, TimeInterval = 100):
        pMsg = PASSTHRU_MSG()
    
        pMsg.Data = Data
        pMsg.DataSize = len(Data)
    
        result = dllPassThruStartPeriodicMsgMsgs(ChannelID, byref(pMsg), byref(c_ulong(MsgID)), c_ulong(TimeInterval))
    
        return Error_ID(hex(result))
    
    def PassThruStopPeriodicMsg(self, ChannelID, MsgID):
        result = dllPassThruStopPeriodicMsgMsgs(ChannelID, MsgID)
    
        return Error_ID(hex(result))

    def PassThruReadVersion(self, DeviceID):
        pFirmwareVersion = (ctypes.c_char * 80)()
        pDllVersion = (ctypes.c_char * 80)()
        pApiVersion = (ctypes.c_char * 80)()
        result = dllPassThruReadVersion(DeviceID, pFirmwareVersion, pDllVersion, pApiVersion)
        
        return Error_ID(hex(result)), pFirmwareVersion, pDllVersion, pApiVersion

    def PassThruStartMsgFilter(self, ChannelID, protocol):
        txID = bytes([0x00, 0x00, 0x07, 0xE0])
        rxID = bytes([0x00, 0x00, 0x07, 0xE8])

        txmsg = PASSTHRU_MSG()

        txmsg.ProtocolID = protocol;
        txmsg.RxStatus = 0;
        txmsg.TxFlags = TxStatusFlag.ISO15765_FRAME_PAD.value
        txmsg.Timestamp = 0;
        txmsg.DataSize = 4;

        msgMask = msgPattern  = msgFlow = txmsg


        for i in range(0, len(txID)):
            msgPattern.Data[i] = txID[i]

        for i in range(0, len(rxID)):
            msgFlow.Data[i] = rxID[i]
        
        msgID = c_ulong(0)

        result = dllPassThruStartMsgFilter(ChannelID, c_ulong(Filter.FLOW_CONTROL_FILTER.value), byref(msgMask), byref(msgPattern), byref(msgFlow), byref(msgID))
        if Error_ID(hex(result)).value != hex(0x0):
            print("        Error setting filter")
            return Error_ID(hex(result))


        for i in range(0, len(rxID)):
            msgPattern.Data[i] = rxID[i]

        for i in range(0, len(txID)):
            msgFlow.Data[i] = txID[i]

        result = dllPassThruStartMsgFilter(ChannelID, c_ulong(Filter.FLOW_CONTROL_FILTER.value), byref(msgMask), byref(msgPattern), byref(msgFlow), byref(msgID))


        return Error_ID(hex(result))


#    dllPassThruStopMsgFilterProto = WINFUNCTYPE(
#        c_long,
#((unsigned long ChannelID, unsigned long MsgID);
#
#
#    dllPassThruSetProgrammingVoltageProto = WINFUNCTYPE(
#        c_long,
#((unsigned long DeviceID, unsigned long Pin, unsigned long Voltage);
#
#
#    dllPassThruGetLastErrorProto = WINFUNCTYPE(
#        c_long,
#((char *pErrorDescription);
#
#
#    dllPassThruIoctlProto = WINFUNCTYPE(
#        c_long,
#((unsigned long ChannelID, unsigned long IoctlID, const void *pInput, void *pOutput);



class Error_ID(Enum):

    ERR_SUCCESS=hex(0x00)
    STATUS_NOERROR=hex(0x00)
    ERR_NOT_SUPPORTED=hex(0x01)
    ERR_INVALID_CHANNEL_ID=hex(0x02)
    ERR_INVALID_PROTOCOL_ID=hex(0x03)
    ERR_NULL_PARAMETER=hex(0x04)
    ERR_INVALID_IOCTL_VALUE=hex(0x05)
    ERR_INVALID_FLAGS=hex(0x06)
    ERR_FAILED	=hex(0x07)
    ERR_DEVICE_NOT_CONNECTED=hex(0x08)
    ERR_TIMEOUT	=hex(0x09)
    ERR_INVALID_MSG=hex(0x0A)
    ERR_INVALID_TIME_INTERVAL=hex(0x0B)
    ERR_EXCEEDED_LIMIT=hex(0x0C)
    ERR_INVALID_MSG_ID=hex(0x0D)
    ERR_DEVICE_IN_USE=hex(0x0E)
    ERR_INVALID_IOCTL_ID=hex(0x0F)
    ERR_BUFFER_EMPTY=hex(0x10)
    ERR_BUFFER_FULL=hex(0x11)
    ERR_BUFFER_OVERFLOW=hex(0x12)
    ERR_PIN_INVALID=hex(0x13)
    ERR_CHANNEL_IN_USE=hex(0x14)
    ERR_MSG_PROTOCOL_ID=hex(0x15)
    ERR_INVALID_FILTER_ID=hex(0x16)
    ERR_NO_FLOW_CONTROL=hex(0x17)
    ERR_NOT_UNIQUE=hex(0x18)
    ERR_INVALID_BAUDRATE=hex(0x19)
    ERR_INVALID_DEVICE_ID=hex(0x1A)


class Protocol_ID(Enum):

    J1850VPW = 1
    J1850PWM = 2
    ISO9141 = 3
    ISO14230 = 4
    CAN = 5
    ISO15765 = 6
    SCI_A_ENGINE = 7	# OP2.0: Not supported
    SCI_A_TRANS = 8	# OP2.0: Not supported
    SCI_B_ENGINE = 9	# OP2.0: Not supported
    SCI_B_TRANS = 10	# OP2.0: Not supported

class Filter(Enum):
    PASS_FILTER = 0x00000001
    BLOCK_FILTER = 0x00000002
    FLOW_CONTROL_FILTER = 0x00000003

class TxStatusFlag(Enum):
    ISO15765_FRAME_PAD = 0x00000040
    WAIT_P3_MIN_ONLY = 0x00000200
    SW_CAN_HV_TX = 0x00000400 # OP2.0: Not supported
    SCI_MODE = 0x00400000 # OP2.0: Not supported
    SCI_TX_VOLTAGE = 0x00800000 # OP2.0: Not supported
