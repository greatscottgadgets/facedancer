#!/usr/bin/env python3
#
# facedancer-usbproxy.py

from facedancer import FacedancerUSBApp
from facedancer.USBConfiguration import USBConfiguration
from facedancer.USBInterface import USBInterface
from facedancer.USBEndpoint import USBEndpoint
from facedancer.USBProxy import USBProxyDevice, USBProxyFilter
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
        data[4] = 0xff - data[4]

        return ep_num, data


def main():

    # Create a new proxy/MITM connection for the Switch Wired Pro Controller.
    u = FacedancerUSBApp(verbose=1)
    d = USBProxyDevice(u, idVendor=0x0f0d, idProduct=0x00c1, verbose=2)

    # Apply the standard filters that make USBProork.
    d.add_filter(USBProxySetupFilters(d, verbose=2))

    d.add_filter(SwitchControllerInvertXFilter())
    d.add_filter(USBProxyPrettyPrintFilter(verbose=5))

    d.connect()

    try:
        d.run()
    # SIGINT raises KeyboardInterrupt
    except KeyboardInterrupt:
        d.disconnect()

if __name__ == "__main__":
    main()
