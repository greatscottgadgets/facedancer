
import logging

# Alias objects to make them easier to import.
from .core import FacedancerUSBApp, FacedancerUSBHostApp, FacedancerBasicScheduler
from .backends import *
from .USBProxy import USBProxyFilter, USBProxyDevice

from .devices import default_main as main

# Set up our extra log levels.
logging.addLevelName(5, 'TRACE')
LOGLEVEL_TRACE = 5
