#!/usr/bin/env python3
#
# facedancer-printer.py

from facedancer import FacedancerUSBApp
from USBPrinter import USBPrinterDevice

u = FacedancerUSBApp(verbose=1)
# 0=uni directional, 1=bi directional, 2=both
interface_options = 2
d = USBPrinterDevice(u, interface_options, verbose=6)

d.connect()

try:
    d.run()
# SIGINT raises KeyboardInterrupt
except KeyboardInterrupt:
    d.disconnect()
