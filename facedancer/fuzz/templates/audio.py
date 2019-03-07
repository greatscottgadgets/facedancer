'''
Audio device templates
'''
from facedancer.usb.USB import DescriptorType
from kitty.model import UInt8, LE16, RandomBytes, BitField, Static
from kitty.model import Template, Repeat, List, Container, ForEach, OneOf
from kitty.model import ElementCount, SizeInBytes
from kitty.model import ENC_INT_LE
from .hid import GenerateHidReport
from .generic import Descriptor, SizedPt, DynamicInt, SubDescriptor
from binascii import unhexlify

class _AC_DescriptorSubTypes:  # AC Interface Descriptor Subtype

    '''Descriptor sub types [audio10.pdf table A-5]'''

    AC_DESCRIPTOR_UNDEFINED = 0x00
    HEADER = 0x01
    INPUT_TERMINAL = 0x02
    OUTPUT_TERMINAL = 0x03
    MIXER_UNIT = 0x04
    SELECTOR_UNIT = 0x05
    FEATURE_UNIT = 0x06
    PROCESSING_UNIT = 0x07
    EXTENSION_UNIT = 0x08


class _AS_DescriptorSubTypes:  # AS Interface Descriptor Subtype

    '''Descriptor sub types [audio10.pdf table A-6]'''

    AS_DESCRIPTOR_UNDEFINED = 0x00
    AS_GENERAL = 0x01
    FORMAT_TYPE = 0x02
    FORMAT_SPECIFIC = 0x03


# TODO: audio_ep2_buffer_available

# TODO: remove?
audio_header_descriptor = Descriptor(
    name='audio_header_descriptor',
    descriptor_type=DescriptorType.cs_interface,
    fields=[
        UInt8(name='bDesciptorSubType', value=_AC_DescriptorSubTypes.HEADER),
        LE16(name='bcdADC', value=0x0100),
        LE16(name='wTotalLength', value=0x1e),
        UInt8(name='bInCollection', value=0x1),
        Repeat(UInt8(name='baInterfaceNrX', value=1), 0, 247)
    ])

# TODO: remove?
audio_input_terminal_descriptor = Descriptor(
    descriptor_type=DescriptorType.cs_interface,
    name='audio_input_terminal_descriptor',
    fields=[
        UInt8(name='bDesciptorSubType', value=_AC_DescriptorSubTypes.INPUT_TERMINAL),
        UInt8(name='bTerminalID', value=0x00),
        LE16(name='wTerminalType', value=0x0206),  # termt10.pdf table 2-2
        UInt8(name='bAssocTerminal', value=0x00),
        UInt8(name='bNrChannels', value=0x01),
        LE16(name='wChannelConfig', value=0x0101),
        UInt8(name='iChannelNames', value=0x00),
        UInt8(name='iTerminal', value=0x00)
    ])

# TODO: remove?
audio_output_terminal_descriptor = Descriptor(
    name='audio_output_terminal_descriptor',
    descriptor_type=DescriptorType.cs_interface,
    fields=[
        UInt8(name='bDesciptorSubType', value=_AC_DescriptorSubTypes.OUTPUT_TERMINAL),
        UInt8(name='bTerminalID', value=0x00),
        LE16(name='wTerminalType', value=0x0307),  # termt10.pdf table 2-3
        UInt8(name='bAssocTerminal', value=0x00),
        UInt8(name='bSourceID', value=0x01),
        UInt8(name='iTerminal', value=0x00)
    ])

# Table 4-7
# TODO: remove?
audio_feature_unit_descriptor = Descriptor(
    name='audio_feature_unit_descriptor',
    descriptor_type=DescriptorType.cs_interface,
    fields=[
        UInt8(name='bDesciptorSubType', value=_AC_DescriptorSubTypes.FEATURE_UNIT),
        UInt8(name='bUnitID', value=0x00),
        UInt8(name='bSourceID', value=0x00),
        SizedPt(name='bmaControls',
                fields=RandomBytes(name='bmaControlsX', value='\x00', min_length=0, step=17, max_length=249)),
        UInt8(name='iFeature', value=0x00)
    ])


# Table 4-19
# TODO: remove?
audio_as_interface_descriptor = Descriptor(
    name='audio_as_interface_descriptor',
    descriptor_type=DescriptorType.cs_interface,
    fields=[
        UInt8(name='bDesciptorSubType', value=_AS_DescriptorSubTypes.AS_GENERAL),
        UInt8(name='bTerminalLink', value=0x00),
        UInt8(name='bDelay', value=0x00),
        LE16(name='wFormatTag', value=0x0001)
    ])


# TODO: remove?
audio_as_format_type_descriptor = Descriptor(
    name='audio_as_format_type_descriptor',
    descriptor_type=DescriptorType.cs_interface,
    fields=[
        UInt8(name='bDesciptorSubType', value=_AS_DescriptorSubTypes.FORMAT_TYPE),
        UInt8(name='bFormatType', value=0x01),
        UInt8(name='bNrChannels', value=0x01),
        UInt8(name='bSubFrameSize', value=0x02),
        UInt8(name='bBitResolution', value=0x10),
        UInt8(name='bSamFreqType', value=0x01),
        BitField(name='tSamFreq', length=24, value=0x01F40)
    ])


audio_hid_descriptor = Descriptor(
    name='audio_hid_descriptor',
    descriptor_type=DescriptorType.hid,
    fields=[
        DynamicInt('bcdHID', LE16(value=0x1001)),
        DynamicInt('bCountryCode', UInt8(value=0x00)),
        DynamicInt('bNumDescriptors', UInt8(value=0x01)),
        DynamicInt('bDescriptorType2', UInt8(value=DescriptorType.hid)),
        DynamicInt('wDescriptorLength', LE16(value=0x2b)),
    ]
)

# this descriptor is based on umap
# https://github.com/nccgroup/umap
# commit 3ad812135f8c34dcde0e055d1fefe30500196c0f
audio_report_descriptor = Template(
    name='audio_report_descriptor',
    fields=GenerateHidReport(
        unhexlify('050C0901A1011500250109E909EA75019502810209E209008106050B092095018142050C09009503810226FF000900750895038102090095049102C0')
    )
)


def size_in_words(x):
    return len(x) // 16


# This template is based on
# http://www.usb.org/developers/docs/devclass_docs/audio10.pdf
# Chapter 4.3
audio_control_interface_descriptor = Template(
    name='audio_control_interface_descriptor',
    fields=[
        SubDescriptor(
            name='Standard AC interface descriptor',
            descriptor_type=DescriptorType.interface,
            fields=[
                UInt8(name='bInterfaceNumber', value=0x00),
                UInt8(name='bAlternateSetting', value=0x00),
                ElementCount(name='bNumEndpoints', depends_on='endpoints', length=8),
                UInt8(name='bInterfaceClass', value=0x01, fuzzable=False),  # audio
                UInt8(name='bInterfaceSubClass', value=0x01, fuzzable=False),  # audio control
                UInt8(name='bInterfaceProtocol', value=0x00),
                UInt8(name='iInterface', value=0x01),
            ]
        ),
        List(
            name='Class-Specific AC interfaces',
            fields=[
                SubDescriptor(
                    name='header',
                    descriptor_type=DescriptorType.cs_interface,
                    fields=[
                        UInt8(name='bDesciptorSubType', value=0x01),
                        LE16(name='bcdADC', value=0x100),
                        SizeInBytes(name='wTotalLength', sized_field='Class-Specific AC interfaces', length=16, encoder=ENC_INT_LE),
                        SizeInBytes(name='bInCollection', sized_field='baInterfaceNr', length=8),
                        RandomBytes(name='baInterfaceNr', value='\x01', min_length=0, max_length=250),
                    ]
                ),
                SubDescriptor(
                    name='input terminal',
                    descriptor_type=DescriptorType.cs_interface,
                    fields=[
                        UInt8(name='bDesciptorSubType', value=0x02),
                        UInt8(name='bTerminalID', value=1),
                        LE16(name='wTerminalType', value=1),  # .. todo: review this field
                        UInt8(name='bAssocTerminal', value=2),
                        UInt8(name='bNrChannels', value=8),
                        LE16(name='wChannelConfig', value=0xff),
                        UInt8(name='iChannelNames', value=1),
                        UInt8(name='iTerminal', value=1),
                    ]
                ),
                SubDescriptor(
                    name='output terminal',
                    descriptor_type=DescriptorType.cs_interface,
                    fields=[
                        UInt8(name='bDesciptorSubType', value=0x03),
                        UInt8(name='bTerminalID', value=2),
                        LE16(name='wTerminalType', value=1),  # .. todo: review this field
                        UInt8(name='bAssocTerminal', value=1),
                        UInt8(name='bSourceID', value=8),
                        UInt8(name='iTerminal', value=1),
                    ]
                ),
                SubDescriptor(
                    name='mixer unit',
                    descriptor_type=DescriptorType.cs_interface,
                    fields=[
                        UInt8(name='bDesciptorSubType', value=0x04),
                        UInt8(name='bUnitID', value=3),
                        SizeInBytes(name='bNrInPins', sized_field='baSourceID', length=8),
                        RandomBytes(name='baSourceID', value='\x01', min_length=0, max_length=250),
                        UInt8(name='bNrChannels', value=8),
                        LE16(name='wChannelConfig', value=0xaaaa),
                        UInt8(name='iChannelNames', value=4),
                        UInt8(name='bmControls', value=0xff),  # this should be re-checked !! (section 4.3.2.3)
                        UInt8(name='iMixer', value=1),
                    ]
                ),
                SubDescriptor(
                    name='selector unit',
                    descriptor_type=DescriptorType.cs_interface,
                    fields=[
                        UInt8(name='bDesciptorSubType', value=0x05),
                        UInt8(name='bUnitID', value=4),
                        SizeInBytes(name='bNrInPins', sized_field='baSourceID', length=8),
                        RandomBytes(name='baSourceID', value='\x01', min_length=0, max_length=250),
                        UInt8(name='iSelector', value=1),
                    ]
                ),
                SubDescriptor(
                    name='feature unit',
                    descriptor_type=DescriptorType.cs_interface,
                    fields=[
                        UInt8(name='bDesciptorSubType', value=0x06),
                        UInt8(name='bUnitID', value=5),
                        UInt8(name='bSourceID', value=2),
                        SizeInBytes(name='bControlSize', sized_field='bmaControls', length=8),
                        RandomBytes(name='bmaControls', value='\x01', min_length=0, max_length=250),
                        UInt8(name='iFeature', value=1),
                    ]
                ),
                # .. todo: 4.3.2.6
                OneOf(
                    fields=[
                        Static(''),
                        SubDescriptor(
                            name='junk',
                            descriptor_type=DescriptorType.cs_interface,
                            fields=[
                                UInt8(name='bDesciptorSubType', value=0x15),
                                ForEach('bDesciptorSubType', fields=[
                                    RandomBytes(name='junk', value='\x01', min_length=0, max_length=250),
                                ])
                            ]
                        ),
                    ]
                )
            ]
        ),
        # .. todo: endpoint descriptor??
        Container(name='endpoints', fields=[])
    ]
)
