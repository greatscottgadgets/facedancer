#!/usr/bin/env python3
#
# facedancer-usbproxy.py

from facedancer import FacedancerUSBApp
from USBProxy import USBProxyDevice, USBProxyFilter
import argparse

class USBProxySetupFilters(USBProxyFilter):

    SET_ADDRESS_REQUEST = 5

    def __init__(self, device):
        self.device = device

    def filter_control_out(self, req, data):
        # Special case: if this is a SET_ADDRESS request,
        # handle it ourself, and absorb it.
        if req.request == self.SET_ADDRESS_REQUEST:
            self.device.handle_set_address_request(req)
            return None, None
        return req, data


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
    filters = USBProxySetupFilters(d)
    d.add_filter(filters)

    d.connect()

    try:
        d.run()
    # SIGINT raises KeyboardInterrupt
    except KeyboardInterrupt:
        d.disconnect()

if __name__ == "__main__":
    main()