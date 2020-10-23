#
# This file is part of FaceDancer.
#

import argparse
import asyncio
import inspect
import logging
import pprint
import sys

from .. import logger


def default_main(device_or_type, *coroutines):
    """ Simple, default main for FaceDancer emulation.

    Parameters:
        device_type -- The USBDevice type to emulate.
    """

    # Instantiate the relevant device, and connect it to our host.
    parser = argparse.ArgumentParser(description=f"Emulation frontend for {device_or_type.name}(s).")
    parser.add_argument('--print-only', action='store_true', help="Prints information about the device without emulating.")
    parser.add_argument('--suggest', action='store_true', help="Prints suggested code additions after device emualtion is complete.")
    parser.add_argument('-v', '--verbose',
        help="Controls verbosity. 0=silent, 3=default, 5=spammy. Default = %(default)s",
        default=3, choices={0, 3, 5}, type=int)
    args = parser.parse_args()

    # Set up our logging output.
    python_loglevel = 100
    verbose = args.verbose
    if verbose == 3:
        python_loglevel = logging.INFO
    elif verbose == 5:
        python_loglevel = logging.DEBUG
    logger.level = python_loglevel

    if inspect.isclass(device_or_type):
        device = device_or_type()
    else:
        device = device_or_type

    if args.print_only:
        pprint.pprint(device)
        sys.exit(0)

    # Run the relevant code, along with any added coroutines.
    device.emulate(*coroutines)

    if args.suggest:
        device.print_suggested_additions()
