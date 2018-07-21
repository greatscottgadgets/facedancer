#!/usr/bin/env python3
#
# facedancer-usbproxy.py

from facedancer import FacedancerUSBApp
from facedancer.usb.USBConfiguration import USBConfiguration
from facedancer.usb.USBInterface import USBInterface
from facedancer.usb.USBEndpoint import USBEndpoint
from facedancer.usb.USBProxy import USBProxyDevice, USBProxyFilter
from facedancer.filters.standard import USBProxySetupFilters
from facedancer.filters.logging import USBProxyPrettyPrintFilter
import argparse

def vid_pid(x):
    return int(x, 16)

def main():

    # TODO: Accept arguments that specify a list of filters to apply,
    # from the local directory or the filters directory.
    parser = argparse.ArgumentParser(description="FaceDancer USB Proxy")
    parser.add_argument('-v', dest='vendorid', metavar='<VendorID>',
                        type=vid_pid, help="Vendor ID of device",
                        required=True)
    parser.add_argument('-p', dest='productid', metavar='<ProductID>',
                        type=vid_pid, help="Product ID of device",
                        required=True)
    parser.add_argument('-verbose', dest='verbose', metavar='<Verbose>',
                        help='Debug level',default='0')
    args = parser.parse_args()
    quirks = []

    # Create a new USBProxy device.
    u = FacedancerUSBApp()
    u.set_log_level(int(args.verbose))

    d = USBProxyDevice(u, idVendor=args.vendorid, idProduct=args.productid, quirks=quirks)

    # Add our standard filters.
    # TODO: Make the PrettyPrintFilter switchable?
    d.add_filter(USBProxyPrettyPrintFilter(verbose=5))
    d.add_filter(USBProxySetupFilters(d, verbose=2))

    # TODO: Figure these out from the command line!
    d.connect()

    try:
        d.run()
    # SIGINT raises KeyboardInterrupt
    except KeyboardInterrupt:
        d.disconnect()

if __name__ == "__main__":
    main()
