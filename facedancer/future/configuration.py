#
# This file is part of FaceDancer.
#
""" Functionality for describing USB device configurations. """


import typing
import struct
import logging

from dataclasses  import dataclass

from .interface   import USBInterface
from .descriptor  import USBDescribable

from .magic       import instantiate_subordinates, AutoInstantiable
from .request     import USBRequestHandler

# TODO: Section these out into their own folder?
from ..USBClass import USBClass
from ..HIDClass import HIDClass


# Create a default logger for the module.
logger = logging.getLogger(__name__)

@dataclass
class USBConfiguration(USBDescribable, AutoInstantiable, USBRequestHandler):
    """ Class representing a USBDevice's configuration. """

    DESCRIPTOR_TYPE_NUMBER     = 0x02
    DESCRIPTOR_SIZE_BYTES      = 9

    parent               : typing.Any = None

    configuration_index  : int = 1
    configuration_string : str = None

    attributes           : int = 0xe0
    max_power            : int = 250


    def __post_init__(self):
        self.device = self.parent

        # FIXME: handle this
        self.configuration_string_index =  0

        # FIXME: use our dictionary
        self._interfaces = instantiate_subordinates(self, USBInterface)
        self.interfaces = list(self._interfaces.values())

        print(self._interfaces)

        for i in self.interfaces:
            i.set_configuration(self)


    @classmethod
    def from_binary_descriptor(cls, data):
        """
        Generates a new USBConfiguration object from a configuration descriptor,
        handling any attached subordiate descriptors.

        data: The raw bytes for the descriptor to be parsed.
        """

        length = data[0]

        # Unpack the main colleciton of data into the descriptor itself.
        descriptor_type, total_length, num_interfaces, index, string_index, \
            attributes, max_power = struct.unpack_from('<xBHBBBBB', data[0:length])

        # Extract the subordinate descriptors, and parse them.
        interfaces = cls._parse_subordinate_descriptors(data[length:total_length])
        return cls(index, string_index, interfaces, attributes, max_power, total_length)


    @classmethod
    def _parse_subordinate_descriptors(cls, data):
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
            descriptor = USBDescribable.from_binary_descriptor(data[:length])

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

        max_power_mA = self.max_power * 2
        return "<USBConfiguration index={} num_interfaces={} attributes=0x{:02X} max_power={}mA>".format(
            self.configuration_index, len(set(interface.number for interface in self.interfaces)), self.attributes, max_power_mA)


    def set_device(self, device):
        self.device = device

    def set_configuration_string_index(self, i):
        self.configuration_string_index = i

    def get_descriptor(self):
        interface_descriptors = bytearray()
        for i in self.interfaces:
            interface_descriptors += i.get_descriptor()

        total_len = len(interface_descriptors) + 9

        d = bytes([
                9,          # length of descriptor in bytes
                2,          # descriptor type 2 == configuration
                total_len & 0xff,
                (total_len >> 8) & 0xff,
                len(set(interface.number for interface in self.interfaces)),
                self.configuration_index,
                self.configuration_string_index,
                self.attributes,
                self.max_power
        ])

        return d + interface_descriptors


    def get_identifier(self):
        return self.configuration_index


    #
    # Request handler functions.
    #

    def _request_handlers(self):
        return ()


    def _get_subordinate_handlers(self):
        return self._interfaces.values()
