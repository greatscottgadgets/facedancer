#!/usr/bin/env python3
#
# facedancer-usbproxy.py

from facedancer import FacedancerUSBApp
from USBProxy import USBProxyDevice
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
    args = parser.parse_args()
    u = FacedancerUSBApp(verbose=4)
    d = USBProxyDevice(u, idVendor=args.vendorid, idProduct=args.productid, verbose=4)

    d.connect()

    try:
        d.run()
    # SIGINT raises KeyboardInterrupt
    except KeyboardInterrupt:
        d.disconnect()

if __name__ == "__main__":
    main()