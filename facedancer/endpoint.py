#
# This file is part of Facedancer
#
""" Functionality for describing USB endpoints. """

# Support annotations on Python < 3.9
from __future__  import annotations

import struct
import textwrap

from typing      import Iterable, List, Dict
from dataclasses import field
from collections import defaultdict

from .magic      import AutoInstantiable, instantiate_subordinates
from .descriptor import USBDescribable, USBDescriptor
from .request    import USBRequestHandler, get_request_handler_methods
from .request    import to_this_endpoint, standard_request_handler
from .types      import USBDirection, USBTransferType, USBSynchronizationType
from .types      import USBUsageType, USBStandardRequests

from .logging    import log


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
    def from_binary_descriptor(cls, data, strings={}):
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
            direction=USBDirection(direction),
            transfer_type=USBTransferType(transfer_type),
            synchronization_type=USBSynchronizationType(sync_type),
            usage_type=USBUsageType(usage_type),
            max_packet_size=max_packet_size,
            interval=interval,
            extra_bytes=data[7:]
        )


    def __post_init__(self):

        # Capture any descriptors declared directly on the class.
        for descriptor in instantiate_subordinates(self, USBDescriptor):
            self.add_descriptor(descriptor)

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
        identifier = descriptor.get_identifier()
        desc_name = type(descriptor).__name__

        if descriptor.include_in_config:
            self.attached_descriptors.append(descriptor)
            descriptor.parent = self

        elif descriptor.number is None:
            raise Exception(
                f"Descriptor of type {desc_name} cannot be added to this "
                f"endpoint because it is not to be included in the "
                f"configuration descriptor, yet does not have a number "
                f"to request it separately with")

        elif identifier in self.requestable_descriptors:
            other = self.requestable_descriptors[identifier]
            other_name = type(other).__name__
            other_type = f"0x{other.type_number:02X}"
            raise Exception(
                f"Descriptor of type {desc_name} cannot be added to this "
                f"endpoint because there is already a descriptor of type "
                f"{other_name} with the same type code {other_type} and "
                f"number {other.number}")

        else:
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


    def generate_code(self, name=None, indent=0):

        if name is None:
            name = f"Endpoint_{self.number}_{self.direction.name}"

        direction = f"USBDirection.{self.direction.name}"
        transfer_type = f"USBTransferType.{self.transfer_type.name}"
        sync_type = f"USBSynchronizationType.{self.synchronization_type.name}"
        usage_type = f"USBUsageType.{self.usage_type.name}"

        values = str.join(", ", map(lambda x: f"0x{x:02x}", self.extra_bytes))

        code = f"""
class {name}(USBEndpoint):
    number               = {self.number}
    direction            = {direction}
    transfer_type        = {transfer_type}
    synchronization_type = {sync_type}
    usage_type           = {usage_type}
    max_packet_size      = {self.max_packet_size}
    interval             = {self.interval}
    extra_bytes          = bytes([{values}])
"""

        # Use alphabetic suffixes to distinguish between multiple attached
        # descriptors with the same type number.
        suffixes = defaultdict(lambda: 'A')

        for descriptor in self.attached_descriptors:
            type_number = descriptor.type_number
            suffix = suffixes[type_number]
            suffixes[type_number] = chr(ord(suffix) + 1)
            name = f"Descriptor_0x{type_number:02X}_{suffix}"
            code += descriptor.generate_code(name=name, indent=4)

        for descriptor_id in sorted(self.requestable_descriptors):
            descriptor = self.requestable_descriptors[descriptor_id]
            code += descriptor.generate_code(indent=4)

        return textwrap.indent(code, indent * ' ')
