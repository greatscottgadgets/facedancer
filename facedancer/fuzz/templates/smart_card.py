'''
Smart card device templates
'''

from kitty.model import UInt8, LE32, RandomBytes
from kitty.model import SizeInBytes
from kitty.model import ENC_INT_LE
from kitty.model import Template, Container
from generic import DynamicInt


class R2PParameters(Template):

    def __init__(self, name, status, error, proto, ab_data, fuzzable=True):
        fields = [
            UInt8(name='bMessageType', value=0x82),
            SizeInBytes(name='dwLength', sized_field=ab_data, length=32, fuzzable=True, encoder=ENC_INT_LE),
            DynamicInt(name='bSlot', key='bSlot', bitfield=UInt8(name='bSlotInt', value=0)),
            DynamicInt(name='bSeq', key='bSeq', bitfield=UInt8(name='bSeqInt', value=0)),
            UInt8(name='bStatus', value=status),
            UInt8(name='bError', value=error),
            UInt8(name='bProtocolNum', value=proto),
            Container(name='abData', fields=ab_data),
        ]
        super(R2PParameters, self).__init__(name=name, fields=fields, fuzzable=fuzzable)


smartcard_GetParameters_response = R2PParameters(
    name='smartcard_GetParameters_response',
    status=0x00,
    error=0x80,
    proto=0,
    ab_data=RandomBytes(name='data', value='\x11\x00\x00\x0a\x00', min_length=0, max_length=150),
)


smartcard_ResetParameters_response = R2PParameters(
    name='smartcard_ResetParameters_response',
    status=0x00,
    error=0x80,
    proto=0,
    ab_data=RandomBytes(name='data', value='\x11\x00\x00\x0a\x00', min_length=0, max_length=150),
)

smartcard_SetParameters_response = R2PParameters(
    name='smartcard_SetParameters_response',
    status=0x00,
    error=0x80,
    proto=0,
    ab_data=RandomBytes(name='data', value='\x11\x00\x00\x0a\x00', min_length=0, max_length=150),
)


class R2PDataBlock(Template):

    def __init__(self, name, status, error, chain_param, ab_data, fuzzable=True):
        fields = [
            UInt8(name='bMessageType', value=0x80),
            SizeInBytes(name='dwLength', sized_field=ab_data, length=32, fuzzable=True, encoder=ENC_INT_LE),
            DynamicInt(name='bSlot', key='bSlot', bitfield=UInt8(name='bSlotInt', value=0)),
            DynamicInt(name='bSeq', key='bSeq', bitfield=UInt8(name='bSeqInt', value=0)),
            UInt8(name='bStatus', value=status),
            UInt8(name='bError', value=error),
            UInt8(name='bChainParameter', value=chain_param),
            Container(name='abData', fields=ab_data),
        ]
        super(R2PDataBlock, self).__init__(name=name, fields=fields, fuzzable=fuzzable)

smartcard_IccPowerOn_response = R2PDataBlock(
    name='smartcard_IccPowerOn_response',
    status=0x00,
    error=0x80,
    chain_param=0x00,
    ab_data=RandomBytes(name='data', value='\x3b\x6e\x00\x00\x80\x31\x80\x66\xb0\x84\x12\x01\x6e\x01\x83\x00\x90\x00', min_length=0, max_length=150),
)

smartcard_XfrBlock_response = R2PDataBlock(
    name='smartcard_XfrBlock_response',
    status=0x00,
    error=0x80,
    chain_param=0x00,
    ab_data=RandomBytes(name='data', value='\x6a\x82', min_length=0, max_length=150),
)


class R2PSlotStatus(Template):
    def __init__(self, name, status, error, clock_status, fuzzable=True):
        fields = [
            UInt8(name='bMessageType', value=0x80),
            LE32(name='dwLength', value=0x00),
            DynamicInt(name='bSlot', key='bSlot', bitfield=UInt8(name='bSlotInt', value=0)),
            DynamicInt(name='bSeq', key='bSeq', bitfield=UInt8(name='bSeqInt', value=0)),
            UInt8(name='bStatus', value=status),
            UInt8(name='bError', value=error),
            UInt8(name='bClockStatus', value=clock_status),
        ]
        super(R2PSlotStatus, self).__init__(name=name, fields=fields, fuzzable=fuzzable)


smartcard_IccPowerOff_response = R2PSlotStatus('smartcard_IccPowerOff_response', 0x00, 0x80, 0)
smartcard_GetSlotStatus_response = R2PSlotStatus('smartcard_GetSlotStatus_response', 0x00, 0x80, 0)
smartcard_IccClock_response = R2PSlotStatus('smartcard_IccClock_response', 0x00, 0x80, 0)
smartcard_T0APDU_response = R2PSlotStatus('smartcard_T0APDU_response', 0x00, 0x80, 0)


class R2PEscape(Template):

    def __init__(self, name, status, error, ab_data, fuzzable=True):
        fields = [
            UInt8(name='bMessageType', value=0x83),
            SizeInBytes(name='dwLength', sized_field='abData', length=32, fuzzable=True, encoder=ENC_INT_LE),
            DynamicInt(name='bSlot', key='bSlot', bitfield=UInt8(name='bSlotInt', value=0)),
            DynamicInt(name='bSeq', key='bSeq', bitfield=UInt8(name='bSeqInt', value=0)),
            UInt8(name='bStatus', value=status),
            UInt8(name='bError', value=error),
            UInt8(name='bRFU', value=0),
            Container(name='abData', fields=ab_data),
        ]
        super(R2PEscape, self).__init__(name=name, fields=fields, fuzzable=fuzzable)

smartcard_Escape_response = R2PEscape('smartcard_Escape_response', 0x00, 0x00, RandomBytes(name='data', value='', min_length=0, max_length=150))
