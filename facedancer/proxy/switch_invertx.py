#!/usr/bin/env python3
#
# facedancer-usbproxy.py

from facedancer.usb.USBConfiguration import USBConfiguration
from facedancer.usb.USBInterface import USBInterface
from facedancer.usb.USBEndpoint import USBEndpoint
from facedancer.usb.USBProxy import USBProxyDevice, USBProxyFilter
from facedancer.filters.standard import USBProxySetupFilters
from facedancer.filters.logging import USBProxyPrettyPrintFilter


class SwitchControllerInvertXFilter(USBProxyFilter):
    """
    Sample filter that inverts the X axis on a switch controller.
    Demonstrates how dead simple this is. :)
    """

    # Joystick up:   b'\x00\x00\x0f\x80\xff\x80\x80\x00'
    # Joystick down: b'\x00\x00\x0f\x80\x00\x80\x80\x00'

    def filter_in(self, ep_num, data):

        # Invert the X axis...
        try:
            data[3] = 0xff - data[3]
        except:
            pass

        return ep_num, data