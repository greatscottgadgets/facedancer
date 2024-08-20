# Facedancer.py
#
# Contains the core methods for working with a facedancer, inclduing methods
# necessary for autodetection.
# and GoodFETMonitorApp.

import os

from .errors import *
from .logging import log

def FacedancerUSBApp(verbose=0, quirks=None):
    """
    Convenience function that automatically creates a FacedancerApp
    based on the BOARD environment variable and some crude internal
    automagic.

    Args:
        verbose : Sets the verbosity level of the relevant app. Increasing
                  this from zero yields progressively more output.
    """
    return FacedancerApp.autodetect(verbose, quirks)


class FacedancerApp:
    app_name = "override this"
    app_num = 0x00

    @classmethod
    def autodetect(cls, verbose=0, quirks=None):
        """
        Convenience function that automatically creates the appropriate
        subclass based on the BOARD environment variable and some crude internal
        automagic.

        Args:
            verbose: Sets the verbosity level of the relevant app. Increasing
                     this from zero yields progressively more output.
        """

        if 'BACKEND' in os.environ:
            backend_name = os.environ['BACKEND'].lower()
        else:
            backend_name = None

        # Iterate over each subclass of FacedancerApp until we find one
        # that seems appropriate.
        subclass = cls._find_appropriate_subclass(backend_name)

        if subclass:
            if verbose > 0:
                log.info("Using {} backend.".format(subclass.app_name))

            return subclass(verbose=verbose, quirks=quirks)
        else:
            log.error("FacedancerApp failed to autodetect any Facedancer devices.")
            log.error("Try specifying a backend with: BACKEND=\"<backend name>\" <your app>")
            raise DeviceNotFoundError("FacedancerApp failed to autodetect any Facedancer devices.")


    @classmethod
    def _find_appropriate_subclass(cls, backend_name):

        # Recursive case: if we have any subnodes, see if they are
        # feed them to this function.
        for subclass in cls.__subclasses__():

            # Check to see if the subnode has any appropriate children.
            appropriate_class = subclass._find_appropriate_subclass(backend_name)

            # If it does, that's our answer!
            if appropriate_class:
                return appropriate_class

        # Base case: check the current node.
        if cls.appropriate_for_environment(backend_name):
            return cls
        else:
            return None


    @classmethod
    def appropriate_for_environment(cls, backend_name=None):
        """
        Returns true if the current class is likely to be the appropriate
        class to connect to a facedancer given the board_name and other
        environmental factors.

        Args:
            backend_name : The name of the backend, as typically retrieved from the BACKEND
                           environment variable, or None to try figuring things out based
                           on other environmental factors.
        """
        return False


    def __init__(self, device, verbose=0):
        self.device = device
        self.verbose = verbose

        self.init_commands()

        if self.verbose > 0:
            log.info(self.app_name, "initialized")

    def init_commands(self):
        pass

    def enable(self):
        pass


def FacedancerUSBHostApp(verbose=0, quirks=None):
    """
    Convenience function that automatically creates a FacedancerApp
    based on the BOARD environment variable and some crude internal
    automagic.

    verbose: Sets the verbosity level of the relevant app. Increasing
        this from zero yields progressively more output.
    """
    return FacedancerUSBHost.autodetect(verbose, quirks)


class FacedancerUSBHost:
    """
    Base class for Facedancer host connections-- extended to provide actual
    connections to each host.
    """

    # TODO: remove this redundancy; these should be somewhere common
    # Endpoint directions
    ENDPOINT_DIRECTION_OUT  = 0x00
    ENDPOINT_DIRECTION_IN = 0x80

    # Endpoint types
    ENDPOINT_TYPE_CONTROL = 0

    # Packet IDs
    PID_SETUP = 2
    PID_OUT = 0
    PID_IN = 1

    # USB Request Types
    REQUEST_TYPE_STANDARD = 0
    REQUEST_TYPE_CLASS = 1
    REQUEST_TYPE_VENDOR = 2
    REQUEST_TYPE_RESERVED = 3

    # USB Request Recipients
    REQUEST_RECIPIENT_DEVICE = 0
    REQUEST_RECIPIENT_INTERFACE = 1
    REQUEST_RECIPIENT_ENDPOINT = 2
    REQUEST_RECIPIENT_OTHER = 3

    # USB Standard Requests
    STANDARD_REQUEST_GET_STATUS = 0
    STANDARD_REQUEST_SET_ADDRESS = 5
    STANDARD_REQUEST_GET_DESCRIPTOR = 6
    STANDARD_REQUEST_SET_CONFIGURATION = 9


    @classmethod
    def autodetect(cls, verbose=0, quirks=None):
        """
        Convenience function that automatically creates the appropriate
        subclass based on the BOARD environment variable and some crude internal
        automagic.

        Args:
            verbose: Sets the verbosity level of the relevant app. Increasing
                     this from zero yields progressively more output.
        """

        # TODO: Filter this out into some kind of autodetecting base class...

        if 'BACKEND' in os.environ:
            backend_name = os.environ['BACKEND'].lower()
        else:
            backend_name = None

        # Iterate over each subclass of FacedancerApp until we find one
        # that seems appropriate.
        subclass = cls._find_appropriate_subclass(backend_name)

        if subclass:
            if verbose > 0:
                log.info("Using {} backend.".format(subclass.app_name))

            return subclass(verbose=verbose, quirks=quirks)
        else:
            log.error("FacedancerUSBHost failed to autodetect any Facedancer devices.")
            log.error("Try specifying a backend with: BACKEND=\"<backend name>\" <your app>")
            raise DeviceNotFoundError("FacedancerUSBHost failed to autodetect any Facedancer devices.")


    @classmethod
    def _find_appropriate_subclass(cls, backend_name):

        # TODO: Filter this out into some kind of autodetecting base class...

        # Recursive case: if we have any subnodes, see if they are
        # feed them to this function.
        for subclass in cls.__subclasses__():

            # Check to see if the subnode has any appropriate children.
            appropriate_class = subclass._find_appropriate_subclass(backend_name)

            # If it does, that's our answer!
            if appropriate_class:
                return appropriate_class

        # Base case: check the current node.
        if cls.appropriate_for_environment(backend_name):
            return cls
        else:
            return None


    @classmethod
    def appropriate_for_environment(cls, backend_name=None):
        """
        Returns true if the current class is likely to be the appropriate
        class to connect to a facedancer given the board_name and other
        environmental factors.

        Args:
            backend_name : The name of the backend, as typically retrieved from the BACKEND
                           environment variable, or None to try figuring things out based
                           on other environmental factors.
        """
        return False


    @classmethod
    def _build_request_type(cls, is_in, req_type, recipient):
        """ Builds the request type field for a USB request.

        Args:
            is_in     : True iff this is a DEVICE-to-HOST request.
            req_type  : The type of request to be used.
            recipient : The context in which this request should be interpreted.

        Returns : a request_type byte
        """

        request_type = 0

        if is_in:
            request_type |= cls.ENDPOINT_DIRECTION_IN

        request_type |= (req_type << 5)
        request_type |= (recipient)

        return request_type


    @classmethod
    def _build_setup_request(cls, is_in, request_type, recipient, request, value, index, length):
        """ Builds a setup request packet from the standard USB request fields. """

        # Fields:
        #       uint8_t request_type;
        #       uint8_t request;
        #       uint16_t value;
        #       uint16_t index;
        #       uint16_t length;

        def split(value):
            value_high  = value >> 8
            value_low = value & 0xFF
            return [value_low, value_high]

        setup_request = [cls._build_request_type(is_in, request_type, recipient), request]
        setup_request.extend(split(value))
        setup_request.extend(split(index))
        setup_request.extend(split(length))
        return setup_request


    def control_request_in(self, request_type, recipient, request, value=0, index=0, length=0):
        """ Performs an IN control request.

        Args:
            request_type : Determines if this is a standard, class, or vendor request. Accepts
                           a REQUEST_TYPE_* constant.
            recipient    : Determines the context in which this command is interpreted. Accepts
                           a REQUEST_RECIPIENT_* constant.
            request      : The request number to be performed.
            value, index : The standard USB request arguments, to be included in the setup
                           packet. Their meaning varies depending on the request.
            length       : The maximum length of data expected in response, or 0 if we don't
                           expect any data back.
        """

        # Create the raw setup request, and send it.
        setup_request = self._build_setup_request(True, request_type, recipient,
                                                  request, value, index, length)

        if self.verbose > 4:
            log.info("Issuing setup packet: {}".format(setup_request))

        self.send_on_endpoint(0, setup_request, True, data_packet_pid=0)

        if self.verbose > 4:
            log.info("Done.")

        # If we have a data stage, issue it:
        if length:

            if self.verbose > 4:
                log.info("Reading response... ")

            data = self.read_from_endpoint(0, length, data_packet_pid=1)

            if self.verbose > 4:
                log.info("Got response: {}".format(data))

            # and give the host an opportunity to ACK by sending a ZLP.
            self.send_on_endpoint(0, [], data_packet_pid=1)
            return data

        else:
            self.read_from_endpoint(0, 0, data_packet_pid=1)


    def control_request_out(self, request_type, recipient, request, value=0, index=0, data=[]):
        """ Performs an OUT control request.

        Args:
            request_type : Determines if this is a standard, class, or vendor request. Accepts
                           a REQUEST_TYPE_* constant.
            recipient    : Determines the context in which this command is interpreted. Accepts
                           a REQUEST_RECIPIENT_* constant.
            request      : The request number to be performed.
            value, index : The standard USB request arguments, to be included in the setup
                           packet. Their meaning varies depending on the request.
            data         : The data to be transmitted with this control request.
        """

        # Create the raw setup request, and send it.
        setup_request = self._build_setup_request(False, request_type, recipient,
                                                  request, value, index, len(data))
        self.send_on_endpoint(0, setup_request, True)

        # If we have a data stage, issue it:
        if data:
            self.send_on_endpoint(0, data)

        # And try to read a ZLP from the host for ACK'ing purposes.
        self.read_from_endpoint(0, 0, data_packet_pid=1)


    def initialize_device(self, apply_configuration=0, assign_address=0):
        """
        Sets up a connection to a directly-attached USB device.

        Args:
            apply_configuration : If non-zero, the configuration with the given index will
                                  be applied to the relevant device.
            assign_address      : If non-zero, the device will be assigned the given address
                                  as part of the enumeration/initialization process.
        """

        # TODO: support timeouts in waiting for a connection

        # Repeatedly attempt to connect to any connected devices.
        while not self.device_is_connected():
            self.bus_reset()

        # Assume the default device addresses, and read the device's speed.
        self.last_device_address = 0
        self.last_device_speed = self.current_device_speed()

        # Set up the device to work.
        if self.verbose > 3:
            log.info("Initializing control endpoint...")
        self.initialize_control_endpoint()

        # Try to ask the device for its maximum packet size on EP0.
        self.last_ep0_max_packet_size = self.read_ep0_max_packet_size()

        # If we've been asked to assign an address,
        # set the device's address, and reinitialize the control endpoint
        # with the updated address.
        if assign_address:
            self.set_address(assign_address)
            self.initialize_control_endpoint(max_packet_size=self.last_ep0_max_packet_size)

        # If we're auto-configuring the device, read the full configuration descriptor,
        # assign the first configuration, and then set up endpoints accordingly
        if apply_configuration:
            self.apply_configuration(apply_configuration)




    def get_descriptor(self, descriptor_type, descriptor_index,
                       language_id, max_length):
        """ Reads up to max_length bytes of a device's descriptors. """

        return self.control_request_in(
                self.REQUEST_TYPE_STANDARD, self.REQUEST_RECIPIENT_DEVICE,
                self.STANDARD_REQUEST_GET_DESCRIPTOR,
                (descriptor_type << 8) | descriptor_index, language_id, max_length)


    def get_device_descriptor(self, max_length=18):
        """ Returns the device's device descriptor. """

        from .device import USBDevice

        raw_descriptor = self.get_descriptor(USBDevice.DESCRIPTOR_TYPE_NUMBER, 0, 0, max_length)
        return USBDevice.from_binary_descriptor(raw_descriptor)


    def read_ep0_max_packet_size(self):
        """ Returns the device's reported maximum packet size on EP0, in a way appropriate for an barely-configured endpoint. """
        device_descriptor = self.get_device_descriptor(max_length=8)
        return device_descriptor.max_packet_size_ep0


    def get_configuration_descriptor(self, index=0, include_subordinates=True):
        """ Returns the device's configuration descriptor.

        Args:
            include_subordinate : if true, subordinate descriptors will also be returned
        """

        from .configuration import USBConfiguration

        # Read just the raw configuration descriptor.
        raw_descriptor = self.get_descriptor(USBConfiguration.DESCRIPTOR_TYPE_NUMBER, index, 0, USBConfiguration.DESCRIPTOR_SIZE_BYTES)

        # If we want to include the subordinate descriptors, read-read the configuration descriptor with an updated length.
        if include_subordinates:

            from struct import unpack

            total_descriptor_lengths = unpack('<H', raw_descriptor[2:4])[0]
            raw_descriptor = self.get_descriptor(USBConfiguration.DESCRIPTOR_TYPE_NUMBER, index, 0, total_descriptor_lengths)

        return USBConfiguration.from_binary_descriptor(raw_descriptor)


    def set_address(self, device_address):
        """ Sets the device's address.

        Note that all endpoints must be set up again after issuing the new address;
        the easiest way to do this is to call apply_configuration().

        Args:
            device_address : the address to apply to the given device
        """
        self.control_request_out(
                self.REQUEST_TYPE_STANDARD, self.REQUEST_RECIPIENT_DEVICE,
                self.STANDARD_REQUEST_SET_ADDRESS, value=device_address)
        self.last_device_address = device_address


    def set_configuration(self, index):
        """ Sets the device's active configuration.

        Note that this does not configure the host for the given configuration.
        Most of the time, you probably want apply_configuration, which does.

        Args:
            index : the index of the configuration to apply
        """
        self.control_request_out(
                self.REQUEST_TYPE_STANDARD, self.REQUEST_RECIPIENT_DEVICE,
                self.STANDARD_REQUEST_SET_CONFIGURATION, value=index)


    def apply_configuration(self, index, set_configuration=True):
        """ Applies a device's configuration. Necessary to use endpoints other
            than the control endpoint.

        Args:
             index             : The configuration index to apply.
             set_configuration : If true, also informs the device of the change.
                 Setting this to false can allow the host to update its view of all
                 endpoints without communicating with the device -- e.g. to update the
                 device's address.
        """

        # Read the full set of descriptors for the given configuration...
        # TODO: don't assume that the indices increment nicely from 1?
        configuration = self.get_configuration_descriptor(index - 1)

        # If we're informing the device of the change, do so.
        if set_configuration:
            self.set_configuration(index)

        # Locally, set up our endpoints to handle device communication.
        for interface in configuration.interfaces.values():
            for endpoint in interface.endpoints.values():
                self.set_up_endpoint(endpoint)

    def handle_events(self):
        self.service_irqs()


class FacedancerBasicScheduler(object):
    """
    Most basic scheduler for Facedancer devices-- and the schedule which is
    created implicitly if no other scheduler is provided. Executes each of its
    tasks in order, over and over.
    """
    do_exit = False

    def __init__(self):
        self.tasks = []
        self.do_exit = False


    def add_task(self, callback):
        """
        Adds a facedancer task to the scheduler, which will be called
        repeatedly according to the internal scheduling algorithm

        callback: The callback to be scheduled.
        """
        self.tasks.append(callback)


    def run(self):
        """
        Run the main scheduler stack.
        """

        self.do_exit = False
        while not self.do_exit:
            for task in self.tasks:
                task()


    def stop(self):
        """
        Stop the scheduler on next loop.
        """
        self.do_exit = True
