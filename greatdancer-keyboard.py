#!/usr/bin/env python3
#
# facedancer-keyboard.py

import greatfet

from greatfet import *
from facedancer.GreatDancerApp import GreatDancerApp

from USBKeyboard import *

gf = GreatFET()
u = GreatDancerApp(gf, verbose=5)

d = USBKeyboardDevice(u, verbose=5)

d.connect()

try:
    d.run()
# SIGINT raises KeyboardInterrupt
except KeyboardInterrupt:
    d.disconnect()
