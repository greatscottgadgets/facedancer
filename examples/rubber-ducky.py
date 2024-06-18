#!/usr/bin/env python3
#
# This file is part of Facedancer.
#
""" USB 'Rubber Ducky' example; enters some text via the keyboard module. """

import asyncio
import logging

from facedancer import main
from facedancer.devices.keyboard     import USBKeyboardDevice
from facedancer.classes.hid.keyboard import KeyboardModifiers

device = USBKeyboardDevice()

async def type_letters():
    logging.info("Beginning message typing demo...")

    await asyncio.sleep(2)
    await device.type_string("echo Hello, Facedancer!\n")

    logging.info("Typing complete. Idly handling USB requests.")


main(device, type_letters())
