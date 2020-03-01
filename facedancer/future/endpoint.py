#
# This file is part of FaceDancer
#
""" Functionality for describing USB endpoints. """

import struct

from dataclasses import dataclass

from ..USB import *

from .magic      import AutoInstantiable
from .descriptor import USBDescribable
from .request    import USBRequestHandler, get_request_handler_methods, standard_request_handler, to_endpoint
from .types      import USBDirection, USBTransferType, USBSynchronizationType, USBUsageType


@dataclass
class USBEndpoint(USBDescribable, AutoInstantiable, USBRequestHandler):

    DESCRIPTOR_TYPE_NUMBER      = 0x05

    # Core identifiers.
    number               : int
    direction            : USBDirection

    # Endpoint attributes.
    transfer_type        : USBTransferType        = USBTransferType.BULK
    synchronization_type : USBSynchronizationType = USBSynchronizationType.NONE
    usage_type           : USBUsageType           = USBUsageType.DATA

    max_packet_size      : int = 64
    interval             : int = 0

    parent               : USBDescribable = None


    def __post_init__(self):
        self._request_handler_methods = get_request_handler_methods(self)


    def get_address(self):
        """ Returns the address for the given endpoint. """
        direction_mask = 0x80 if self.direction == USBDirection.IN else 0x00
        return self.number | direction_mask


    def __repr__(self):
        # TODO: make these nice string representations
        transfer_type = self.transfer_type
        sync_type = self.synchronization_type
        usage_type = self.usage_type
        direction = "IN" if self.direction else "OUT"

        # TODO: handle high/superspeed; don't assume 1ms frames
        interval = self.interval

        return "<USBEndpoint number={} direction={} transfer_type={} sync_type={} usage_type={} max_packet_size={} interval={}ms>".format(
            self.number, direction, transfer_type, sync_type, usage_type, self.max_packet_size, interval
        )



    @standard_request_handler(number=1)
    @to_endpoint
    def handle_clear_feature_request(self, req):
        print("received CLEAR_FEATURE request for endpoint", self.number,
                "with value", req.value)
        self.parent.configuration.device.maxusb_app.send_on_endpoint(0, b'')


    # see Table 9-13 of USB 2.0 spec (pdf page 297)
    def get_descriptor(self):
        address = (self.number & 0x0f) | (self.direction << 7)
        attributes = (self.transfer_type & 0x03) \
                   | ((self.synchronization_type & 0x03) << 2) \
                   | ((self.usage_type & 0x03) << 4)

        d = bytearray([
                7,          # length of descriptor in bytes
                5,          # descriptor type 5 == endpoint
                address,
                attributes,
                self.max_packet_size & 0xff,
                (self.max_packet_size >> 8) & 0xff,
                self.interval
        ])

        return d

    def send_packet(self, data, blocking=False):
        dev = self.parent.parent.parent
        dev.maxusb_app.send_on_endpoint(self.number, data, blocking=blocking)


    def send(self, data):
        # Send the relevant data one packet at a time,
        # chunking if we're larger than the max packet size.
        # This matches the behavior of the MAX3420E.
        while data:
            packet = data[0:self.max_packet_size]
            data = data[self.max_packet_size:]

            self.send_packet(packet)


    def recv(self):
        dev = self.parent.parent.parent
        data = dev.maxusb_app.read_from_endpoint(self.number)
        return data

    def get_identifier(self):
        return self.number


    #
    # Request handling.
    #

    def _request_handlers(self):
        return self._request_handler_methods
