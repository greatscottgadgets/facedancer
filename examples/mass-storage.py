#!/usr/bin/env python3
#
# This file is part of FaceDancer.
#

import sys
import logging

from facedancer import main
from facedancer.devices.umass import RawDiskImage
from facedancer.devices.umass import USBMassStorageDevice


# usage instructions
if len(sys.argv)==1:
    print("Usage: mass-storage.py disk.img")
    sys.exit(1)

# get disk image filename and clear arguments
filename = sys.argv[1]
sys.argv = [sys.argv[0]]

# open our disk image
disk_image = RawDiskImage(filename, 512, verbose=3)

# create the device
device = USBMassStorageDevice(disk_image)


async def hello():
    """ Waits for the host to connect, and then says hello. """

    logging.info("Waiting for the host to connect.")
    await device.wait_for_host()
    logging.info("Host connected!")

main(device, hello())


# Creating a disk image for testing:
#
#    dd if=/dev/zero of=disk.img bs=1M count=100
#    mkfs -t ext4 disk.img
#    mount -t auto -o loop disk.img /mnt
