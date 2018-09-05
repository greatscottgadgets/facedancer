# Facedancer.py
#
# Contains the core methods for working with a facedancer, inclduing methods
# necessary for autodetection.
# and GoodFETMonitorApp.

import os

from .errors import *
from .USBDevice import USBDevice

def FacedancerUSBApp(verbose=0, quirks=None):
    """
    Convenience function that automatically creates a FacedancerApp
    based on the BOARD environment variable and some crude internal
    automagic.

    verbose: Sets the verbosity level of the relevant app. Increasing
        this from zero yields progressively more output.
    """
    return FacedancerApp.autodetect(verbose, quirks)


class FacedancerApp:
    app_name = "override this"
    app_num = 0x00

    @classmethod
    def autodetect(cls, verbose=0, quirks=None):
        """
        Convenience function that automatically creates the apporpriate
        sublass based on the BOARD environment variable and some crude internal
        automagic.

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
                print("Using {} backend.".format(subclass.app_name))

            return subclass(verbose=verbose, quirks=quirks)
        else:
            raise DeviceNotFoundError()


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

        board: The name of the backend, as typically retreived from the BACKEND
            environment variable, or None to try figuring things out based
            on other environmental factors.
        """
        return False


    def __init__(self, device, verbose=0):
        self.device = device
        self.verbose = verbose

        self.init_commands()

        if self.verbose > 0:
            print(self.app_name, "initialized")

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
    Base class for FaceDancer host connections-- extended to provide actual
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
    STANDARD_REQUEST_GET_DESCRIPTOR = 6


    @classmethod
    def autodetect(cls, verbose=0, quirks=None):
        """
        Convenience function that automatically creates the apporpriate
        sublass based on the BOARD environment variable and some crude internal
        automagic.

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
                print("Using {} backend.".format(subclass.app_name))

            return subclass(verbose=verbose, quirks=quirks)
        else:
            raise DeviceNotFoundError()


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

        board: The name of the backend, as typically retreived from the BACKEND
            environment variable, or None to try figuring things out based
            on other environmental factors.
        """
        return False


    @classmethod
    def _build_request_type(cls, is_in, req_type, recipient):
        """
        Builds the request type field for a USB request.
        """

        request_type = 0

        if is_in:
            request_type |= cls.ENDPOINT_DIRECTION_IN

        request_type |= (req_type << 5)
        request_type |= (recipient)

        return request_type


    @classmethod
    def _build_setup_request(cls, is_in, request_type, recipient, request, value, index, length):
        # And send a setup request:
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


    def get_descriptor(self, descriptor_type, descriptor_index,
                       language_id, max_length):
        """ Reads up to max_length bytes of a device's descriptors. """

        return self.control_request_in(
                self.REQUEST_TYPE_STANDARD, self.REQUEST_RECIPIENT_DEVICE,
                self.STANDARD_REQUEST_GET_DESCRIPTOR,
                (descriptor_type << 8) | descriptor_index, language_id, max_length)


    def get_device_descriptor(self, max_length=18):
        """ Returns the device's device descriptor. """
        return self.get_descriptor(USBDevice.DESCRIPTOR_TYPE_NUMBER, 0, 0, max_length)



class FacedancerBasicScheduler(object):
    """
    Most basic scheduler for Facedancer devices-- and the schedule which is
    created implicitly if no other scheduler is provided. Executes each of its
    tasks in order, over and over.
    """

    def __init__(self):
        self.tasks = []


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

        while True:
            for task in self.tasks:
                task()


