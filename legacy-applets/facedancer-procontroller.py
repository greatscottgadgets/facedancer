#!/usr/bin/env python3
#
# facedancer-procontroller.py
#
# Custom SPI flash can be provided as a parameter to SPIFlash() - should be
# 512kb in size. Otherwise by default all reads will be 0xff

from facedancer import FacedancerUSBApp
from USBProController import *
from SPIFlash import SPIFlash

u = FacedancerUSBApp(verbose=3)
d = USBProControllerDevice(u, spi_flash=SPIFlash(), verbose=3)

d.connect()

try:
    d.run()
# SIGINT raises KeyboardInterrupt
except KeyboardInterrupt:
    d.disconnect()
