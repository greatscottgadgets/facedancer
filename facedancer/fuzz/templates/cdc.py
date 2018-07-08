'''
CDC Device tempaltes
'''
from facedancer.dev.cdc import FunctionalDescriptor, CommunicationClassSubclassCodes
from facedancer.usb.USBClass import USBClass
from facedancer.usb.USB import DescriptorType
from kitty.model import UInt8, LE16, RandomBytes, BitField, Static
from kitty.model import Template, Repeat, List, Container, ForEach, OneOf
from kitty.model import ElementCount
from kitty.model import MutableField
from generic import SubDescriptor


cdc_control_interface_descriptor = Template(
    name='cdc_control_interface_descriptor',
    fields=[
        SubDescriptor(
            name='Standard interface descriptor',
            descriptor_type=DescriptorType.interface,
            fields=[
                UInt8(name='bInterfaceNumber', value=0x00),
                UInt8(name='bAlternateSetting', value=0x00),
                ElementCount(name='bNumEndpoints', depends_on='endpoints', length=8),
                UInt8(name='bInterfaceClass', value=USBClass.CDC, fuzzable=False),
                UInt8(name='bInterfaceSubClass', value=CommunicationClassSubclassCodes.Reserved, fuzzable=False),
                UInt8(name='bInterfaceProtocol', value=0x00),
                UInt8(name='iInterface', value=0x01),
            ]
        ),
        List(
            name='Class-Specific interfaces',
            fields=[
                SubDescriptor(
                    name='cdc_header_functional_descriptor',
                    descriptor_type=DescriptorType.cs_interface,
                    fields=[
                        UInt8(name='bDesciptorSubType', value=FunctionalDescriptor.Header),
                        LE16(name='bcdCDC', value=0x0101)
                    ]),
                SubDescriptor(
                    name='cdc_call_management_functional_descriptor',
                    descriptor_type=DescriptorType.cs_interface,
                    fields=[
                        UInt8(name='bDesciptorSubType', value=FunctionalDescriptor.CM),
                        BitField(name='bmCapabilities', value=0, length=8),
                        UInt8(name='bDataInterface', value=2)
                    ]),
                SubDescriptor(
                    name='cdc_abstract_control_management_functional_descriptor',
                    descriptor_type=DescriptorType.cs_interface,
                    fields=[
                        UInt8(name='bDesciptorSubType', value=FunctionalDescriptor.ACM),
                        BitField(name='bmCapabilities', value=0, length=8)
                    ]),
                SubDescriptor(
                    name='cdc_union_functional_descriptor',
                    descriptor_type=DescriptorType.cs_interface,
                    fields=[
                        UInt8(name='bDesciptorSubType', value=FunctionalDescriptor.UN),
                        UInt8(name='bMasterInterface', value=0),
                        Repeat(UInt8(name='bSlaveInterfaceX', value=1), 0, 251)
                    ]),
                SubDescriptor(
                    name='cdc_ethernet_networking_functional_descriptor',
                    descriptor_type=DescriptorType.cs_interface,
                    fields=[
                        UInt8(name='bDesciptorSubType', value=FunctionalDescriptor.EN),
                        UInt8(name='iMACAddress', value=0),
                        BitField(name='bmEthernetStatistics', value=0xffffffff, length=32),
                        LE16(name='wMaxSegmentSize', value=1514),
                        LE16(name='wNumberMCFilters', value=0),
                        UInt8(name='bNumberPowerFilters', value=0)
                    ]),
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
        Container(name='endpoints', fields=[
            SubDescriptor(
                name='endpoint_descriptor',
                descriptor_type=DescriptorType.endpoint,
                fields=[
                    UInt8(name='bEndpointAddress', value=0x83),
                    BitField(name='bmAttributes', value=3, length=8),
                    LE16(name='wMaxPacketSize', value=0x40),
                    UInt8(name='bInterval', value=0x20)
                ])
        ])
    ]
)

cdc_notification = Template(
    name='cdc_notification',
    fields=[
        OneOf(
            fields=[
                MutableField(name='mutable notification', value=b'\xa1\x00\x01\x00\x01\x00\x01\x00\x00'),
            ]),
    ])

