#
# This file is part of FaceDancer.
#

import struct
import asyncio
import logging
import warnings

from typing      import Dict
from dataclasses import dataclass, field

from .. import FacedancerUSBApp

from ..USB              import *
from ..USBClass         import *
from ..core             import FacedancerBasicScheduler

from .types         import DescriptorTypes, LanguageIDs
from .magic         import instantiate_subordinates

from .descriptor    import USBDescribable, USBDescriptor, StringDescriptorManager
from .configuration import USBConfiguration
from .request       import USBControlRequest, USBRequestHandler
from .request       import standard_request_handler, to_device, get_request_handler_methods


# Create a default logger for the module.
logger = logging.getLogger(__name__)


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

    descriptors          : Dict[int, bytes]  = None

    backend              : FacedancerUSBApp = None


    @property
    def maxusb_app(self):
        warnings.warn('maxusb_app should be replaced with backend', DeprecationWarning)
        return self.backend


    def __post_init__(self):
        """ Set up our device for execution. """

        self._strings = StringDescriptorManager()

        # If we don't have a collection of descriptors, gather any attached to the class.
        if not self.descriptors:
            self.descriptors = instantiate_subordinates(self, USBDescriptor)

        # Add our basic descriptor handlers.
        self.descriptors[DescriptorTypes.DEVICE]        = lambda _ : self.get_descriptor()
        self.descriptors[DescriptorTypes.CONFIGURATION] = self.handle_get_configuration_descriptor_request
        self.descriptors[DescriptorTypes.STRING]        = self.handle_get_string_descriptor_request

        # Start off un-configured, and with an address of 0.
        self.address = 0
        self.configuration = None

        # Populate our control request handlers, and any subordinate classes we'll need to create.
        self._request_handler_methods = get_request_handler_methods(self)
        self._configurations = instantiate_subordinates(self, USBConfiguration)

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


    def run_with(self, *coroutines):
        """
        Runs the actual device emulation synchronously; running any provided
        coroutines simultaneously.
        """

        async def inner():
            await asyncio.gather(self.run(), *coroutines)

        asyncio.run(inner())


    def emulate(self, *coroutines):
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
            self._strings.get_index(self.manufacturer_string),
            self._strings.get_index(self.product_string),
            self._strings.get_index(self.serial_number_string),
            len(self._configurations)
        ])
        return d[:n]

    def send_control_message(self, data):
        self.backend.send_on_endpoint(0, data)

    def handle_get_configuration_descriptor_request(self, num):
        return self._configurations[num + 1].get_descriptor()


    def handle_get_supported_langauges_descriptor(self):
        """ Returns the special string-descriptor-zero that indicates which langauges are supported. """

        # Our string descriptor is going to have two header bytes, plus two bytes
        # for each language.
        total_length = (len(self.supported_langauges) * 2) + 2
        packet = bytearray([total_length, DescriptorTypes.STRING])

        for language in self.supported_langauges:
            packet.extend(language.to_bytes(2, byteorder='little'))

        return bytes(packet)

    def handle_get_string_descriptor_request(self, num):
        """ Returns the string descriptor associated with a given index. """
        if num == 0:
            return self.handle_get_supported_langauges_descriptor()
        else:
            return self._strings[num]


    #
    # Backend interface helpers.
    #
    @staticmethod
    def create_request(raw_data):
        return USBControlRequest(raw_data)


    #
    # Event handlers.
    #

    def _request_handlers(self):
        return self._request_handler_methods


    def _get_subordinate_handlers(self):
        # As a device, our subordinates are our configurations.
        return self._configurations.values()


    def handle_request(self, request):
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
            logger.info(f"unhandled request {repr(request)}; stalling")
            self.backend.stall_ep0()

        return handled


    def handle_data_available(self, ep_num, data):
        pass


    def handle_buffer_available(self, ep_num):
        pass


    def handle_nak(self, ep_num):
        pass


    #
    # Pretty-printing and metadata.
    #



class USBDevice(USBBaseDevice):
    """ Class representing the behavior of a USB device. """


    @standard_request_handler(number=0)
    @to_device
    def handle_get_status_request(self, req):
        # USB 2.0 specification, section 9.4.5 (p 282 of pdf)

        logger.debug(self.name, "received GET_STATUS request")

        # self-powered and remote-wakeup (USB 2.0 Spec section 9.4.5)
        response = b'\x03\x00'
        self.send_control_message(response)


    @standard_request_handler(number=1)
    @to_device
    def handle_clear_feature_request(self, req):
        # USB 2.0 specification, section 9.4.1 (p 280 of pdf)

        logger.info(self.name, "received CLEAR_FEATURE request with type 0x%02x and value 0x%02x" \
                % (req.request_type, req.value))
        self.ack_status_stage()


    # USB 2.0 specification, section 9.4.9 (p 286 of pdf)
    @standard_request_handler(number=3)
    @to_device
    def handle_set_feature_request(self, req):
        logger.info(self.name, "received SET_FEATURE request")


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
    def handle_get_descriptor_request(self, req):
        dtype  = (req.value >> 8) & 0xff
        dindex = req.value & 0xff
        lang   = req.index
        n      = req.length

        response = None

        logger.debug(self.name, ("received GET_DESCRIPTOR req %d, index %d, " \
                + "language 0x%04x, length %d") \
                % (dtype, dindex, lang, n))

        response = self.descriptors.get(dtype, None)

        while callable(response):
            response = response(dindex)

        if response:
            n = min(n, len(response))
            self.send_control_message(response[:n])
            logger.debug(self.name, "sent", n, "bytes in response")
        else:
            self.backend.stall_ep0()

    # USB 2.0 specification, section 9.4.8 (p 285 of pdf)
    @standard_request_handler(number=7)
    @to_device
    def handle_set_descriptor_request(self, req):
        print(self.name, "received SET_DESCRIPTOR request")


    # USB 2.0 specification, section 9.4.2 (p 281 of pdf)
    @standard_request_handler(number=8)
    @to_device
    def handle_get_configuration_request(self, req):
        logger.debug(self.name, "received GET_CONFIGURATION request with data 0x%02x" \
                    % req.value)

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
        logger.debug(self.name, "received SET_CONFIGURATION request")

        self.configuration = self._configurations[req.value]

        # collate endpoint numbers
        # FIXME: get rid of this
        self.endpoints = { }
        for i in self.configuration.interfaces:
            for e in i.endpoints:
                self.endpoints[e.number] = e

        # HACK: blindly acknowledge request
        self.ack_status_stage()

        # notify the device of the reconfiguration, in case
        # it needs to e.g. set up endpoints accordingly
        self.backend.configured(self.configuration)


    # USB 2.0 specification, section 9.4.4 (p 282 of pdf)
    @standard_request_handler(number=10)
    @to_device
    def handle_get_interface_request(self, req):
        logger.debug(self.name, "received GET_INTERFACE request")

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
