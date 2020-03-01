#
# This file is part of FaceDancer.
#

import sys
import pprint
import asyncio
import argparse
import logging

def default_main(device_type):
    """ Simple, default main for FaceDancer emulation.

    Parameters:
        device_type -- The USBDevice type to emulate.
    """

    # Instantiate the relevant device, and connect it to our host.
    parser = argparse.ArgumentParser(description=f"Emulation frontend for {device_type.name}(s).")
    parser.add_argument('--print-only', action='store_true', help="Prints information about the device without emulating.")
    parser.add_argument('-v', '--verbose', help="Controls verbosity. 0=silent, 3=default, 5=spammy", default=3)
    args = parser.parse_args()

    # Set up our logging output.
    python_loglevel = 50 - (args.verbose * 10)
    logging.basicConfig(level=python_loglevel)

    device = device_type()

    if args.print_only:
        pprint.pprint(device)
        sys.exit(0)

    device.connect()

    # And run it, ensuring we always clean up afterwards.
    try:
        asyncio.run(device.run())
    except KeyboardInterrupt:
        pass
    finally:
        device.disconnect()
