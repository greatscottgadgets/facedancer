#
# This file is part of Facedancer
#
""" Functionality for describing USB endpoints. """

# Support annotations on Python < 3.9
from __future__  import annotations

import struct

from typing      import Iterable, List, Dict
from dataclasses import dataclass, field

from .magic      import AutoInstantiable
from .descriptor import USBDescribable, USBDescriptor
from .request    import USBRequestHandler, get_request_handler_methods
from .request    import to_this_endpoint, standard_request_handler
from .types      import USBDirection, USBTransferType, USBSynchronizationType
from .types      import USBUsageType, USBStandardRequests

from .logging    import log


@dataclass
class USBEndpoint(USBDescribable, AutoInstantiable, USBRequestHandler):
    """ Class representing a USBEndpoint object.

    Field:
        number:
            The endpoint number (without the direction bit) for this endpoint.
        direction:
            A USBDirection constant indicating this endpoint's direction.
        transfer_type:
            A USBTransferType constant indicating the type of communications used.
        max_packet_size:
            The maximum packet size for this endpoint.
        interval:
            The polling interval, for an INTERRUPT endpoint.
    """
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

    # Extra bytes that extend the basic endpoint descriptor.
    extra_bytes          : bytes = b''

    # Descriptors that will be included in a GET_CONFIGURATION response.
    attached_descriptors : List[USBDescriptor] = field(default_factory=list)

    # Descriptors that can be requested with the GET_DESCRIPTOR request.
    requestable_descriptors : Dict[tuple[int, int], USBDescriptor] = field(default_factory=dict)

    parent               : USBDescribable = None


    @classmethod
    def from_binary_descriptor(cls, data):
        """
        Creates an endpoint object from a description of that endpoint.
        """

        # Parse the core descriptor into its components...
        address, attributes, max_packet_size, interval = struct.unpack_from("xxBBHB", data)

        # ... and break down the packed fields.
        number        = address & 0x7F
        direction     = address >> 7
        transfer_type = attributes & 0b11
        sync_type     = attributes >> 2 & 0b1111
        usage_type    = attributes >> 4 & 0b11

        return cls(
            number=number,
            direction=direction,
            transfer_type=transfer_type,
            synchronization_type=sync_type,
            usage_type=usage_type,
            max_packet_size=max_packet_size,
            interval=interval,
            extra_bytes=data[7:]
        )


    def __post_init__(self):

        # Grab our request handlers.
        self._request_handler_methods = get_request_handler_methods(self)

    #
    # User interface.
    #

    @staticmethod
    def address_for_number(endpoint_number: int, direction: USBDirection) -> int:
        """ Computes the endpoint address for a given number + direction. """
        direction_mask = 0x80 if direction == USBDirection.IN else 0x00
        return endpoint_number | direction_mask


    def get_device(self):
        """ Returns the device associated with the given descriptor. """
        return self.parent.get_device()


    def send(self, data: bytes, *, blocking: bool = False):
        """ Sends data on this endpoint. Valid only for IN endpoints.

        Args:
            data     : The data to be sent.
            blocking : True if we should block until the backend reports
                        the transmission to be complete.
        """
        self.get_device()._send_in_packets(self.number, data,
            packet_size=self.max_packet_size, blocking=blocking)


    #
    # Event handlers.
    #

    def handle_data_received(self, data: bytes):
        """ Handler for receipt of non-control request data.

        Args:
            data   : The raw bytes received.
        """
        log.info(f"EP{self.number} received {len(data)} bytes of data; "
                "but has no handler.")


    def handle_data_requested(self):
        """ Handler called when the host requests data on this endpoint."""


    def handle_buffer_empty(self):
        """ Handler called when this endpoint first has an empty buffer. """


    @standard_request_handler(number=USBStandardRequests.CLEAR_FEATURE)
    @to_this_endpoint
    def handle_clear_feature_request(self, request):
        log.debug(f"received CLEAR_FEATURE request for endpoint {self.number} "
            f"with value {request.value}")
        request.acknowledge()


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


    @property
    def attributes(self):
        """ Fetches the attributes for the given endpoint, as a single byte. """
        return (self.transfer_type & 0x03)               | \
               ((self.synchronization_type & 0x03) << 2) | \
               ((self.usage_type & 0x03) << 4)


    def add_descriptor(self, descriptor: USBDescriptor):
        """ Adds the provided descriptor to the endpoint. """
        if descriptor.include_in_config:
            self.attached_descriptors.append(descriptor)
        else:
            identifier = descriptor.get_identifier()
            self.requestable_descriptors[identifier] = descriptor
        descriptor.parent = self


    def get_descriptor(self) -> bytes:
        """ Get a descriptor string for this endpoint. """
        # FIXME: use construct

        d = bytearray([
                # length of descriptor in bytes
                7 + len(self.extra_bytes),
                # descriptor type 5 == endpoint
                5,
                self.address,
                self.attributes,
                self.max_packet_size & 0xff,
                (self.max_packet_size >> 8) & 0xff,
                self.interval
        ])

        return d + self.extra_bytes


    #
    # Automatic instantiation helpers.
    #

    def get_identifier(self) -> int:
        return self.address

    def matches_identifier(self, other:int) -> bool:
        # Use only the MSB and the lower nibble; per the USB specification.
        masked_other = other & 0b10001111
        return self.get_identifier() == masked_other


    #
    # Request handling.
    #

    def _request_handlers(self) -> Iterable[callable]:
        return self._request_handler_methods


    #
    # Pretty-printing.
    #
    def __str__(self):
        direction     = USBDirection(self.direction).name
        transfer_type = USBTransferType(self.transfer_type).name
        is_interrupt  = (self.transfer_type == USBTransferType.INTERRUPT)
        additional    = f" every {self.interval}ms" if is_interrupt else ""

        return f"endpoint {self.number:02x}/{direction}: {transfer_type} transfers{additional}"
