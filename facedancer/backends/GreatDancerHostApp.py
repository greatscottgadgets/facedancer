# GreatDancerHostApp.py
#
# Host support for GreatFET-base devices

import sys
import time
import codecs
import struct

from ..core import *

class GreatDancerHostApp(FacedancerUSBHost):
    """
    Class that represets a GreatFET-based USB host.
    """
    app_name = "GreatDancer Host"


    PORT_STATUS_REG  = 0
    READ_STATUS_REG  = 1
    WRITE_STATUS_REG = 2

    PORT_STATUS_REGISTER_CONNECTED_MASK = (1 << 0)
    PORT_STATUS_REGISTER_ENABLED_MASK = (1 << 2)
    PORT_STATUS_REGISTER_POWERED_MASK = (1 << 12)

    PORT_STATUS_REGISTER_SPEED_SHIFT  = 26
    PORT_STATUS_REGISTER_SPEED_MASK  = 0b11

    PORT_STATUS_REGISTER_LINE_STATE_SHIFT  = 10
    PORT_STATUS_REGISTER_LINE_STATE_MASK   = 0b11

    LINE_STATE_NAMES = {
        0: "SE0",
        1: "J",
        2: "K",
        3: "No device / SE1"
    }

    LINE_STATE_SE0 = 0
    LINE_STATE_J = 1
    LINE_STATE_K = 2
    LINE_STATE_SE1 = 3

    DEVICE_SPEED_LOW = 0
    DEVICE_SPEED_FULL = 1
    DEVICE_SPEED_HIGH = 2
    DEVICE_SPEED_NONE = 3

    STATUS_REG_SPEED_VALUES = {
        0: DEVICE_SPEED_FULL,
        1: DEVICE_SPEED_LOW,
        2: DEVICE_SPEED_HIGH,
        3: DEVICE_SPEED_NONE
    }
    DEVICE_SPEED_NAMES = {
        DEVICE_SPEED_FULL: "Full speed",
        DEVICE_SPEED_LOW: "Low speed",
        DEVICE_SPEED_HIGH: "High speed",
        DEVICE_SPEED_NONE: "Disconnected"
    }

    SPEED_REQUESTS = {
        0: 1,
        1: 0,
        2: 2,
        3: 3
    }

    # Endpoint directions
    DIRECTION_IN  = 0x00
    DIRECTION_OUT = 0x80

    # Endpoint types
    ENDPOINT_TYPE_CONTROL = 0

    # Packet IDs
    PID_SETUP = 2
    PID_OUT = 0
    PID_IN = 1


    @classmethod
    def appropriate_for_environment(cls, backend_name):
        """
        Determines if the current environment seems appropriate
        for using the GreatDancer backend.
        """

        # Check: if we have a backend name other than greatfet,
        # the user is trying to use something else. Abort!
        if backend_name and backend_name != "greatfet":
            return False

        # If we're not explicitly trying to use something else,
        # see if there's a connected GreatFET.
        try:
            import greatfet
            greatfet.GreatFET()
            return True
        except ImportError:
            sys.stderr.write("NOTE: Skipping GreatFET-based devices, as the greatfet python module isn't installed.\n")
            return False
        except:
            return False


    def __init__(self, verbose=0, quirks=[], autoconnect=True, device=None):
        """
        Sets up a GreatFET-based host connection.
        """

        import greatfet

        if device is None:
            device = greatfet.GreatFET()

        # Store our input args.
        # TODO: pull into base class
        self.device = device
        self.verbose = verbose

        # Grab a reference to our protocol definitions.
        self.vendor_requests = greatfet.protocol.vendor_requests

        if autoconnect:
            self.connect()


    def connect(self):
        """
        Sets up our host to talk to the device, including turning on VBUS.
        """
        self.device.comms._vendor_request_out(self.vendor_requests.USBHOST_CONNECT)


    def bus_reset(self, delay=0.500):
        """
        Issues a "bus reset", requesting that the downstream device reset itself.

            delay -- The amount of time, in seconds, to wait before or after the
                reset request. To be compliant, this should be omitted, or set
                to 0.1s.
        """

        # Note: we need to wait a reset delay before and after the bus reset.
        # This allows the host to initialize _and_ then allows the device to settle.
        time.sleep(delay)
        self.device.comms._vendor_request_out(self.vendor_requests.USBHOST_BUS_RESET)
        time.sleep(delay)


    @staticmethod
    def _decode_usb_register(transfer_result):
        """
        Decodes a raw 32-bit register value from a form encoded
        for transit as a USB control request.

        transfer_result: The value returned by the vendor request.
        returns: The raw integer value of the given register.
        """
        status_hex = codecs.encode(transfer_result[::-1], 'hex')
        return int(status_hex, 16)


    def _fetch_status_register(self, register_number):
        """
        Fetches a status register from the GreatDacner, and returns it
        as an integer.
        """
        raw_status = self.device.comms._vendor_request_in(self.vendor_requests.USBHOST_GET_STATUS, index=register_number, length=4)
        return self._decode_usb_register(raw_status)


    def _port_status(self):
        """ Returns the raw state of the port status register. """
        return self._fetch_status_register(self.PORT_STATUS_REG)


    def _get_read_status(self):
        """ Returns the raw state of the read status word. """
        return self._fetch_status_register(self.READ_STATUS_REG)


    def _get_write_status(self):
        """ Returns the raw state of the read status word. """
        return self._fetch_status_register(self.WRITE_STATUS_REG)


    def device_is_connected(self):
        """ Returns true iff a given device is connected.  """
        status = self._port_status()
        return bool(status & self.PORT_STATUS_REGISTER_CONNECTED_MASK)


    def port_is_enabled(self):
        """ Returns true iff the FaceDancer host port's enabled. """
        status = self._port_status()
        return bool(status & self.PORT_STATUS_REGISTER_ENABLED_MASK)


    def port_is_powered(self):
        """ Returns true iff the FaceDancer host port's enabled. """
        status = self._port_status()
        return bool(status & self.PORT_STATUS_REGISTER_POWERED_MASK)


    def current_device_speed(self, as_string=False):
        """ Returns the speed of the connected device

        as_string -- If true, returns the speed as a string for printing; otherwise
            returns a DEVICE_SPEED_* constant.
        """


        port_speed_raw = \
            (self._port_status() >> self.PORT_STATUS_REGISTER_SPEED_SHIFT) & \
            self.PORT_STATUS_REGISTER_SPEED_MASK

        # Translate from a GreatFET format device speed to a FaceDancer one.
        port_speed = self.STATUS_REG_SPEED_VALUES[port_speed_raw]

        if as_string:
            port_speed = self.DEVICE_SPEED_NAMES[port_speed]

        return port_speed


    def current_line_state(self, as_string=False):
        """ Returns the current state of the USB differential pair

        as_string -- If true, returns the speed as a string for printing; otherwise
            returns a LINE_STATE_* constant.
        """

        line_state = \
            (self._port_status() >> self.PORT_STATUS_REGISTER_LINE_STATE_SHIFT) & \
            self.PORT_STATUS_REGISTER_LINE_STATE_MASK

        if as_string:
            line_state = self.LINE_STATE_NAMES[line_state]

        return line_state


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

        if isinstance(endpoint_address_or_object, USBEndpoint):
            endpoint = endpoint_address_or_object

            # Figure out the endpoint address from its direction and number.
            endpoint_address = endpoint.number
            if endpoint.direction == endpoint.direction_in:
                endpoint_address |= self.DIRECTION_IN

            self.set_up_endpoint(endpoint_address, endpoint.transfer_type, endpoint.max_packet_size)
            return

        endpoint_address = endpoint_address_or_object
        endpoint_number = endpoint_address & 0x7f

        if endpoint_number > 15:
            raise ValueError("cannot have an endpoint with a number > 15!")

        # Figure out defaults for any arguments not provided.
        if device_address is None:
            device_address = self.last_device_address
        if endpoint_speed is None:
            endpoint_speed = self.last_device_speed
        if is_control_endpoint is None:
            is_control_endpoint = (endpoint_number == 0)
        if handle_data_toggle is None:
            handle_data_toggle = True if not is_control_endpoint else False

        # Figure out which endpoint schedule to use.
        # FIXME: support more than the asynchronous schedule
        endpoint_schedule = 0

        # TODO: do we translate speed requests, here?

        # Issue the configuration packet.
        packet = struct.pack("<BBBBBHB", endpoint_schedule, device_address, endpoint_address,
                             endpoint_speed, is_control_endpoint, max_packet_size, handle_data_toggle)
        self.device.comms._vendor_request_out(self.vendor_requests.USBHOST_SET_UP_ENDPOINT, data=packet)


    def initialize_control_endpoint(self, device_address=None, device_speed=None, max_packet_size=None):
        """
        Set up the device's control endpoint, so we can use it for e.g. enumeration.
        """

        # If not overridden, apply the specification default maximum packet size.
        # TODO: support high speed devices, here?
        if max_packet_size is None:
            max_packet_size = 8 if device_speed == self.DEVICE_SPEED_LOW else 64

        # Set up both directions on the control endpoint.
        self.set_up_endpoint(0 | self.DIRECTION_OUT, self.ENDPOINT_TYPE_CONTROL, max_packet_size)
        self.set_up_endpoint(0 | self.DIRECTION_IN, self.ENDPOINT_TYPE_CONTROL, max_packet_size)




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

        # Determine the PID token with which to start the request...
        pid_token = self.PID_SETUP if is_setup else self.PID_OUT

        # Issue the actual send itself.
        # TODO: validate length

        self.device.comms._vendor_request_out(self.vendor_requests.USBHOST_SEND_ON_ENDPOINT,
                                       index=endpoint_number, value=(data_packet_pid << 8) | pid_token,
                                       data=data)

        # ... and if we're blocking, also finish it.
        if blocking:
            complete = False
            stalled  = False

            # Wait until we get a complete flag in the status register.
            # XXX: This isn't entirely correct-- it'll clear too much status.
            while not complete:
                status = self._get_write_status()

                stalled  = (status >> endpoint_number) & 0x1
                complete = (status >> (endpoint_number + 16)) & 0x1

                if stalled:
                    raise IOError("Stalled!")



    def read_from_endpoint(self, endpoint_number, expected_read_size=64, data_packet_pid=0):
        """
        Sends a block of data on the provided endpoints.

        endpoint_number -- The endpoint number on which to send.
        expected_read_size -- The expected amount of data to be read.
        data_packet_pid -- The data packet PID to use (1 or 0). 
            Ignored if the endpoint is set to automatically alternate data PIDs.

        raises an IOError on a communications error or stall
        """

        # Start the request...
        self.device.comms._vendor_request_out(self.vendor_requests.USBHOST_START_NONBLOCKING_READ,
                                       index=(data_packet_pid << 8) | endpoint_number, value=expected_read_size)

        # ... and if we're blocking, also finish it.
        complete = False
        stalled  = False

        # Wait until we get a complete flag in the status register.
        # XXX: This isn't entirely correct-- it'll clear too much status.
        while not complete:
            status = self._get_read_status()

            stalled  = (status >> endpoint_number) & 0x1
            complete = (status >> (endpoint_number + 16)) & 0x1

            if stalled:
                raise IOError("Stalled!")

        # Figure out how muhc to read.
        raw_length = self.device.comms._vendor_request_in(self.vendor_requests.USBHOST_GET_NONBLOCKING_LENGTH,
                                                   index=endpoint_number, length=4)
        length = self._decode_usb_register(raw_length)

        if self.verbose > 4:
            print("Supposedly, we've got {} bytes of data to read".format(length))

        # If there's no data available, we don't need to waste time reading anyting.
        if length == 0:
            return b''

        # Otherwise, read the data from the endpoint and return it.
        data = self.device.comms._vendor_request_in(self.vendor_requests.USBHOST_FINISH_NONBLOCKING_READ,
                                             index=endpoint_number, length=length)
        return data.tostring()

