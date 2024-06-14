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

    # Type ls.
    await asyncio.sleep(5)
    await device.type_letters('l', 's', '\n')

    # Echo hi.
    await asyncio.sleep(2)
    await device.type_string("echo hi, user\n")

    # Finally, try to pop calc, just for fun.
    logging.info("Bonus: trying to pop calc.")
    await device.type_string('r', modifiers=KeyboardModifiers.MOD_LEFT_META)
    await asyncio.sleep(0.5)
    await device.type_string('calc\n')


    logging.info("Typing complete. Idly handling USB requests.")


main(device, type_letters())
