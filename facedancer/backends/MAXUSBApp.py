# MAXUSBApp.py
#
# Contains class definition for MAXUSBApp.

import time

from ..core import FacedancerApp
from ..USB import *
from ..USBDevice import USBDeviceRequest

class MAXUSBApp(FacedancerApp):

    # TODO: Support a generic MaxUSB interface that doesn't
    # depend on any GoodFET details.

    def enable(self):
        for i in range(3):
            self.device.writecmd(self.enable_app_cmd)
            self.device.readcmd()

        if self.verbose > 0:
            print(self.app_name, "enabled")


    def set_address(self, address):
        """
        Sets the device address of the Facedancer. Usually only used during
        initial configuration.

        address: The address that the Facedance should assume.
        """

        # The MAXUSB chip handles this for us, so we don't need to do anything.
        pass


    def configured(self, configuration):
        """
        Callback that's issued when a USBDevice is configured, e.g. by the
        SET_CONFIGRUATION request. Allows us to apply the new configuration.

        configuration: The configruation applied by the SET_CONFIG request.
        """

        # For the MAXUSB case, we don't need to do anything, though it might
        # be nice to print a message or store the active coniguration for
        # use by the USBDevice, etc. etc.
        pass
