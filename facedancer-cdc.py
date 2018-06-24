#!/usr/bin/env python3
#
# facedancer-cdc.py

from facedancer import FacedancerUSBApp
from facedancer.dev.cdc import *

u = FacedancerUSBApp(verbose=1)
print(u)
d = USBCDCDevice(u, verbose=4)

d.connect()

try:
    d.run()
# SIGINT raises KeyboardInterrupt
except KeyboardInterrupt:
    d.disconnect()
