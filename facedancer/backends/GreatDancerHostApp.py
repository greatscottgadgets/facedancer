# GreatDancerHostApp.py
#
# Host support for GreatFET-base devices

import time
import codecs

from ..core import *

class GreatDancerHostApp(FacedancerUSBHost):
    """
    Class that represets a GreatFET-based USB host.
    """
    app_name = "GreatDancer Host"


    PORT_STATUS_REG  = 0
    READ_STATUS_REG  = 1
    WRITE_STATUS_REG = 2


    LINE_STATE_NAMES = {
        0: "SE0",
        1: "J",
        2: "K",
        3: "No device / SE1"
    }

    SPEED_NAMES = {
        0: "Full speed",
        1: "Low speed",
        2: "High speed",
        3: "Disconnected"
    }

    SPEED_REQUESTS = {
        0: 1,
        1: 0,
        2: 2,
        3: 3
    }


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
            gf = greatfet.GreatFET()
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
        self.device.vendor_request_out(self.vendor_requests.USBHOST_CONNECT)


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
        self.device.vendor_request_out(self.vendor_requests.USBHOST_BUS_RESET)
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
        raw_status = self.device.vendor_request_in(self.vendor_requests.USBHOST_GET_STATUS, index=register_number, length=4)
        return self._decode_usb_register(raw_status)


    def device_is_connected(self):
        """
            Returns true iff a given device is connected.
        """

        # Read the status of the USB port, which in turn gives us information 
        # about the connected device.
        status = self._fetch_status_register(self.PORT_STATUS_REG)

        port_speed  = self.SPEED_NAMES[status >> 26 & 0b11]
        line_status = self.LINE_STATE_NAMES[status >> 10 & 0b11]

        if self.verbose > 3:
            print("Device is: {}".format("Connected" if (status & 0x1) else "Disconnected"))
            print("Device speed: {}".format(port_speed))
            print("Port is: {}".format("Enabled" if (status & (1 << 2)) else "Disabled"))
            print("Port power is: {}".format("On" if (status & (1 << 12)) else "Off"))
            print("Line states: {}".format(line_status))
            print("Full status is: {}".format(bin(status)))

        return True if (status & 0x1) else False


    def _initialize_control_endpoint(self, device_address):
        """
        Set up the device's control endpoint, so we can use it for e.g. enumeration.
        """



    def initialize_device(self):
        """
        Sets up a conenction to a directly-attached USB device.

        reset -- true if we should issue a host reset as part of the initialization process
        returns -- true iff we've detected a connected device
        """

        # Repeatedly attempt to connect to any connected devices.
        while not self.device_is_connected():
            self.bus_reset()

