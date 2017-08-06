#!/usr/bin/env python3
#
# facedancer-usbproxy.py

from facedancer import FacedancerUSBApp
from facedancer.USBConfiguration import USBConfiguration
from facedancer.USBInterface import USBInterface
from facedancer.USBEndpoint import USBEndpoint
from USBProxy import USBProxyDevice, USBProxyFilter
import argparse

class USBProxySetupFilters(USBProxyFilter):

    SET_ADDRESS_REQUEST = 5
    SET_CONFIGURATION_REQUEST = 9
    GET_DESCRIPTOR_REQUEST = 6
    RECIPIENT_DEVICE = 0

    def __init__(self, device):
        self.device = device
        self.configuration = None

    def filter_control_in(self, req, data):
        if req.request == self.GET_DESCRIPTOR_REQUEST and \
           req.value == 0x0200 and req.length == 32:
            print(data)
            cfg = data[:data[0]]
            rest = data[data[0]:]
            print("cfg ", cfg)
            print(rest)
            iface = rest[:rest[0]]
            rest = rest[rest[0]:]
            print("iface ", iface)
            x = iface[4]
            eps = []
            while x:
                eps.append(rest[:rest[0]])
                rest = rest[rest[0]:]
                x -= 1
            print(eps)
            endpoints = [
                USBEndpoint(
                    ep[2],
                    (ep[2]&0x80)>>7,
                    ep[3]&0x03,
                    (ep[3]>>2)&0x03,
                    (ep[3]>>4)&0x03,
                    ep[4] | ep[5]<<8,
                    ep[6],
                    None
                )
                for ep in eps
            ]
            interface = USBInterface(
                iface[2],
                iface[3],
                iface[5],
                iface[6],
                iface[7],
                iface[8],
                endpoints = endpoints
            )
            self.configuration = USBConfiguration(
                cfg[5],
                "",
                [interface]
            )
        return req, data

    def filter_control_out(self, req, data):
        # Special case: if this is a SET_ADDRESS request,
        # handle it ourself, and absorb it.
        if req.get_recipient() == self.RECIPIENT_DEVICE and \
           req.request == self.SET_ADDRESS_REQUEST:
            self.device.handle_set_address_request(req)
            return None, None

        if req.get_recipient() == self.RECIPIENT_DEVICE and \
           req.request == self.SET_CONFIGURATION_REQUEST:
            print("Setting config", self.configuration)
            if self.configuration:
                self.device.maxusb_app.configured(self.configuration)
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