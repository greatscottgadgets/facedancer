#
# This file is part of FaceDancer
#
""" Functionality for describing USB endpoints. """

import struct
import logging

from dataclasses import dataclass

from ..USB import *

from .magic      import AutoInstantiable
from .descriptor import USBDescribable
from .request    import USBRequestHandler, get_request_handler_methods, standard_request_handler, to_endpoint
from .types      import USBDirection, USBTransferType, USBSynchronizationType, USBUsageType


# Create a default logger for the module.
logger = logging.getLogger(__name__)


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


    @staticmethod
    def address_for_number(endpoint_number: int, direction: USBDirection):
        direction_mask = 0x80 if direction == USBDirection.IN else 0x00
        return endpoint_number | direction_mask


    #
    # User interface.
    #

    def get_device(self):
        """ Returns the device associated with the given descriptor. """
        return self.parent.get_device()


    def send(self, data, *, blocking=False):
        """ Sends data on this endpoint. Valid only for IN endpoints.

        Parameters:
            data     -- The data to be sent.
            blocking -- True if we should block until the backend reports
                        the transmission to be complete.
        """
        self.get_device()._send_in_packets(self.number, data,
            packet_size=self.max_packet_size, blocking=blocking)


    #
    # Event handlers.
    #

    def handle_data_received(self, data: bytes):
        """ Handler for receipt of non-control request data.

        Parameters:
            data   -- The raw bytes received.
        """
        logger.info(f"EP{self.number} received {len(data)} bytes of data; "
                "but has no handler.")


    def handle_data_requested(self):
        """ Handler called when the host requests data on this endpoint."""


    def handle_buffer_empty(self):
        """ Handler called when this endpoint first has an empty buffer. """



    #
    # Properties.
    #

    @property
    def address(self):
        """ Fetches the address for the given endpoint. """
        return self.address_for_number(self.number, self.direction)


    def get_address(self):
        """ Method alias for the address property. For backend support. """
        return self.address



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
        logger.debug(f"received CLEAR_FEATURE request for endpoint {self.number} "
            f"with value {req.value}")
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



    def recv(self):
        dev = self.parent.parent.parent
        data = dev.maxusb_app.read_from_endpoint(self.number)
        return data

    def get_identifier(self):
        return self.address


    #
    # Request handling.
    #

    def _request_handlers(self):
        return self._request_handler_methods
