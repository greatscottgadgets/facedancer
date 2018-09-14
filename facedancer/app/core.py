# Facedancer.py
#
# Contains the core methods for working with a facedancer, inclduing methods
# necessary for autodetection.
# and GoodFETMonitorApp.

import os
import time
import logging
from .errors import *
from facedancer.usb.USBDevice import USBDevice
from facedancer.usb.USBConfiguration import USBConfiguration
from facedancer.usb.USBEndpoint import USBEndpoint
from facedancer.utils.ulogger import get_logger
from kitty.remote.rpc import RpcClient
from facedancer.fuzz.helpers import StageLogger, set_stage_logger

def FacedancerUSBApp(loglevel=0, quirks=None):
    """
    Convenience function that automatically creates a FacedancerApp
    based on the BOARD environment variable and some crude internal
    automagic.

    loglevel: Sets the verbosity level of the relevant app. Increasing
        this from zero yields progressively more output.
    """
    return FacedancerApp.autodetect(loglevel, quirks)


class FacedancerApp(object):
    app_name = "override this"
    name = "FacedancerApp"
    app_num = 0x00
    log_level = 0
    fuzzer=None
    count = 0
    stage=False
    
    @classmethod
    def set_log_level(self,loglevel):
        self.log_level=loglevel
        return get_logger(loglevel)

    @classmethod
    def get_log_level(self):
        return self.log_level

    def get_mutation(self, stage, data=None):
        if self.fuzzer:
            data = {} if data is None else data
            return self.fuzzer.get_mutation(stage=stage, data=data)
        return None


    @classmethod
    def usb_function_supported(self, reason=None):
        '''
        Callback from a USB device, notifying that the current USB device
        is supported by the host.

        :param reason: reason why we decided it is supported (default: None)
        '''
        self.current_usb_function_supported = True

    @classmethod
    def is_connected(self):
        return self.connected_device is not None

    @classmethod
    def autodetect(cls, loglevel=0, quirks=None):
        """
        Convenience function that automatically creates the apporpriate
        sublass based on the BOARD environment variable and some crude internal
        automagic.

        loglevel: Sets the verbosity level of the relevant app. Increasing
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
            if loglevel > 0:
                print("Using {} backend.".format(subclass.app_name))

            return subclass(loglevel=loglevel, quirks=quirks)
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

    # Fuzzer start
    def get_fuzzer(self,fhost,fport):
        fuzzer = RpcClient(host=fhost,port=int(fport))
        fuzzer.start()
        return fuzzer

    def send_heartbeat(self):
        heartbeat_file = 'heartbeat'
        if os.path.isdir(os.path.dirname(heartbeat_file)):
            with open(heartbeat_file, 'a'):
                os.utime(heartbeat_file, None)

    def check_connection_commands(self):
        '''
        :return: whether performed reconnection
        '''
        if self._should_disconnect():
            self.phy.disconnect()
            self._clear_disconnect_trigger()
            # wait for reconnection request; no point in returning to service_irqs loop while not connected!
            while not self._should_reconnect():
                self._clear_disconnect_trigger()  # be robust to additional disconnect requests
                time.sleep(0.1)
        # now that we received a reconnect request, flow into the handling of it...
        # be robust to reconnection requests, whether received after a disconnect request, or standalone
        # (not sure this is right, might be better to *not* be robust in the face of possible misuse?)
        if self._should_reconnect():
            self.phy.connect(self.dev)
            self._clear_reconnect_trigger()
            return True
        return False

    def _should_reconnect(self):
        if self.fuzzer:
            if os.path.isfile('trigger_reconnect'):
                return True
        return False

    def _clear_reconnect_trigger(self):
        trigger = 'trigger_reconnect'
        if os.path.isfile(trigger):
            os.remove(trigger)

    def _should_disconnect(self):
        if self.fuzzer:
            if os.path.isfile('trigger_disconnect'):
                return True
        return False

    def _clear_disconnect_trigger(self):
        trigger = 'trigger_disconnect'
        if os.path.isfile(trigger):
            os.remove(trigger)

    # Fuzzer end
    
    # Stages start
    
    
    def setstage(self, stage_file_name):
        self.stage=True
        self.start_time = time.time()
        stage_logger = StageLogger(stage_file_name)
        stage_logger.start()
        set_stage_logger(stage_logger)

    
    def should_stop_phy(self):
        if self.fuzzer:
            self.count = (self.count + 1) % 50
            self.check_connection_commands()
            if self.count == 0:
                self.send_heartbeat()
            return False
        elif self.stage:
            stop_phy = False
            passed = int(time.time() - self.start_time)
            if passed > 5:
                self.logger.info('have been waiting long enough (over %d secs.), disconnect' % (passed))
                stop_phy = True
            return stop_phy
        else:
            return False
            
    # Stages end
          
    def __init__(self, device, loglevel=0):
        self.device = device
        self.loglevel = loglevel
        self.logger = logging.getLogger('facedancer')
        self.init_commands()

        if self.loglevel > 0:
            print(self.app_name, "initialized")

    def init_commands(self):
        pass

    def enable(self):
        pass

    def verbose(self, msg, *args, **kwargs):
        self.logger.verbose('[%s] %s' % (self.name, msg), *args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        self.logger.debug('[%s] %s' % (self.name, msg), *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self.logger.info('[%s] %s' % (self.name, msg), *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self.logger.warning('[%s] %s' % (self.name, msg), *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self.logger.error('[%s] %s' % (self.name, msg), *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        self.logger.critical('[%s] %s' % (self.name, msg), *args, **kwargs)

    def always(self, msg, *args, **kwargs):
        self.logger.always('[%s] %s' % (self.name, msg), *args, **kwargs)

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
    STANDARD_REQUEST_SET_ADDRESS = 5
    STANDARD_REQUEST_GET_DESCRIPTOR = 6
    STANDARD_REQUEST_SET_CONFIGURATION = 9


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
        """ Builds the request type field for a USB request.

        is_in -- True iff this is a DEVICE-to-HOST request.
        req_type -- The type of request to be used.
        recipient -- The context in which this request should be interprted.

        returns -- a request_type byte
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

        request_type -- Determines if this is a standard, class, or vendor request. Accepts a REQUEST_TYPE_* constant.
        recipient -- Determines the context in which this command is interpreted. Accepts a REQUEST_RECIPIENT_* constant.
        request -- The request number to be performed.
        value, index -- The standad USB request arguments, to be included in the setup packet. Their meaning varies
            depending on the request.
        length -- The maximum length of data expected in response, or 0 if we don't expect any data back.
        """

        # Create the raw setup request, and send it.
        setup_request = self._build_setup_request(True, request_type, recipient,
                                                  request, value, index, length)

        if self.verbose > 4:
            print("Issuing setup packet: {}".format(setup_request))

        self.send_on_endpoint(0, setup_request, True, data_packet_pid=0)

        if self.verbose > 4:
            print("Done.")

        # If we have a data stage, issue it:
        if length:

            if self.verbose > 4:
                print("Reading response... ")

            data = self.read_from_endpoint(0, length, data_packet_pid=1)

            if self.verbose > 4:
                print("Got response: {}".format(data))

            # and give the host an opportunity to ACK by sending a ZLP.
            self.send_on_endpoint(0, [], data_packet_pid=1)
            return data

        else:
            self.read_from_endpoint(0, 0, data_packet_pid=1)


    def control_request_out(self, request_type, recipient, request, value=0, index=0, data=[]):
        """ Performs an OUT control request.

        request_type -- Determines if this is a standard, class, or vendor request. Accepts a REQUEST_TYPE_* constant.
        recipient -- Determines the context in which this command is interpreted. Accepts a REQUEST_RECIPIENT_* constant.
        request -- The request number to be performed.
        value, index -- The standad USB request arguments, to be included in the setup packet. Their meaning varies
            depending on the request.
        data -- The data to be transmitted with this control request.
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
        Sets up a conenction to a directly-attached USB device.

        apply_configuration -- If non-zero, the configuration with the given 
            index will be applied to the relevant device.
        assign_address -- If non-zero, the device will be assigned the given
            address as part of the enumeration/initialization process.
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
            print("Initializing control endpoint...")
        self.initialize_control_endpoint()

        # If we've been asked to assign an address,
        # set the device's address, and reinitialize the control endpoint
        # with the updated address.
        if assign_address:
            self.set_address(assign_address)
            self.initialize_control_endpoint()

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

        raw_descriptor = self.get_descriptor(USBDevice.DESCRIPTOR_TYPE_NUMBER, 0, 0, max_length)
        return USBDevice.from_binary_descriptor(raw_descriptor)


    def get_configuration_descriptor(self, index=0, include_subordinates=True):
        """ Returns the device's configuration desctriptor.

        include_subordinate -- if true, subordinate descriptors will also be returned
        """

        # Read just the raw configuration descriptor.
        raw_descriptor = self.get_descriptor(USBConfiguration.DESCRIPTOR_TYPE_NUMBER, index, 0, USBConfiguration.DESCRIPTOR_SIZE_BYTES)

        # If we want to include the subordinate descriptors, read-read the configuration descriptor with an updated length.
        if include_subordinates:
            descriptor = USBConfiguration.from_binary_descriptor(raw_descriptor)
            raw_descriptor = self.get_descriptor(USBConfiguration.DESCRIPTOR_TYPE_NUMBER, index, 0, descriptor.total_descriptor_lengths)

        return USBConfiguration.from_binary_descriptor(raw_descriptor)


    def set_address(self, device_address):
        """ Sets the device's address.

        Note that all endpoints must be set up again after issuing the new address;
        the easiest way to do this is to call apply_configuration().

        device_address -- the address to apply to the given device
        """
        self.control_request_out(
                self.REQUEST_TYPE_STANDARD, self.REQUEST_RECIPIENT_DEVICE,
                self.STANDARD_REQUEST_SET_ADDRESS, value=device_address)
        self.last_device_address = device_address


    def set_configuration(self, index):
        """ Sets the device's active configuration.

        Note that this does not configure the host for the given configuration.
        Most of the time, you probably want apply_configuration, which does.

        index -- the index of the configuration to apply
        """
        self.control_request_out(
                self.REQUEST_TYPE_STANDARD, self.REQUEST_RECIPIENT_DEVICE,
                self.STANDARD_REQUEST_SET_CONFIGURATION, value=index)


    def apply_configuration(self, index, set_configuration=True):
        """ Applies a device's configuration. Necessary to use endpoints other
            than the control endpoint.

        index -- The configuration index to apply.
        set_configuration -- If true, also informs the device of the change.
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
        for interface in configuration.interfaces:
            for endpoint in interface.endpoints:
                self.set_up_endpoint(endpoint)


class FacedancerBasicScheduler(object):
    """
    Most basic scheduler for Facedancer devices-- and the schedule which is
    created implicitly if no other scheduler is provided. Executes each of its
    tasks in order, over and over.
    """

    def __init__(self,phy):
        self.tasks = []
        self.phy=phy


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
            if self.phy.should_stop_phy():
                break
