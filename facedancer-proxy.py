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
from facedancer.proxy.switch_invertx import SwitchControllerInvertXFilter
from facedancer.proxy.switch_flip_endpoints import SwitchControllerWorkWithFacedancer21Filter
import argparse

def vid_pid(x):
    return int(x, 16)

targets=[
    ["SwitchControllerInvertX", [SwitchControllerInvertXFilter]],
    ["SwitchFlipEndpoint", [SwitchControllerWorkWithFacedancer21Filter,SwitchControllerInvertXFilter]],
    ["Default",[]],
]

def showtypes():
    print("\nSupported types are:")
    for entry in targets:
        print("\t\"%s\"" % (entry[0]))
        
def main():
    parser = argparse.ArgumentParser(description="FaceDancer USB Proxy")
    parser.add_argument('-v', dest='vendorid', metavar='<VendorID>',
                        type=vid_pid, help="Vendor ID of device",
                        required=False)
    parser.add_argument('-p', dest='productid', metavar='<ProductID>',
                        type=vid_pid, help="Product ID of device",
                        required=False)
    parser.add_argument('-verbose', dest='verbose', metavar='<Verbose>',
                        help='Debug level',default='0')
    parser.add_argument('--mode', '-mode',help='USB Proxy Mode',default='Default')
    args = parser.parse_args()
    quirks = []

    found=False
    for entry in targets:
        if args.mode==entry[0]:
            funcs=entry[1]
            found=True
            break

    if not found:
        print("Wrong devicetype given.")
        showtypes()
        exit(0)
        
    # Create a new USBProxy device.
    u = FacedancerUSBApp()
    u.set_log_level(int(args.verbose))

    if args.mode=="SwitchControllerInvertX":
        d = USBProxyDevice(u, idVendor=0x0f0d, idProduct=0x00c1, quirks=quirks)
    elif args.mode=="SwitchFlipEndpoint":
        d = USBProxyDevice(u, idVendor=0x0f0d, idProduct=0x00c1, quirks=quirks)
    else:
        if args.vendorid==None or args.productid==None:
            print("Error: -v and -p are required, or use -mode instead:")
            showtypes()
            exit(0)
        d = USBProxyDevice(u, idVendor=args.vendorid, idProduct=args.productid, quirks=quirks)
    
    for func in funcs:
        d.add_filter(func())
        
    d.add_filter(USBProxySetupFilters(d, verbose=2))
    d.add_filter(USBProxyPrettyPrintFilter(verbose=5))
    d.connect()

    try:
        d.run()
    # SIGINT raises KeyboardInterrupt
    except KeyboardInterrupt:
        d.disconnect()

if __name__ == "__main__":
    main()
