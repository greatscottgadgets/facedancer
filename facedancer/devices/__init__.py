#
# This file is part of FaceDancer.
#

import sys
import pprint
import asyncio
import inspect
import logging
import argparse


# Log formatting strings.
LOG_FORMAT_COLOR = "\u001b[37;1m%(levelname)-8s| \u001b[0m\u001b[1m%(module)-15s|\u001b[0m %(message)s"
LOG_FORMAT_PLAIN = "%(levelname)-8s:n%(module)-15s>%(message)s"


def default_main(device_or_type, *coroutines):
    """ Simple, default main for FaceDancer emulation.

    Parameters:
        device_type -- The USBDevice type to emulate.
    """

    # Instantiate the relevant device, and connect it to our host.
    parser = argparse.ArgumentParser(description=f"Emulation frontend for {device_or_type.name}(s).")
    parser.add_argument('--print-only', action='store_true', help="Prints information about the device without emulating.")
    parser.add_argument('--suggest', action='store_true', help="Prints suggested code additions after device emualtion is complete.")
    parser.add_argument('-v', '--verbose', help="Controls verbosity. 0=silent, 3=default, 5=spammy", default=3)
    args = parser.parse_args()

    if sys.stdout.isatty():
        log_format = LOG_FORMAT_COLOR
    else:
        log_format = LOG_FORMAT_PLAIN

    # Set up our logging output.
    python_loglevel = 50 - (int(args.verbose) * 10)
    logging.basicConfig(level=python_loglevel, format=log_format)

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
