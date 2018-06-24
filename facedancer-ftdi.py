#!/usr/bin/env python3
#
# facedancer-ftdi.py

from facedancer import FacedancerUSBApp
from facedancer.dev.ftdi import *

u = FacedancerUSBApp(verbose=1)
d = USBFtdiDevice(u, verbose=6)

d.connect()

try:
    d.run()
# SIGINT raises KeyboardInterrupt
except KeyboardInterrupt:
    d.disconnect()

