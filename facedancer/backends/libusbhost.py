# LibUSBHostApp.py
#
# Host support for accessing libusb with a FaceDancer-like syntax.

import sys
import time
import codecs
import struct

import usb

from ..core import *

class LibUSBHostApp(FacedancerUSBHost):
    """
    Class that represets a libusb-based USB host.
    """
    app_name = "LibUSB Host"

    @classmethod
    def appropriate_for_environment(cls, backend_name):
        """
        Determines if the current environment seems appropriate
        for using the libusb backend.
        """

        # For this to work, we need to somehow select a single port.
        # The best way to do this is with BUS and PORT, so allow the user
        # to select those using the environment.
        # TODO: accept these via quirks?
        if os.environ.get('LIBUSB_BUS') and os.environ.get('LIBUSB_PORT'):
            return True

        # As a stand-in, allow use if the user specifies a device's address.
        if os.environ.get('LIBUSB_ADDRESS'):
            return True

        # Never automaticaly instantiate the libusb backend,
        # as it's not a full implementation and requires host-OS oddities.
        return False


    def __init__(self, verbose=0, quirks=[], index=0, **kwargs):
        """
        Creates a new libusb backend for communicating with a target device.
        """

        self.verbose = verbose
    
        # If we have a specified bus/port, accept them.
        # TODO: accept these via quirks?
        desired_bus = os.environ.get('LIBUSB_BUS')
        desired_port = os.environ.get('LIBUSB_PORT')
        if desired_bus and desired_port:
            kwargs['bus'] = int(desired_bus)
            kwargs['port_number'] = int(desired_port)

        # If the user's searching by address, use that.
        # TODO: accept these via quirks?
        desired_address = os.environ.get('LIBUSB_ADDRESS')
        if desired_address:
            kwargs['address'] = int(desired_address)

        # Open a connection to the target device...
        usb_devices = list(usb.core.find(find_all=True, **kwargs))
        if len(usb_devices) <= index:
            raise DeviceNotFoundError("Could not find a device to connect to via libusb!")
        self.device = usb_devices[index]

        # Detach any existing drivers, where possible.
        try:
            index = self.device.get_active_configuration().index
            self.device.detach_kernel_driver(index)
        except:
            # FIXME: note this here, with a warning?
            pass


    def connect(self):
        """
        Sets up our host to talk to the device, including turning on VBUS.
        """
        pass


    def bus_reset(self, delay=0):
        """
        Issues a "bus reset", requesting that the downstream device reset itself.

            delay -- The amount of time, in seconds, to wait before or after the
                reset request. To be compliant, this should be omitted, or set
                to 0.1s.
        """

        # Note: we need to wait a reset delay before and after the bus reset.
        # This allows the host to initialize _and_ then allows the device to settle.
        time.sleep(delay)
        self.device.reset()
        time.sleep(delay)


    def current_device_speed(self, as_string=False):
        """ Returns the speed of the connected device

        as_string -- If true, returns the speed as a string for printing; otherwise
            returns a DEVICE_SPEED_* constant.
        """
        return self.device.speed


    def current_line_state(self, as_string=False):
        """ Returns the current state of the USB differential pair

        as_string -- If true, returns the speed as a string for printing; otherwise
            returns a LINE_STATE_* constant.
        """
        return None


    def device_is_connected(self):
        """ Returns true iff a given device is connected.  """
        return True


    def port_is_enabled(self):
        """ Returns true iff a given device is connected.  """
        return True


    def port_is_powered(self):
        """ Returns true iff a given device is connected.  """
        return True


    def set_up_endpoint(self, endpoint_address_or_object, endpoint_type=None, max_packet_size=None,
                        device_address=None, endpoint_speed=None, handle_data_toggle=None,
                        is_control_endpoint=None):
        """
        Sets up an endpoint for use. Can be used to initialize an endpoint or to update
        its parameters. Two forms exist:

        endpoint_object -- a USBEndpoint object with the parameters to be populated

        or

        endpoint_address -- the address of the endpoint to be setup; including the direction bit
        endpoint_type -- one of the ENDPOINT_TYPE constants that specifies the transfer mode on
            the endpoint_address
        max_packet_size -- the maximum packet size to be communicated on the given endpoint

        device_address -- the address of the device to be communicated with; if not provided,
            the last address will be used
        endpoint_speed -- the speed of the packets to be communicated on the endpoint; should be a
            DEVICE_SPEED_* constant; if not provided, the last device's speed will be used
        handle_data_toggle -- true iff the hardware should automatically handle selection of data
            packet PIDs
        is_control_endpoint -- true iff the given packet is a for a control endpoint

        TODO: eventually support hubs / more than one device?
        """
        pass


    def initialize_control_endpoint(self, device_address=None, device_speed=None, max_packet_size=None):
        """
        Set up the device's control endpoint, so we can use it for e.g. enumeration.
        """
        pass


    def send_on_endpoint(self, endpoint_number, data, is_setup=False,
                         blocking=True, data_packet_pid=0):
        """
        Sends a block of data on the provided endpoints.

        endpoint_number -- The endpoint number on which to send.
        data -- The data to be transmitted.
        is_setup -- True iff this transfer should begin with a SETUP token.
        blocking -- True iff this transaction should wait for the transaction to complete.
        data_packet_pid -- The data packet PID to use (1 or 0). Ignored if the endpoint is set to automatically
                alternate data PIDs.

        raises an IOError on a communications error or stall
        """
        self.device.write(endpoint_number, data)


    def read_from_endpoint(self, endpoint_number, expected_read_size=64, data_packet_pid=0):
        """
        Sends a block of data on the provided endpoints.

        endpoint_number -- The endpoint number on which to send.
        expected_read_size -- The expected amount of data to be read.
        data_packet_pid -- The data packet PID to use (1 or 0). 
            Ignored if the endpoint is set to automatically alternate data PIDs.

        raises an IOError on a communications error or stall
        """
        data = self.device.read(endpoint_number, expected_read_size)
        return data.tostring()


    def control_request_in(self, request_type, recipient, request, value=0, index=0, length=0):
        """ Performs an IN control request.

        request_type -- Determines if this is a standard, class, or vendor request. Accepts a REQUEST_TYPE_* constant.
        recipient -- Determines the context in which this command is interpreted. Accepts a REQUEST_RECIPIENT_* constant.
        request -- The request number to be performed.
        value, index -- The standad USB request arguments, to be included in the setup packet. Their meaning varies
            depending on the request.
        length -- The maximum length of data expected in response, or 0 if we don't expect any data back.
        """

        request_type = self._build_request_type(True, request_type, recipient)
        data = self.device.ctrl_transfer(request_type, request,
                                         value, index, length)
        return data.tostring()


    def control_request_out(self, request_type, recipient, request, value=0, index=0, data=[]):
        """ Performs an OUT control request.

        request_type -- Determines if this is a standard, class, or vendor request. Accepts a REQUEST_TYPE_* constant.
        recipient -- Determines the context in which this command is interpreted. Accepts a REQUEST_RECIPIENT_* constant.
        request -- The request number to be performed.
        value, index -- The standad USB request arguments, to be included in the setup packet. Their meaning varies
            depending on the request.
        data -- The data to be transmitted with this control request.
        """

        request_type = self._build_request_type(True, request_type, recipient)
        self.device.ctrl_transfer(request_type, request,
                                         value, index, data)
