#
# This file is part of FaceDancer.
#

import asyncio
import logging
import warnings

from typing         import Dict, Iterable
from dataclasses    import dataclass, field

from ..             import FacedancerUSBApp
from .types         import DescriptorTypes, LanguageIDs, USBDirection
from .magic         import instantiate_subordinates

from .descriptor    import USBDescribable, USBDescriptor, StringDescriptorManager
from .configuration import USBConfiguration
from .request       import USBControlRequest, USBRequestHandler
from .request       import standard_request_handler, to_device, get_request_handler_methods

# Create a default logger for the module.
logger = logging.getLogger("device")

# FIXME: abstract this to the logging library
LOGLEVEL_TRACE = 5

@dataclass
class USBBaseDevice(USBDescribable, USBRequestHandler):
    """
    Base-most class for FaceDancer USB devices. This version is very similar to the USBDevice type,
    except that it does not define _any_ standard handlers. This allows you the freedom to declare
    whatever standard requests you'd like.
    """

    DESCRIPTOR_TYPE_NUMBER    = 0x01
    DESCRIPTOR_LENGTH         = 0x12


    name                 : str = "generic device"

    device_class         : int  = 0
    device_subclass      : int  = 0

    protocol_rel_num     : int  = 0
    max_packet_size_ep0  : int  = 64

    vendor_id            : int  = 0x610b
    product_id           : int  = 0x4653

    manufacturer_string  : str  = "FaceDancer"
    product_string       : str  = "Generic USB Device"
    serial_number_string : str  = "S/N 3420E"

    # I feel bad for putting this as the default language ID / propagating anglocentrism,
    # but this appears to be the only language ID supported by some systems, so here it is.
    supported_langauges  : tuple = (LanguageIDs.ENGLISH_US,)

    device_rev           : int = 0
    usb_spec_version     : int  = 0x0002

    descriptors          : Dict[int, bytes]  = field(default_factory=dict)
    backend              : FacedancerUSBApp = None


    @property
    def maxusb_app(self):
        warnings.warn('maxusb_app should be replaced with backend', DeprecationWarning)
        return self.backend


    def __post_init__(self):
        """ Set up our device for execution. """

        self.strings = StringDescriptorManager()

        # If we don't have a collection of descriptors, gather any attached to the class.
        subordinate_descriptors = instantiate_subordinates(self, USBDescriptor)
        self.descriptors.update(subordinate_descriptors)

        # Add our basic descriptor handlers.
        self.descriptors.update({
            DescriptorTypes.DEVICE:        lambda _ : self.get_descriptor(),
            DescriptorTypes.CONFIGURATION: self.get_configuration_descriptor,
            DescriptorTypes.STRING:        self.get_string_descriptor
        })

        # Start off un-configured, and with an address of 0.
        self.address = 0
        self.configuration = None

        # Populate our control request handlers, and any subordinate classes we'll need to create.
        self._request_handler_methods = get_request_handler_methods(self)
        self.configurations = instantiate_subordinates(self, USBConfiguration)

    #
    # Control interface.
    #

    def connect(self):
        """ Connects this device to the host; e.g. turning on our presence-detect pull up. """
        if self.backend is None:
            self.backend = FacedancerUSBApp()

        self.backend.connect(self)


    def disconnect(self):
        """ Disconnects this device from the host. """
        self.backend.disconnect()


    async def run(self):
        """ Runs the actual device emulation. """

        if self.backend is None:
            self.connect()

        # Constantly service any events that need to be performed.
        while True:
            self.backend.service_irqs()
            await asyncio.sleep(0)


    def run_with(self, *coroutines: Iterable[asyncio.coroutine]):
        """
        Runs the actual device emulation synchronously; running any provided
        coroutines simultaneously.
        """

        async def inner():
            await asyncio.gather(self.run(), *coroutines)

        asyncio.run(inner())


    def emulate(self, *coroutines: Iterable[asyncio.coroutine]):
        """ Convenience method that runs a full method in a blocking manner.
        Performs connect, run, and then disconnect.

        Parameters:
            *coroutines -- any asyncio coroutines to be executed concurrently
                           with our emulation
        """

        self.connect()

        try:
            self.run_with(*coroutines)
        except KeyboardInterrupt:
            pass
        finally:
            self.disconnect()



    #
    # I/O interface.
    #

    def stall(self, *, endpoint_number: int = 0, direction: USBDirection = USBDirection.OUT):
        """ Stalls the provided endpoint.

        For endpoint zero, this indicates that the active (or next)
        request is not supported. For all other endpoints, this indicates
        a persistent 'halt' condition.

        Parameters:
            endpoint -- The endpoint address; or EP0 if not provided.
        """
        self.backend.stall_endpoint(endpoint_number, direction)


    # TODO: add a clear_stall() method here for non-control endpoints

    def send(self, endpoint_number: int, data: bytes, *, blocking: bool = False):
        """ Queues sending data on the IN endpoint with the provided number.

        Parameters:
            endpoint_number -- The endpoint number to send data upon.
            data            -- The data to send.
            blocking        -- If provided and true, this function will block
                               until the backend indicates the send is complete.
        """

        if endpoint_number == 0:
            self._send_in_packets(endpoint_number, data,
                packet_size=self.max_packet_size_ep0, blocking=blocking)
        elif self.configuration:
            endpoint = self.configuration.get_endpoint(endpoint_number, USBDirection.IN)
            endpoint.send(data, blocking=blocking)


    def _send_in_packets(self, endpoint_number: int, data: bytes, *,
            packet_size: int, blocking: bool = False):
        """ Queues sending data on the IN endpoint with the provided number.

        Sends the relevant data to the backend in chunks of packet_size.

        Parameters:
            endpoint_number -- The endpoint number to send data upon.
            data            -- The data to send.
            packet_size     -- The "chunk" size to send in.
            blocking        -- If provided and true, this function will block
                               until the backend indicates the send is complete.
        """

        data = bytearray(data)

        # Special case: if we have a ZLP to begin with, send it, and return.
        if not data:
            self.backend.send_on_endpoint(endpoint_number, data, blocking=blocking)
            return

        # Send the relevant data one packet at a time,
        # chunking if we're larger than the max packet size.
        # This matches the behavior of the MAX3420E.
        while data:
            packet = data[0:packet_size]
            del data[0:packet_size]

            self.backend.send_on_endpoint(endpoint_number, packet, blocking=blocking)



    def get_endpoint(self, endpoint_number: int, direction: USBDirection):
        """ Attempts to find a subordinate endpoint matching the given number/direction.

        Parameters:
            endpoint_number -- The endpoint number to search for.
            direction       -- The endpoint direction to be matched.

        Returns:
            The matching endpoint; or None if no matching endpoint existed.
        """

        if self.configuration:
            return self.configuration.get_endpoint(endpoint_number, direction)
        else:
            return None



    #
    # Backend interface helpers.
    #
    def create_request(self, raw_data):
        return USBControlRequest(raw_data, device=self)


    #
    # Backend / low-level event receivers.
    #

    def handle_nak(self, ep_num):
        """ Backend data-requested handler; for legacy compatibility.

        Prefer overriding handle_data_requested().
        """
        self.handle_data_requested(ep_num)


    def handle_buffer_available(self, ep_num):
        pass


    def handle_data_available(self, ep_num, data):
        """ Backend data-available handler; for legacy compatibility.

        Prefer overriding handle_data_received().
        """
        self.handle_data_received(ep_num, data)


    #
    # Event handlers.
    #

    def handle_request(self, request: USBControlRequest):
        """ Core control request handler.

        This function can be overridden by a subclass if desired; but the typical way to
        handle a specific control request is to the the ``@control_request_handler`` decorators.

        Parameters:
            request -- the USBControlRequest object representing the relevant request
        """
        logger.debug(f"{self.name} received request: {request}")

        # Call our base USBRequestHandler method.
        handled = super().handle_request(request)

        # As the top-most handle_request function, we have an extra responsibility:
        # we'll need to stall the endpoint if no handler was found.
        if not handled:
            logger.warning(f"Unhandled control request [{request}]; stalling.")
            self.stall()

        return handled


    def handle_data_received(self, endpoint_number: int, data: bytes):
        """ Handler for receipt of non-control request data.

        Typically, this method will delegate any data received to the
        appropriate configuration/interface/endpoint. If overridden, the
        overriding function will receive all data.

        Parameteres:
            endpoint_number -- The endpoint number on which the data was received.
            data            -- The raw bytes received on the relevant endpoint.
        """

        # If we have a configuration, delegate to it.
        if self.configuration:
            self.configuration.handle_data_received(endpoint_number, data)

        # If we're un-configured, we don't expect to receive
        # anything other than control data; defer to our "unexpected data".
        else:
            logger.error(f"Received non-control data when unconfigured!"
                    "This is invalid host behavior.")
            self.handle_unexpected_data_received(endpoint_number, data)


    def handle_unexpected_data_received(self, endpoint_number: int, data: bytes):
        """ Handler for unexpected data.

        Handles any data directed at an unexpected target; e.g. an endpoint that
        doesn't exist. Note that even if `handle_data_received` is overridden,
        this method can still be called e.g. by configuration.handle_data_received.

        Parameteres:
            endpoint_number -- The endpoint number on which the data was received.
            data            -- The raw bytes received on the relevant endpoint.
        """
        logger.error(f"Received {len(data)} bytes of data on invalid EP{endpoint_number}/OUT.")


    def handle_data_requested(self, endpoint_number: int):
        """ Handler called when the host requests data on a non-control endpoint.

        Typically, this method will delegate the request to the appropriate
        configuration+interface+endpoint. If overridden, the
        overriding function will receive all events.

        Parameters:
            endpoint_number -- The endpoint number on which the host requested data.
        """

        # If we have a configuration, delegate to it.
        if self.configuration:
            self.configuration.handle_data_requested(endpoint_number)

        # If we're un-configured, we don't expect to receive
        # anything other than control data; defer to our "unexpected data".
        else:
            logger.error(f"Received non-control data when unconfigured!"
                    "This is invalid host behavior.")
            self.handle_unexpected_data_requested(endpoint_number)


    def handle_unexpected_data_requested(self, endpoint_number: int):
        """ Handler for unexpected data requests.

        Handles any requests directed at an unexpected target; e.g. an endpoint that
        doesn't exist. Note that even if `handle_data_requested` is overridden,
        this method can still be called e.g. by configuration.handle_data_received.

        Parameters:
            endpoint_number -- The endpoint number the data was received.
        """
        logger.error(f"Host requested data on invalid EP{endpoint_number}/IN.")


    def handle_buffer_empty(self, endpoint_number: int):
        """ Handler called when a given endpoint first has an empty buffer.

        Often, an empty buffer indicates an opportunity to queue data
        for sending ('prime an endpoint'), but doesn't necessarily mean
        that the host is planning on reading the data.

        This function is called only once per buffer.
        """

        # If we have a configuration, delegate to it.
        if self.configuration:
            self.configuration.handle_buffer_empty(endpoint_number)


    #
    # Methods for USBRequestHandler.
    #

    def _request_handlers(self):
        return self._request_handler_methods


    def _get_subordinate_handlers(self):
        # As a device, our subordinates are our configurations.
        return self.configurations.values()



    #
    # Backend helpers.
    #


    def ack_status_stage(self, blocking=False):
        self.backend.ack_status_stage(blocking=blocking)


    def set_address(self, address, defer=False):
        self.backend.set_address(address, defer)


    def get_descriptor(self, n=0x12):
        d = bytearray([
            18,         # length of descriptor in bytes
            1,          # descriptor type 1 == device
            (self.usb_spec_version >> 8) & 0xff,
            self.usb_spec_version & 0xff,
            self.device_class,
            self.device_subclass,
            self.protocol_rel_num,
            self.max_packet_size_ep0,
            self.vendor_id & 0xff,
            (self.vendor_id >> 8) & 0xff,
            self.product_id & 0xff,
            (self.product_id >> 8) & 0xff,
            (self.device_rev >> 8) & 0xff,
            self.device_rev & 0xff,
            self.strings.get_index(self.manufacturer_string),
            self.strings.get_index(self.product_string),
            self.strings.get_index(self.serial_number_string),
            len(self.configurations)
        ])
        return d[:n]

    def send_control_message(self, data):
        self.backend.send_on_endpoint(0, data)

    def get_configuration_descriptor(self, num):
        return self.configurations[num + 1].get_descriptor()


    def handle_get_supported_langauges_descriptor(self):
        """ Returns the special string-descriptor-zero that indicates which langauges are supported. """

        # Our string descriptor is going to have two header bytes, plus two bytes
        # for each language.
        total_length = (len(self.supported_langauges) * 2) + 2
        packet = bytearray([total_length, DescriptorTypes.STRING])

        for language in self.supported_langauges:
            packet.extend(language.to_bytes(2, byteorder='little'))

        return bytes(packet)


    def get_string_descriptor(self, index):
        """ Returns the string descriptor associated with a given index. """

        if index == 0:
            return self.handle_get_supported_langauges_descriptor()
        else:
            return self.strings[index]



class USBDevice(USBBaseDevice):
    """ Class representing the behavior of a USB device. """


    @standard_request_handler(number=0)
    @to_device
    def handle_get_status_request(self, req):
        # USB 2.0 specification, section 9.4.5 (p 282 of pdf)

        logger.debug("received GET_STATUS request")

        # self-powered and remote-wakeup (USB 2.0 Spec section 9.4.5)
        response = b'\x03\x00'
        self.send_control_message(response)


    @standard_request_handler(number=1)
    @to_device
    def handle_clear_feature_request(self, req):
        # USB 2.0 specification, section 9.4.1 (p 280 of pdf)

        logger.info(f"Received CLEAR_FEATURE request with type {req.number} and value {req.value}.")
        self.ack_status_stage()


    # USB 2.0 specification, section 9.4.9 (p 286 of pdf)
    @standard_request_handler(number=3)
    @to_device
    def handle_set_feature_request(self, req):
        logger.info("received SET_FEATURE request")


    # USB 2.0 specification, section 9.4.6 (p 284 of pdf)
    @standard_request_handler(number=5)
    @to_device
    def handle_set_address_request(self, req):
        self.address = req.value
        self.ack_status_stage(blocking=True)
        self.set_address(self.address)


    # USB 2.0 specification, section 9.4.3 (p 281 of pdf)
    @standard_request_handler(number=6)
    @to_device
    def handle_get_descriptor_request(self, request):
        dtype  = (request.value >> 8) & 0xff
        dindex = request.value & 0xff
        lang   = request.index
        n      = request.length

        response = None
        logger.debug(f"received GET_DESCRIPTOR request {request}")

        response = self.descriptors.get(dtype, None)

        while callable(response):
            response = response(dindex)

        if response:
            n = min(n, len(response))
            request.reply(response[:n])
            logger.log(LOGLEVEL_TRACE, f"sent {n} bytes in response")
        else:
            request.stall()

    # USB 2.0 specification, section 9.4.8 (p 285 of pdf)
    @standard_request_handler(number=7)
    @to_device
    def handle_set_descriptor_request(self, req):
        logger.info("received SET_DESCRIPTOR request")


    # USB 2.0 specification, section 9.4.2 (p 281 of pdf)
    @standard_request_handler(number=8)
    @to_device
    def handle_get_configuration_request(self, req):
        logger.debug(f"received GET_CONFIGURATION request with data {req.value}")

        # If we haven't yet been configured, send back a zero configuration value.
        if self.configuration is None:
            self.send_control_message(b'\x00')
        # Otherwise, return the index for our configuration.
        else:
            config_index = self.configuration.configuration_index
            self.send_control_message(config_index.to_bytes(1, byteorder='little'))


    # USB 2.0 specification, section 9.4.7 (p 285 of pdf)
    @standard_request_handler(number=9)
    @to_device
    def handle_set_configuration_request(self, req):
        logger.debug("received SET_CONFIGURATION request")

        self.configuration = self.configurations[req.value]
        req.acknowledge()

        # notify the device of the reconfiguration, in case
        # it needs to e.g. set up endpoints accordingly
        self.backend.configured(self.configuration)


    # USB 2.0 specification, section 9.4.4 (p 282 of pdf)
    @standard_request_handler(number=10)
    @to_device
    def handle_get_interface_request(self, req):
        logger.debug("received GET_INTERFACE request")

        if req.index == 0:
            # HACK: currently only support one interface
            self.send_control_message(b'\x00')
        else:
            self.backend.stall_ep0()


    # USB 2.0 specification, section 9.4.10 (p 288 of pdf)
    @standard_request_handler(number=11)
    @to_device
    def handle_set_interface_request(self, req):
        logger.debug(f"f{self.name} received SET_INTERFACE request")


    # USB 2.0 specification, section 9.4.11 (p 288 of pdf)
    @standard_request_handler(number=12)
    @to_device
    def handle_synch_frame_request(self, req):
        logger.debug(f"f{self.name} received SYNCH_FRAME request")
