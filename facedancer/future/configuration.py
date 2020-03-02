#
# This file is part of FaceDancer.
#
""" Functionality for describing USB device configurations. """


import typing
import struct
import logging

from dataclasses  import dataclass

from .types       import USBDirection
from .magic       import instantiate_subordinates, AutoInstantiable
from .request     import USBRequestHandler, USBControlRequest

from .interface   import USBInterface
from .descriptor  import USBDescribable
from .endpoint    import USBEndpoint

# TODO: Section these out into their own folder?
from ..USBClass import USBClass
from ..HIDClass import HIDClass


# Create a default logger for the module.
logger = logging.getLogger("configuration")

@dataclass
class USBConfiguration(USBDescribable, AutoInstantiable, USBRequestHandler):
    """ Class representing a USBDevice's configuration. """

    DESCRIPTOR_TYPE_NUMBER     = 0x02
    DESCRIPTOR_SIZE_BYTES      = 9


    configuration_index  : int            = 1
    configuration_string : str            = None

    attributes           : int            = 0xe0
    max_power            : int            = 250

    parent               : USBDescribable = None


    def __post_init__(self):

        # Gather any interfaces
        self.interfaces = instantiate_subordinates(self, USBInterface)


    #
    # User API.
    #

    def get_device(self):
        """ Returns a reference to the associated device."""
        return self.parent


    def add_interface(self, interface: USBInterface):
        """ Adds an interface to the configuration. """
        self.interfaces[interface.number] = interface


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

    def get_interfaces(self):
        """ Returns an iterable of all interfaces on the provided device. """
        return self.interfaces.values()


    def get_descriptor(self):
        interface_descriptors = bytearray()

        # FIXME: sort these by their interface numbers
        for interface in self.interfaces.values():
            interface_descriptors += interface.get_descriptor()

        total_len = len(interface_descriptors) + 9

        string_manager = self.get_device().strings

        d = bytes([
                9,          # length of descriptor in bytes
                2,          # descriptor type 2 == configuration
                total_len & 0xff,
                (total_len >> 8) & 0xff,
                len(set(interface.number for interface in self.interfaces.values())),
                self.configuration_index,
                string_manager.get_index(self.configuration_string),
                self.attributes,
                self.max_power
        ])

        return d + interface_descriptors




    #
    # Interfacing functions for AutoInstantiable.
    #
    def get_identifier(self):
        return self.configuration_index


    #
    # Backend functions for our RequestHandler class.
    #

    def _request_handlers(self):
        return ()

    def _get_subordinate_handlers(self):
        return self.interfaces.values()
