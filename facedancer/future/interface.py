# USBInterface.py
#
# Contains class definition for USBInterface.

import struct
import logging

from typing       import List, Dict
from dataclasses  import dataclass, field

from ..USB import *
from ..USBClass import USBClass

from .magic       import instantiate_subordinates, AutoInstantiable
from .types       import USBDirection

from .descriptor  import USBDescribable, USBDescriptor, USBClassDescriptor
from .request     import USBRequestHandler, get_request_handler_methods
from .request     import standard_request_handler, to_interface
from .endpoint    import USBEndpoint

# Create a default logger for the module.
logger = logging.getLogger("interface")

@dataclass
class USBInterface(USBDescribable, AutoInstantiable, USBRequestHandler):
    DESCRIPTOR_TYPE_NUMBER = 0x4

    name                   : str = "generic USB interface"

    number                 : int = 0
    alternate              : int = 0

    class_number           : int = 0
    subclass_number        : int = 0
    protocol_number        : int = 0

    # FIXME: replace with an interface string
    interface_string_index : int = 0

    descriptors            : Dict[int, bytes] = field(default_factory=dict)
    class_descriptor       : bytes = None

    parent                 : USBDescribable = None


    def __post_init__(self):

        # FIXME: cleanup

        self.endpoints = instantiate_subordinates(self, USBEndpoint)

        subordinate_descriptors = instantiate_subordinates(self, USBDescriptor)
        self.descriptors.update(subordinate_descriptors)

        # If we weren't provided with a class descriptor, try to find one provided on the class.
        if self.class_descriptor is None:
            class_descriptors = instantiate_subordinates(self, USBClassDescriptor)
            self.class_descriptor = list(class_descriptors.values())[0] if class_descriptors else None

        self.descriptors[USB.desc_type_interface] = self.get_descriptor
        self.configuration = None

        # populate our handlers
        self._request_handler_methods = get_request_handler_methods(self)


    #
    # User interface.
    #

    def get_device(self):
        """ Returns the device associated with the given descriptor. """
        return self.parent.get_device()


    def get_endpoint(self, endpoint_number: int, direction: USBDirection) -> USBEndpoint:
        """ Attempts to find a subordinate endpoint matching the given number/direction.

        Parameters:
            endpoint_number -- The endpoint number to search for.
            direction       -- The endpoint direction to be matched.

        Returns:
            The matching endpoint; or None if no matching endpoint existed.
        """
        address = USBEndpoint.address_for_number(endpoint_number, direction)
        return self.endpoints.get(address, None)


    def has_endpoint(self, endpoint_number: int, direction: USBDirection) -> USBEndpoint:
        """ Returns true iff we have matching subordinate endpoint.

        Parameters:
            endpoint_number -- The endpoint number to search for.
            direction       -- The endpoint direction to be matched.
        """
        return (self.get_endpoint(endpoint_number, direction) is not None)


    #
    # Event handlers.
    #

    def handle_data_received(self, endpoint_number: int, data: bytes):
        """ Handler for receipt of non-control request data.

        Typically, this method will delegate any data received to the
        appropriate configuration/interface/endpoint. If overridden, the
        overriding function will receive all data; and can delegate it by
        calling the `.handle_data_received` method on `self.configuration`.

        Parameters:
            endpoint_number -- The endpoint number on which the data was received.
            data            -- The raw bytes received on the relevant endpoint.
        """
        endpoint = self.get_endpoint(endpoint_number, USBDirection.OUT)

        if endpoint:
            endpoint.handle_data_received(data)
        else:
            self.get_device().handle_unexpected_data_received(endpoint_number, data)


    def handle_data_requested(self, endpoint_number: int):
        """ Handler called when the host requests data on a non-control endpoint.

        Typically, this method will delegate the request to the appropriate
        interface+endpoint. If overridden, the overriding function will receive
        all data.

        Parameters:
            endpoint_number -- The endpoint number on which the host requested data.
        """
        endpoint = self.get_endpoint(endpoint_number, USBDirection.IN)

        if endpoint:
            endpoint.handle_data_requested()
        else:
            self.get_device().handle_unexpected_data_requested(endpoint_number)


    def handle_buffer_empty(self, endpoint_number: int):
        """ Handler called when a given endpoint first has an empty buffer.

        Often, an empty buffer indicates an opportunity to queue data
        for sending ('prime an endpoint'), but doesn't necessarily mean
        that the host is planning on reading the data.

        This function is called only once per buffer.
        """

        endpoint = self.get_endpoint(endpoint_number, USBDirection.IN)
        if endpoint:
            endpoint.handle_buffer_empty()


    #
    # Backend helpers.
    #

    def get_endpoints(self):
        """ Returns an iterable over all endpoints in this interface. """
        return self.endpoints.values()


    #
    # Internal interface.
    #

    # USB 2.0 specification, section 9.4.3 (p 281 of pdf)
    # HACK: blatant copypasta from USBDevice pains me deeply
    @standard_request_handler(number=6)
    @to_interface
    def handle_get_descriptor_request(self, req):
        dtype  = (req.value >> 8) & 0xff
        dindex = req.value & 0xff
        lang   = req.index
        n      = req.length

        response = None

        logger.debug(f"{self.name} received GET_DESCRIPTOR at interface req {dtype}, index {dindex}, " \
                    + f"language {lang:04x}, length {n}")

        # TODO: handle KeyError
        try:
            response = self.descriptors[dtype]
        except KeyError:
            req.stall()

        if callable(response):
            response = response(dindex)

        if response:
            n = min(n, len(response))
            req.reply(response[:n])

            logger.debug(f"sent {n} bytes in response")


    @standard_request_handler(number=11)
    @to_interface
    def handle_set_interface_request(self, req):
        # FIXME: is stalling here right?
        self.configuration.device.maxusb_app.stall_ep0()


    # Table 9-12 of USB 2.0 spec (pdf page 296)
    def get_descriptor(self):
        d = bytearray([
                9,          # length of descriptor in bytes
                4,          # descriptor type 4 == interface
                self.number,
                self.alternate,
                len(self.endpoints),
                self.class_number,
                self.subclass_number,
                self.protocol_number,
                self.interface_string_index
        ])

        # If we have a class object, append its class descriptor...
        if self.class_descriptor:
            if callable(self.class_descriptor):
                d += self.class_descriptor()
            else:
                d += self.class_descriptor

        # ... append each endpoint's endpoint descriptor.
        for e in self.endpoints.values():
            d += e.get_descriptor()

        return d

    #
    # Automatic instantiation support.
    #

    def get_identifier(self):
        return self.number


    #
    # Request handler functions.
    #

    def _request_handlers(self):
        return self._request_handler_methods

    def _get_subordinate_handlers(self):
        return self.endpoints.values()
