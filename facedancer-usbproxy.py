#!/usr/bin/env python3
#
# facedancer-serial.py

from facedancer import FacedancerUSBApp
from USBProxy import *

u = FacedancerUSBApp(verbose=4)
print(u)
d = USBProxyDevice(u, idVendor=0x1d50, idProduct=0x6002, verbose=4)

d.connect()

try:
    d.run()
# SIGINT raises KeyboardInterrupt
except KeyboardInterrupt:
    d.disconnect()
