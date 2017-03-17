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

from serial import Serial, PARITY_NONE

from facedancer import FacedancerUSBApp
from USBMassStorage import *

class DiskImage:
    def __init__(self, filename, block_size):
        self.filename = filename
        self.block_size = block_size

        statinfo = os.stat(self.filename)
        self.size = statinfo.st_size

        self.file = open(self.filename, 'r+b')
        self.image = mmap(self.file.fileno(), 0)

    def close(self):
        self.image.flush()
        self.image.close()

    def get_sector_count(self):
        return int(self.size / self.block_size) - 1

    def get_sector_data(self, address):
        block_start = address * self.block_size
        block_end   = (address + 1) * self.block_size   # slices are NON-inclusive

        return self.image[block_start:block_end]

    def put_sector_data(self, address, data):
        block_start = address * self.block_size
        block_end   = (address + 1) * self.block_size   # slices are NON-inclusive

        self.image[block_start:block_end] = data[:self.block_size]
        self.image.flush()


import sys
if len(sys.argv)==1:
    print("Usage: facedancer-umass.py disk.img");
    sys.exit(1);

i = DiskImage(sys.argv[1], 512)
u = FacedancerUSBApp(verbose=1)
d = USBMassStorageDevice(u, i, verbose=3)

d.connect()

try:
    d.run()
except KeyboardInterrupt:
    d.disconnect()
