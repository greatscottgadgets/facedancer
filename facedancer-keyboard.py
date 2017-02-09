#!/usr/bin/env python3
#
# facedancer-keyboard.py

from facedancer import FacedancerUSBApp
from USBKeyboard import *

u = FacedancerUSBApp(verbose=1)
d = USBKeyboardDevice(u, verbose=5)

d.connect()

try:
    d.run()
# SIGINT raises KeyboardInterrupt
except KeyboardInterrupt:
    d.disconnect()
