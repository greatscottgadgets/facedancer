#!/usr/bin/env python3
#
# facedancer-serial.py

from facedancer.app.core import FacedancerUSBApp
from facedancer.dev.qc_edl import *

u = FacedancerUSBApp(verbose=1)
print(u)
d = USBSaharaDevice(u, verbose=4)

d.connect()

try:
    d.run()
# SIGINT raises KeyboardInterrupt
except KeyboardInterrupt:
    d.disconnect()
