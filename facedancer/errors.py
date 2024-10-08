#
# This file is part of Facedancer.
#

class DeviceNotFoundError(IOError):
    """ Error indicating a device was not found. """
    pass

class EndEmulation(Exception):
    """ When an EndEmulation exception is thrown the emulation will shutdown and exit. """
