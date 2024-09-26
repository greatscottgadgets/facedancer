#
# This file is part of Facedancer.
#

import sys
import pprint
import asyncio
import inspect
import argparse

from ..errors  import EndEmulation
from ..logging import configure_default_logging, log

def default_main(device_or_type, *coroutines):
    """ Simple, default main for Facedancer emulation.

    Parameters:
        device_type -- The USBDevice type to emulate.
    """

    # Instantiate the relevant device, and connect it to our host.
    parser = argparse.ArgumentParser(description=f"Emulation frontend for {device_or_type.name}(s).")
    parser.add_argument('--print-only', action='store_true', help="Prints information about the device without emulating.")
    parser.add_argument('--suggest', action='store_true', help="Prints suggested code additions after device emualtion is complete.")
    parser.add_argument('-v', '--verbose', help="Controls verbosity. 0=silent, 3=default, 5=spammy", default=3)
    args = parser.parse_args()

    # Set up our logging output.
    python_loglevel = 50 - (int(args.verbose) * 10)
    configure_default_logging(level=python_loglevel)

    if inspect.isclass(device_or_type):
        device = device_or_type()
    else:
        device = device_or_type

    if args.print_only:
        pprint.pprint(device)
        sys.exit(0)

    # Run the relevant code, along with any added coroutines.
    log.info("Starting emulation, press 'Control-C' to disconnect and exit.")
    try:
        device.emulate(*coroutines)
    except KeyboardInterrupt:
        pass
    finally:
        if args.suggest:
            device.print_suggested_additions()
