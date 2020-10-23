#!/usr/bin/env python3
#
# This file is part of FaceDancer.
#
from facedancer import logger
from facedancer import main
from facedancer.devices.ftdi import FTDIDevice

device = FTDIDevice()

async def send_hello():
    """ Waits for the host to connect, and then says hello. """

    logger.info("Waiting for the host to connect.")
    await device.wait_for_host()
    logger.info("Host connected!")

    logger.info("Telling the user hello...")
    device.transmit("Hello! Welcome to the FTDI demo.\n")
    device.transmit("Enter any text you'd like, and we'll send it back in UPPERCASE.\n")


def uppercasize(data):
    """ Convert any received data to uppercase. """

    # Convert the data to uppercase...
    uppercase = data.decode('utf-8').upper()

    # ... convert serial line endings to Python line endings...
    uppercase = uppercase.replace('\r', '\n')

    # ... and transmit our response.
    device.transmit(uppercase)


# Override the serial data handler by adding a singleton method on our object.
# This is an easy way to create one-off objects. :)
device.handle_serial_data_received = uppercasize


main(device, send_hello())
