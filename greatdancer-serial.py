#!/usr/bin/env python3
#
# facedancer-serial.py

import greatfet
import facedancer

from greatfet import *
from facedancer.GreatDancerApp import GreatDancerApp

from USBSerial import *

gf = GreatFET()
u = GreatDancerApp(gf, verbose=6)

d = USBSerialDevice(u, verbose=6)

d.connect()

try:
    d.run()
# SIGINT raises KeyboardInterrupt
except KeyboardInterrupt:
    d.disconnect()
