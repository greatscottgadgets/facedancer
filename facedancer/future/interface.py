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
from .descriptor  import USBDescribable, USBDescriptor, USBClassDescriptor
from .request     import USBRequestHandler, get_request_handler_methods
from .request     import standard_request_handler, to_interface
from .endpoint    import USBEndpoint

# Create a default logger for the module.
logger = logging.getLogger(__name__)

@dataclass
class USBInterface(USBDescribable, AutoInstantiable, USBRequestHandler):
    DESCRIPTOR_TYPE_NUMBER = 0x4

    name : str = "generic USB interface"


    number                 : int = 0
    alternate              : int = 0

    class_number           : int = 0
    subclass_number        : int = 0
    protocol_number        : int = 0

    interface_string_index : int = 0

    endpoints              : List[USBEndpoint] = field(default_factory = lambda : [])

    descriptors            : Dict[int, bytes]  = None
    class_descriptor       : bytes = None

    parent                 : USBDescribable = None


    def __post_init__(self):

        # FIXME: use our dictionary
        self._endpoints = instantiate_subordinates(self, USBEndpoint)
        self.endpoints = list(self._endpoints.values())

        # If we don't have a collection of descriptors, gather any attached to the class.
        if not self.descriptors:
            self.descriptors = instantiate_subordinates(self, USBDescriptor)

        # If we weren't provided with a class descriptor, try to find one provided on the class.
        if self.class_descriptor is None:
            class_descriptors = instantiate_subordinates(self, USBClassDescriptor)
            self.class_descriptor = list(class_descriptors.values())[0] if class_descriptors else None

        self.descriptors[USB.desc_type_interface] = self.get_descriptor
        self.configuration = None

        # populate our handlers
        self._request_handler_methods = get_request_handler_methods(self)


    @classmethod
    def from_binary_descriptor(cls, data):
        """
            Generates an interface object from a descriptor.
        """
        interface_number, alternate_setting, num_endpoints, interface_class, \
                interface_subclass, interface_protocol, interface_string_index \
                = struct.unpack_from("xxBBBBBBB", data)
        return cls(interface_number, alternate_setting, interface_class,
                   interface_subclass, interface_protocol, interface_string_index)


    #def __repr__(self):
    #    endpoints = [endpoint.number for endpoint in self.endpoints]

    #    return "<USBInterface number={} alternate={} class={} subclass={} protocol={} string_index={} endpoints={}>".format(
    #            self.number, self.alternate, self.class, self.subclass, self.protocol, self.string_index, endpoints
    #    )

    def set_configuration(self, config):
        self.configuration = config

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
            self.configuration.device.maxusb_app.stall_ep0()

        if callable(response):
            response = response(dindex)

        if response:
            n = min(n, len(response))
            self.configuration.device.maxusb_app.send_on_endpoint(0, response[:n])

            logger.debug(self.name, "sent", n, "bytes in response")


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
        for e in self.endpoints:
            d += e.get_descriptor()

        return d


    def get_identifier(self):
        return self.number


    #
    # Request handler functions.
    #

    def _request_handlers(self):
        return self._request_handler_methods

    def _get_subordinate_handlers(self):
        return self._endpoints.values()
