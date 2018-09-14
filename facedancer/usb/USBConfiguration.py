# USBConfiguration.py
#
# Contains class definition for USBConfiguration.

import struct

from facedancer.usb.USB import USBDescribable,DescriptorType
from facedancer.usb.USBInterface import USBInterface
from facedancer.usb.USBEndpoint import USBEndpoint

# TODO: Section these out into their own folder?
from facedancer.usb.USBClass import USBClass
from .HIDClass import HIDClass
from facedancer.fuzz.helpers import mutable

class USBConfiguration(USBDescribable):

    name = 'Configuration'
    DESCRIPTOR_TYPE_NUMBER = DescriptorType.configuration
    DESCRIPTOR_SIZE_BYTES  = 9
    ATTR_BASE = 0x80
    ATTR_SELF_POWERED = ATTR_BASE | 0x40
    ATTR_REMOTE_WAKEUP = ATTR_BASE | 0x20
    
    def __init__(self, phy, configuration_index=0, configuration_string_or_index=0, interfaces=None, attributes=ATTR_SELF_POWERED, max_power=0x32, total_descriptor_lengths=9):
        super(USBConfiguration, self).__init__(phy)

        self._configuration_index        = configuration_index

        if isinstance(configuration_string_or_index, str):
            self.configuration_string       = configuration_string_or_index
            self._configuration_string_index = 0
        else:
            self._configuration_string_index = configuration_string_or_index
            self.configuration_string       = None

        self.interfaces = interfaces if interfaces else []

        self._attributes = attributes
        self._max_power = max_power
        self.total_descriptor_lengths = total_descriptor_lengths
        
        self._device = None
        self.usb_class = None
        self.usb_vendor = None

        for i in self.interfaces:
            i.set_configuration(self)
            # this is fool-proof against weird drivers
            if i.usb_class is not None:
                self.usb_class = i.usb_class
            if i.usb_vendor is not None:
                self.usb_vendor = i.usb_vendor

    @classmethod
    def from_binary_descriptor(cls, phy, data):
        """
        Generates a new USBConfiguration object from a configuration descriptor,
        handling any attached subordiate descriptors.

        data: The raw bytes for the descriptor to be parsed.
        """
        print("Configuration")
        length = data[0]

        # Unpack the main colleciton of data into the descriptor itself.
        descriptor_type, total_length, num_interfaces, index, string_index, \
            attributes, max_power = struct.unpack('<xBHBBBBB', data[0:length])

        # Extract the subordinate descriptors, and parse them.
        interfaces = cls._parse_subordinate_descriptors(phy, data[length:total_length])
        return cls(phy, index, string_index, interfaces, attributes, max_power, total_length)


    @classmethod
    def _parse_subordinate_descriptors(cls, phy, data):
        """
        Generates descriptor objects from the list of subordinate desciptors.

        data: The raw bytes for the descriptor to be parsed.
        """

        # TODO: handle recieving interfaces out of order?
        interfaces = []

        # Continue parsing until we run out of descriptors.
        while data:

            # Determine the length and type of the next descriptor.
            length          = data[0]
            descriptor = USBDescribable.from_binary_descriptor(phy, data[:length])

            # If we have an interface descriptor, add it to our list of interfaces.
            if isinstance(descriptor, USBInterface):
                interfaces.append(descriptor)
            elif isinstance(descriptor, USBEndpoint):
                interfaces[-1].add_endpoint(descriptor)
            elif isinstance(descriptor, USBClass):
                interfaces[-1].set_class(descriptor)

            # Move on to the next descriptor.
            data = data[length:]

        return interfaces


    def __repr__(self):
        """
        Generates a pretty form of the configuation for printing.
        """
        # TODO: make attributes readable

        max_power_mA = self._max_power * 2
        return "<USBConfiguration index={} num_interfaces={} attributes=0x{:02X} max_power={}mA>".format(
            self._configuration_index, len(self.interfaces), self._attributes, max_power_mA)


    def set_device(self, device):
        self._device = device

    def set_configuration_string_index(self, i):
        self._configuration_string_index = i

    def get_string(self):
        return self.configuration_string

    def get_string_by_id(self, str_id):
        s = super(USBConfiguration, self).get_string_by_id(str_id)
        if not s:
            for iface in self.interfaces:
                s = iface.get_string_by_id(str_id)
                if s:
                    break
        return s

    @mutable('configuration_descriptor')
    def get_descriptor(self, usb_type='fullspeed', valid=False):
        interface_descriptors = bytearray()
        for i in self.interfaces:
            interface_descriptors += i.get_descriptor(usb_type, valid)

        bLength = 9  # always 9
        bDescriptorType = DescriptorType.configuration
        wTotalLength = len(interface_descriptors) + 9
        bNumInterfaces = len(self.interfaces)
        d = struct.pack(
            '<BBHBBBBB',
            bLength,
            bDescriptorType,
            wTotalLength & 0xffff,
            bNumInterfaces,
            self._configuration_index,
            self._configuration_string_index,
            self._attributes,
            self._max_power
        )

        return d + interface_descriptors

    @mutable('other_speed_configuration_descriptor')
    def get_other_speed_descriptor(self, usb_type='lowspeed', valid=False):
        interface_descriptors = b''
        for i in self.interfaces:
            interface_descriptors += i.get_descriptor(usb_type, valid)
        bLength = 9  # always 9
        bDescriptorType = DescriptorType.other_speed_configuration
        wTotalLength = len(interface_descriptors) + 9
        bNumInterfaces = len(self.interfaces)
        d = struct.pack(
            '<BBHBBBBB',
            bLength,
            bDescriptorType,
            wTotalLength & 0xffff,
            bNumInterfaces,
            self._configuration_index,
            self._configuration_string_index,
            self._attributes,
            self._max_power
        )
        return d + interface_descriptors
