#!/usr/bin/env python3
#
# This file is part of FaceDancer.
#
""" USB Proxy example; forwards all USB transactions and logs them to the console. """

from facedancer          import *
from facedancer          import main

from facedancer.proxy    import USBProxyDevice
from facedancer.filters  import USBProxySetupFilters, USBProxyPrettyPrintFilter

# replace with the proxied device's information
ID_VENDOR=0x09e8
ID_PRODUCT=0x0031


if __name__ == "__main__":
    # create a USB Proxy Device
    proxy = USBProxyDevice(idVendor=ID_VENDOR, idProduct=ID_PRODUCT)

    # add a filter to forward control transfers between the target host and
    # proxied device
    proxy.add_filter(USBProxySetupFilters(proxy, verbose=0))

    # add a filter to log USB transactions to the console
    proxy.add_filter(USBProxyPrettyPrintFilter(verbose=5))

    main(proxy)
