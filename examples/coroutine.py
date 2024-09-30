#!/usr/bin/env python3
# pylint: disable=unused-wildcard-import, wildcard-import
#
# This file is part of Facedancer.
#

import asyncio
import sys

from facedancer         import *
from facedancer.errors  import EndEmulation
from facedancer.logging import configure_default_logging, log

from minimal import MyDevice


async def my_exit_handler(bindkey: bytes):
    """A custom exit handler that will gracefully shut down the
        emulation when the user presses the given key combination.
    """
    import platform
    if platform.system() == "Windows":
        import msvcrt
        def get_key():
          key = msvcrt.getch()
          # check for, and propagate Control-C
          if key == b'\x03':
              raise KeyboardInterrupt
          return key
    else:
        import termios, tty
        def get_key():
          fd = sys.stdin.fileno()
          restore = termios.tcgetattr(fd)
          try:
              tty.setcbreak(fd)
              key = sys.stdin.read(1)
          finally:
              termios.tcsetattr(fd, termios.TCSADRAIN, restore)
          return str.encode(key)

    while True:
        key = get_key()
        if key == bindkey:
            raise EndEmulation("User quit the emulation.")
        await asyncio.sleep(0)


def my_main_function(device, *coroutines):
    """
    A custom main function for emulating a Facedancer device.
    """

    # Set up our logging output.
    configure_default_logging(level=20)

    # Add a custom exit handler to our coroutines.
    coroutines = (*coroutines, my_exit_handler(b'\x05'))

    # Run the relevant code, along with any added coroutines.
    log.info("Starting emulation, press 'Control-E' to disconnect and exit.")
    device.emulate(*coroutines)


if __name__ == "__main__":
    my_main_function(MyDevice())
