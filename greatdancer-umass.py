#!/usr/bin/env python3
#
# facedancer-umass.py
#
# Creating a disk image under linux:
#
#   # fallocate -l 100M disk.img
#   # fdisk disk.img
#   # losetup -f --show disk.img
#   # kpartx -a /dev/loopX
#   # mkfs.XXX /dev/mapper/loopXpY
#   # mount /dev/mapper/loopXpY /mnt/point
#       do stuff on /mnt/point
#   # umount /mnt/point
#   # kpartx -d /dev/loopX
#   # losetup -d /dev/loopX

import sys
if len(sys.argv)==1:
    print("Usage: facedancer-umass.py disk.img");
    sys.exit(1);

from serial import Serial, PARITY_NONE

import greatfet

from greatfet import *
from facedancer.GreatDancerApp import GreatDancerApp

from USBMassStorage import *

gf = GreatFET()
u = GreatDancerApp(gf, verbose=6)
d = USBMassStorageDevice(u, sys.argv[1], verbose=3)

d.connect()

try:
    d.run()
except KeyboardInterrupt:
    d.disconnect()
