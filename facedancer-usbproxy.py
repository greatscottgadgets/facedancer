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
import argparse



def vid_pid(x):
    return int(x, 16)

def main():
    parser = argparse.ArgumentParser(description="FaceDancer USB Proxy")
    parser.add_argument('-v', dest='vendorid', metavar='<VendorID>',
                        type=vid_pid, help="Vendor ID of device",
                        required=True)
    parser.add_argument('-p', dest='productid', metavar='<ProductID>',
                        type=vid_pid, help="Product ID of device",
                        required=True)
    parser.add_argument('-f', dest='fastsetaddr', action='store_true', 
                        help="Use fast set_addr quirk")
    args = parser.parse_args()
    quirks = []

    if args.fastsetaddr:
        quirks.append('fast_set_addr')

    u = FacedancerUSBApp(verbose=0)
    d = USBProxyDevice(u, idVendor=args.vendorid, idProduct=args.productid, verbose=2, quirks=quirks)

    d.add_filter(USBProxyPrettyPrintFilter(verbose=5))
    d.add_filter(USBProxySetupFilters(d, verbose=0))
    d.connect()

    try:
        d.run()
    # SIGINT raises KeyboardInterrupt
    except KeyboardInterrupt:
        d.disconnect()

if __name__ == "__main__":
    main()
