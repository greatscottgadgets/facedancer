#!/usr/bin/env python3
#
# facedancer-keyboard.py

from facedancer import FacedancerUSBHostApp
from USBSwitchTAS import *

u = FacedancerUSBHostApp(verbose=5)
u.initialize_device()
