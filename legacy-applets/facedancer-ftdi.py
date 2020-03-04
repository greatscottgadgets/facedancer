#!/usr/bin/env python3
#
# facedancer-ftdi.py

from facedancer import FacedancerUSBApp
from USBFtdi import *

u = FacedancerUSBApp(verbose=1)
d = USBFtdiDevice(u, verbose=6)

d.connect()

try:
    d.run()
# SIGINT raises KeyboardInterrupt
except KeyboardInterrupt:
    d.disconnect()

