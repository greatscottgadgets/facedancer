#!/usr/bin/env python3
#
# This file is part of FaceDancer.
#
""" USB 'Rubber Ducky' example; enters some text via the keyboard module. """

import asyncio

from facedancer import main
from facedancer.devices.keyboard import USBKeyboardDevice

device = USBKeyboardDevice()

async def type_letters():
    await asyncio.sleep(10)
    await device.type_letters('l', 's', '<enter>')
    await asyncio.sleep(2)
    await device.type_string("echo hi, user\n")

main(device, type_letters())

