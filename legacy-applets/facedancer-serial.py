#!/usr/bin/env python3
#
# facedancer-serial.py

from facedancer import FacedancerUSBApp
from USBSerial import *

u = FacedancerUSBApp(verbose=1)
print(u)
d = USBSerialDevice(u, verbose=4)

d.connect()

try:
    d.run()
# SIGINT raises KeyboardInterrupt
except KeyboardInterrupt:
    d.disconnect()
