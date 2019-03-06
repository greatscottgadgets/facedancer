# USBSmartcard.py
#
# Contains class definitions to implement a USB Smartcard.
#
# The implementation is based on
# USB Smart Card Device Class Specification
# http://www.usb.org/developers/docs/devclass_docs/DWG_Smart-Card_CCID_Rev110.pdf

# This device doesn't work properly yet!!!!!

import struct
try:
    from six.moves.queue import Queue # Python 3
except ImportError:
    from six.moves.queue import queue as Queue # Python 2

from binascii import hexlify
from facedancer.usb.USB import DescriptorType
from facedancer.usb.USBClass import USBClass
from facedancer.usb.USBDevice import USBDevice
from facedancer.usb.USBConfiguration import USBConfiguration
from facedancer.usb.USBInterface import USBInterface
from facedancer.usb.USBEndpoint import USBEndpoint
from facedancer.fuzz.helpers import mutable

class ClassRequests(object):
    ABORT = 0x01
    GET_CLOCK_FREQUENCIES = 0x02
    GET_DATA_RATES = 0x03


class USBSmartcardClass(USBClass):
    name = 'SmartcardClass'

    def setup_local_handlers(self):
        self.local_handlers = {
            # ClassRequests.ABORT: ('scd_abort_response', self.handle_abort),
            ClassRequests.GET_CLOCK_FREQUENCIES: self.handle_get_clock_frequencies,
            ClassRequests.GET_DATA_RATES: self.handle_get_data_rates,
        }

    @mutable('get_clock_frequencies_response')
    def handle_get_clock_frequencies(self, req):
        response = b''
        for frequency in self.interface.clock_frequencies:
            response += struct.pack('<I', frequency)
        response = struct.pack('<I', len(response)) + response
        return response

    @mutable('get_data_rates_response')
    def handle_get_data_rates(self, req):
        response = b''
        for data_rate in self.interface.data_rates:
            response += struct.pack('<I', data_rate)
        response = struct.pack('<I', len(response)) + response
        return response


def R2P_Parameters(slot, seq, status, error, proto, data):
    length = len(data)
    response = struct.pack('<BIBBBBB', RdrToPc.Parameters, length, slot, seq, status, error, proto)
    response += data
    return response


def R2P_DataBlock(slot, seq, status, error, chain_param, data):
    length = len(data)
    response = struct.pack('<BIBBBBB', RdrToPc.DataBlock, length, slot, seq, status, error, chain_param)
    response += data
    return response


def R2P_SlotStatus(slot, seq, status, error, clock_status):
    response = struct.pack('<BIBBBBB', RdrToPc.SlotStatus, 0, slot, seq, status, error, clock_status)
    return response


def R2P_Escape(slot, seq, status, error, data):
    length = len(data)
    response = struct.pack('<BIBBBBB', RdrToPc.Escape, length, slot, seq, status, error, 0)
    response += data
    return response


def R2P_DataRateAndClockFrequency(slot, seq, status, error, freq, rate):
    data = struct.pack('<II', freq, rate)
    length = len(data)
    response = struct.pack('<BIBBBBB', RdrToPc.DataRateAndClock_Frequency, length, slot, seq, status, error, 0)
    response += data
    return response


class PcToRdrOpcode(object):
    IccPowerOn = 0x62
    IccPowerOff = 0x63
    GetSlotStatus = 0x65
    XfrBlock = 0x6F
    GetParameters = 0x6C
    ResetParameters = 0x6D
    SetParameters = 0x61
    Escape = 0x6B
    IccClock = 0x6E
    T0APDU = 0x6A
    Secure = 0x69
    Mechanical = 0x71
    Abort = 0x72
    SetDataRateAndClock_Frequency = 0x73


class RdrToPc(object):
    DataBlock = 0x80
    SlotStatus = 0x81
    Parameters = 0x82
    Escape = 0x83
    DataRateAndClock_Frequency = 0x84


class USBSmartcardInterface(USBInterface):
    name = 'SmartcardInterface'

    def __init__(self, phy):
        descriptors = {
            DescriptorType.hid: self.get_icc_descriptor
        }
        self.clock_frequencies = [
            0x00003267, 0x000064ce, 0x0000c99d, 0x0001933a, 0x00032674, 0x00064ce7,
            0x000c99ce, 0x00025cd7, 0x0003f011, 0x00004334, 0x00008669, 0x00010cd1,
            0x000219a2, 0x00043345, 0x0008668a, 0x0002a00b, 0x00003073, 0x000060e6,
            0x0000c1cc, 0x00018399, 0x00030732, 0x00060e63, 0x000122b3, 0x0001e47f,
            0x00015006, 0x00009736, 0x0000fc04, 0x00002853, 0x000050a5, 0x0000a14a,
            0x00014295, 0x00028529, 0x000078f8, 0x0000493e, 0x0000927c, 0x000124f8,
            0x000249f0, 0x000493e0, 0x000927c0, 0x0001b774, 0x0002dc6c, 0x000030d4,
            0x000061a8, 0x0000c350, 0x000186a0, 0x00030d40, 0x00061a80, 0x0001e848,
            0x0000dbba, 0x00016e36, 0x0000f424, 0x00006ddd, 0x0000b71b
        ]

        self.data_rates = []

        self.clock_freq = self.clock_frequencies[0]
        self.data_rate = 0 if not self.data_rates else self.data_rates[0]

        endpoints = [
            # CCID command pipe
            USBEndpoint(
                phy=phy,
                number=1,
                direction=USBEndpoint.direction_out,
                transfer_type=USBEndpoint.transfer_type_bulk,
                sync_type=USBEndpoint.sync_type_none,
                usage_type=USBEndpoint.usage_type_data,
                max_packet_size=0x40,
                interval=0,
                handler=self.handle_data_available
            ),
            # CCID response pipe
            USBEndpoint(
                phy=phy,
                number=2,
                direction=USBEndpoint.direction_in,
                transfer_type=USBEndpoint.transfer_type_bulk,
                sync_type=USBEndpoint.sync_type_none,
                usage_type=USBEndpoint.usage_type_data,
                max_packet_size=0x40,
                interval=0,
                handler=None
            ),
            # CCID event notification pipe
            USBEndpoint(
                phy=phy,
                number=3,
                direction=USBEndpoint.direction_in,
                transfer_type=USBEndpoint.transfer_type_interrupt,
                sync_type=USBEndpoint.sync_type_none,
                usage_type=USBEndpoint.usage_type_data,
                max_packet_size=8,
                interval=0,
                handler=self.handle_buffer_available
            ),
        ]

        # TODO: un-hardcode string index
        super(USBSmartcardInterface, self).__init__(
            phy=phy,
            interface_number=0,
            interface_alternate=0,
            interface_class=USBClass.SmartCard,
            interface_subclass=0,
            interface_protocol=0,
            interface_string_index=0,
            endpoints=endpoints,
            descriptors=descriptors,
            usb_class=USBSmartcardClass(phy)
        )

        self.proto = 0
        self.abProtocolDataStructure = b'\x11\x00\x00\x0a\x00'
        self.clock_status = 0x00
        self.int_q = Queue()
        self.int_q.put(b'\x50\x03')

        self.operations = {
            PcToRdrOpcode.IccPowerOn: self.handle_PcToRdr_IccPowerOn,
            PcToRdrOpcode.IccPowerOff: self.handle_PcToRdr_IccPowerOff,
            PcToRdrOpcode.GetSlotStatus: self.handle_PcToRdr_GetSlotStatus,
            PcToRdrOpcode.XfrBlock: self.handle_PcToRdr_XfrBlock,
            PcToRdrOpcode.GetParameters: self.handle_PcToRdr_GetParameters,
            PcToRdrOpcode.ResetParameters: self.handle_PcToRdr_ResetParameters,
            PcToRdrOpcode.SetParameters: self.handle_PcToRdr_SetParameters,
            PcToRdrOpcode.Escape: self.handle_PcToRdr_Escape,
            PcToRdrOpcode.IccClock: self.handle_PcToRdr_IccClock,
            PcToRdrOpcode.T0APDU: self.handle_PcToRdr_T0APDU,
            PcToRdrOpcode.Secure: self.handle_PcToRdr_Secure,
            PcToRdrOpcode.Mechanical: self.handle_PcToRdr_Mechanical,
            PcToRdrOpcode.Abort: self.handle_PcToRdr_Abort,
            PcToRdrOpcode.SetDataRateAndClock_Frequency: self.handle_PcToRdr_SetDataRateAndClock_Frequency,
        }

    @mutable('smartcard_IccPowerOn_response')
    def handle_PcToRdr_IccPowerOn(self, slot, seq, data):
        abData = b'\x3b\x6e\x00\x00\x80\x31\x80\x66\xb0\x84\x12\x01\x6e\x01\x83\x00\x90\x00'
        # Entropia Universe Gold card
        # Taken from http://ludovic.rousseau.free.fr/softwares/pcsc-tools/smartcard_list.txt
        abData = b'\x3B\x6B\x00\x00\x00\x31\xC0\x64\xA9\xEC\x01\x00\x82\x90\x00'
        return R2P_DataBlock(
            slot=slot,
            seq=seq,
            status=0x00,
            error=0x80,
            chain_param=0x00,
            data=abData
        )

    @mutable('smartcard_IccPowerOff_response')
    def handle_PcToRdr_IccPowerOff(self, slot, seq, data):
        '''
        Check out slot number (should be as bulk OUT message)
        '''
        return R2P_SlotStatus(
            slot=slot,
            seq=seq,
            status=0x00,
            error=0x80,
            clock_status=self.clock_status
        )

    @mutable('smartcard_GetSlotStatus_response')
    def handle_PcToRdr_GetSlotStatus(self, slot, seq, data):
        return R2P_SlotStatus(
            slot=slot,
            seq=seq,
            status=0x00,
            error=0x80,
            clock_status=self.clock_status
        )

    @mutable('smartcard_XfrBlock_response')
    def handle_PcToRdr_XfrBlock(self, slot, seq, data):
        '''
        .. todo:: check the response again later,
        '''
        abData = b'\x6a\x82'
        return R2P_DataBlock(
            slot=slot,
            seq=seq,
            status=0x00,
            error=0x80,
            chain_param=0x00,
            data=abData
        )

    @mutable('smartcard_GetParameters_response')
    def handle_PcToRdr_GetParameters(self, slot, seq, data):
        return R2P_Parameters(
            slot=slot,
            seq=seq,
            status=0x00,
            error=0x80,
            proto=self.proto,
            data=self.abProtocolDataStructure
        )

    @mutable('smartcard_ResetParameters_response')
    def handle_PcToRdr_ResetParameters(self, slot, seq, data):
        return R2P_Parameters(
            slot=slot,
            seq=seq,
            status=0x00,
            error=0x80,
            proto=self.proto,
            data=self.abProtocolDataStructure
        )

    @mutable('smartcard_SetParameters_response')
    def handle_PcToRdr_SetParameters(self, slot, seq, data):
        self.proto = struct.unpack('B', data[7:8])[0]
        if self.proto == 0:
            self.abProtocolDataStructure = data[10:15]
        elif self.proto == 1:
            self.abProtocolDataStructure = data[10:17]
        return R2P_Parameters(
            slot=slot,
            seq=seq,
            status=0x00,
            error=0x80,
            proto=self.proto,
            data=self.abProtocolDataStructure
        )

    @mutable('smartcard_Escape_response')
    def handle_PcToRdr_Escape(self, slot, seq, data):
        '''
        .. todo:: should check the data parameter
        '''
        return R2P_Escape(
            slot=slot,
            seq=seq,
            status=0x00,
            error=0x80,
            data=b''
        )

    @mutable('smartcard_IccClock_response')
    def handle_PcToRdr_IccClock(self, slot, seq, data):
        # bClockCommand = data[7]
        return R2P_SlotStatus(
            slot=slot,
            seq=seq,
            status=0x00,
            error=0x80,
            clock_status=self.clock_status
        )

    @mutable('smartcard_T0APDU_response')
    def handle_PcToRdr_T0APDU(self, slot, seq, data):
        # bmChange, bClassGetResponse, bClassEnvelope = struct.unpack('<BBB', data[7:10])
        return R2P_SlotStatus(
            slot=slot,
            seq=seq,
            status=0x00,
            error=0x80,
            clock_status=self.clock_status
        )

    @mutable('smartcard_Secure_response')
    def handle_PcToRdr_Secure(self, slot, seq, data):
        '''
        .. todo:: to complete that, go over section 6.1.11
                  ATM unpack will raise an exception
        '''
        bBWI, wLevelParameter = struct.unpack('<BH')
        return R2P_DataBlock(
            slot=slot,
            seq=seq,
            status=0x00,
            error=0x80,
            chain_param=0x00,
            data=b''
        )

    @mutable('smartcard_Mechanical_response')
    def handle_PcToRdr_Mechanical(self, slot, seq, data):
        '''
        .. todo:: handling
        '''
        return R2P_SlotStatus(
            slot=slot,
            seq=seq,
            status=0x00,
            error=0x80,
            clock_status=self.clock_status
        )

    @mutable('smartcard_Abort_response')
    def handle_PcToRdr_Abort(self, slot, seq, data):
        '''
        .. todo:: handling
        '''
        return R2P_SlotStatus(
            slot=slot,
            seq=seq,
            status=0x00,
            error=0x80,
            clock_status=self.clock_status
        )

    @mutable('smartcard_SetDataRateAndClock_Frequency_response')
    def handle_PcToRdr_SetDataRateAndClock_Frequency(self, slot, seq, data):
        self.clock_freq, self.data_rate = struct.unpack('<II', data[10:18])
        return R2P_DataRateAndClockFrequency(
            slot=slot,
            seq=seq,
            status=0x00,
            error=0x80,
            freq=self.clock_freq,
            rate=self.data_rate
        )

    @mutable('smartcard_scd_icc_descriptor')
    def get_icc_descriptor(self, *args):
        bDescriptorType = 0x21
        bcdCCID = 0x0110
        bMaxSlotIndex = 0x00
        bVoltageSupport = 0x07
        dwProtocols = 0x00000003
        dwDefaultClock = 0x00000ea6
        dwMaximumClock = 0x00001d4c
        bNumClockSupported = len(self.clock_frequencies)
        dwDataRate = 0x00002760
        dwMaxDataRate = 0x0004c4b4
        bNumDataRatesSupported = len(self.data_rates)
        dwMaxIFSD = 0x000000fe
        dwSynchProtocols = 0x00000000
        dwMechanical = 0x00000000
        dwFeatures = 0x00010030
        dwMaxCCIDMessageLength = 0x0000010f
        bClassGetResponse = 0x00
        bClassEnvelope = 0x00
        wLcdLayout = 0x0000
        bPinSupport = 0x00
        bMaxCCIDBusySlots = 0x01

        response = struct.pack(
            '<BHBBIIIBIIBIIIIIBBHBB',
            bDescriptorType,
            bcdCCID,
            bMaxSlotIndex,
            bVoltageSupport,
            dwProtocols,
            dwDefaultClock,
            dwMaximumClock,
            bNumClockSupported,
            dwDataRate,
            dwMaxDataRate,
            bNumDataRatesSupported,
            dwMaxIFSD,
            dwSynchProtocols,
            dwMechanical,
            dwFeatures,
            dwMaxCCIDMessageLength,
            bClassGetResponse,
            bClassEnvelope,
            wLcdLayout,
            bPinSupport,
            bMaxCCIDBusySlots
        )

        response = struct.pack('B', len(response) + 1) + response
        return response

    def handle_data_available(self, data):
        self.usb_function_supported()
        opcode, length, slot, seq = struct.unpack('<BIBB', data[:7])
        if opcode in self.operations:
            handler = self.operations[opcode]
            self.session_data['bSlot'] = data[5]
            self.session_data['bSeq'] = data[6]
            self.session_data['data'] = data
            response = handler(slot, seq, data)
        else:
            self.error('Received Smartcard command not understood')
            response = b''
        if response:
            self.send_on_endpoint(2, response)

    def handle_buffer_available(self):
        if not self.int_q.empty():
            buff = self.int_q.get()
            self.debug('Sending data to host: %s' % (hexlify(buff)))
            self.send_on_endpoint(3, buff)
        else:
            self.send_on_endpoint(3, b'')


class USBSmartcardDevice(USBDevice):
    name = 'Smartcard device'

    def __init__(self, phy, vid=0x0bda, pid=0x0165, rev=0x2361, **kwargs):
        super(USBSmartcardDevice, self).__init__(
            phy=phy,
            device_class=USBClass.Unspecified,
            device_subclass=0,
            protocol_rel_num=0,
            max_packet_size_ep0=64,
            vendor_id=vid,
            product_id=pid,
            device_rev=rev,
            manufacturer_string='Generic',
            product_string='Smart Card Reader Interface',
            serial_number_string='20070818000000000',
            configurations=[
                USBConfiguration(
                    phy=phy,
                    configuration_index=1,
                    configuration_string_or_index='Emulated Smartcard',
                    interfaces=[
                        USBSmartcardInterface(phy=phy)
                    ]
                )
            ]
        )


usb_device = USBSmartcardDevice
