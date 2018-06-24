#!/usr/bin/env python3
#
# facedancer-cdc_acm.py

from facedancer import FacedancerUSBApp
from facedancer.dev.cdc_acm import *

u = FacedancerUSBApp(verbose=1)
print(u)
d = USBCdcAcmDevice(u, verbose=4)

d.connect()

try:
    d.run()
# SIGINT raises KeyboardInterrupt
except KeyboardInterrupt:
    d.disconnect()
