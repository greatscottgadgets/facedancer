#
# This file is part of FaceDancer.
#
""" Functionality for describing USB device configurations. """

import struct

from dataclasses  import dataclass, field
from typing       import Iterable

from .types       import USBDirection
from .magic       import instantiate_subordinates, AutoInstantiable
from .request     import USBRequestHandler

from .interface   import USBInterface
from .descriptor  import USBDescribable, USBClassDescriptor
from .endpoint    import USBEndpoint



@dataclass
class USBConfiguration(USBDescribable, AutoInstantiable, USBRequestHandler):
    """ Class representing a USBDevice's configuration.

    Fields:
        number                 -- The configuration's number; one-indexed.
        configuration_string   -- A string describing the configuration; or None if not provided.
        max_power              -- The maximum power expected to be drawn by the device when using
                                  this interface, in mA. Typically 500mA, for maximum possible.
        supports_remote_wakeup -- True iff this device should be able to wake the host from suspend.
    """

    DESCRIPTOR_TYPE_NUMBER  = 0x02
    DESCRIPTOR_SIZE_BYTES   = 9

    number                 : int            = 1
    configuration_string   : str            = None

    max_power              : int            = 500

    self_powered           : bool         = True
    supports_remote_wakeup : bool         = True

    parent                 : USBDescribable = None
    interfaces             : USBInterface = field(default_factory=dict)


    @classmethod
    def from_binary_descriptor(cls, data):
        """
        Generates a new USBConfiguration object from a configuration descriptor,
        handling any attached subordinate descriptors.

        data: The raw bytes for the descriptor to be parsed.
        """

        length = data[0]

        # Unpack the main collection of data into the descriptor itself.
        descriptor_type, total_length, num_interfaces, index, string_index, \
            attributes, max_power = struct.unpack_from('<xBHBBBBB', data[0:length])

        # Extract the subordinate descriptors, and parse them.
        interfaces = cls._parse_subordinate_descriptors(data[length:total_length])

        # TODO _parse_subordinate_descriptors should handle this
        interfaces = {interface.number:interface for interface in interfaces}

        return cls(
            number=index,
            configuration_string=string_index,
            max_power=max_power,
            self_powered=(attributes >> 6) & 1,
            supports_remote_wakeup=(attributes >> 5) & 1,
            interfaces=interfaces,
        )


    @classmethod
    def _parse_subordinate_descriptors(cls, data):
        """
        Generates descriptor objects from the list of subordinate descriptors.

        data: The raw bytes for the descriptor to be parsed.
        """

        # TODO: handle recieving interfaces out of order?
        interfaces = []

        # Continue parsing until we run out of descriptors.
        while data:

            # Determine the length and type of the next descriptor.
            length     = data[0]
            descriptor = USBDescribable.from_binary_descriptor(data[:length])

            # If we have an interface descriptor, add it to our list of interfaces.
            if isinstance(descriptor, USBInterface):
                interfaces.append(descriptor)
            elif isinstance(descriptor, USBEndpoint):
                interfaces[-1].add_endpoint(descriptor)
            elif isinstance(descriptor, USBClassDescriptor):
                interfaces[-1].set_class(descriptor)

            # Move on to the next descriptor.
            data = data[length:]

        return interfaces


    def __post_init__(self):

        # Gather any interfaces defined on the object.
        self.interfaces.update(instantiate_subordinates(self, USBInterface))


    @property
    def attributes(self):
        """ Retrives the "attributes" composite word. """

        # Start off with the required bits set to one...
        attributes = 0b10000000

        # ... and then add in our attributes.
        attributes |= (1 << 6) if self.self_powered           else 0
        attributes |= (1 << 5) if self.supports_remote_wakeup else 0


        return attributes

    #
    # User API.
    #

    def get_device(self):
        """ Returns a reference to the associated device."""
        return self.parent


    def add_interface(self, interface: USBInterface):
        """ Adds an interface to the configuration. """
        self.interfaces[interface.number] = interface
        interface.parent = self


    def get_endpoint(self, number: int, direction: USBDirection) -> USBEndpoint:
        """ Attempts to find an endpoint with the given number + direction.

        Paramters:
            number    -- The endpoint number to look for.
            direction -- Whether to look for an IN or OUT endpoint.
        """

        # Search each of our interfaces for the relevant endpoint.
        for interface in self.interfaces.values():
            endpoint = interface.get_endpoint(number, direction)
            if endpoint is not None:
                return endpoint

        # If none have one, return None.
        return None


    #
    # Event handlers.
    #


    def handle_data_received(self, endpoint: USBEndpoint, data: bytes):
        """ Handler for receipt of non-control request data.

        Typically, this method will delegate any data received to the
        appropriate configuration/interface/endpoint. If overridden, the
        overriding function will receive all data; and can delegate it by
        calling the `.handle_data_received` method on `self.configuration`.

        Parameters:
            endpoint -- The endpoint on which the data was received.
            data     -- The raw bytes received on the relevant endpoint.
        """

        for interface in self.interfaces.values():
            if interface.has_endpoint(endpoint.number, direction=USBDirection.OUT):
                interface.handle_data_received(endpoint, data)
                return

        # If no interface owned the targeted endpoint, consider the data unexpected.
        self.get_device().handle_unexpected_data_received(endpoint.number, data)


    def handle_data_requested(self, endpoint: USBEndpoint):
        """ Handler called when the host requests data on a non-control endpoint.

        Typically, this method will delegate the request to the appropriate
        interface+endpoint. If overridden, the overriding function will receive
        all data.

        Parameters:
            endpoint_number -- The endpoint number on which the host requested data.
        """

        for interface in self.interfaces.values():
            if interface.has_endpoint(endpoint.number, direction=USBDirection.IN):
                interface.handle_data_requested(endpoint)
                return

        # If no one interface owned the targeted endpoint, consider the data unexpected.
        self.get_device().handle_unexpected_data_requested(endpoint.number)


    def handle_buffer_empty(self, endpoint: USBEndpoint):
        """ Handler called when a given endpoint first has an empty buffer.

        Often, an empty buffer indicates an opportunity to queue data
        for sending ('prime an endpoint'), but doesn't necessarily mean
        that the host is planning on reading the data.

        This function is called only once per buffer.
        """

        for interface in self.interfaces.values():
            if interface.has_endpoint(endpoint.number, direction=USBDirection.IN):
                interface.handle_buffer_empty(endpoint)
                return



    #
    # Backend interface functions.
    #

    def get_interfaces(self) -> Iterable[USBInterface]:
        """ Returns an iterable over all interfaces on the provided device. """
        return self.interfaces.values()


    def get_descriptor(self) -> bytes:
        """ Returns this configuration's configuration descriptor, including subordinates. """
        interface_descriptors = bytearray()

        # FIXME: use construct

        # All all subordinate descriptors together to create a big subordinate descriptor.
        interfaces = sorted(self.interfaces.values(), key=lambda item: item.number)
        for interface in interfaces:
            interface_descriptors += interface.get_descriptor()

        total_len      = len(interface_descriptors) + 9
        string_manager = self.get_device().strings

        # Build the core interface descriptor.
        d = bytes([
                9,          # length of descriptor in bytes
                2,          # descriptor type 2 == configuration
                total_len & 0xff,
                (total_len >> 8) & 0xff,
                len(set(interface.number for interface in self.interfaces.values())),
                self.number,
                string_manager.get_index(self.configuration_string),
                self.attributes,
                self.max_power // 2
        ])

        return d + interface_descriptors


    #
    # Interfacing functions for AutoInstantiable.
    #
    def get_identifier(self) -> int:
        return self.number


    #
    # Backend functions for our RequestHandler class.
    #

    def _request_handlers(self) -> Iterable[callable]:
        return ()

    def _get_subordinate_handlers(self) -> Iterable[USBInterface]:
        return self.interfaces.values()
