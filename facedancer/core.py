# Facedancer.py
#
# Contains the core methods for working with a facedancer, inclduing methods
# necessary for autodetection.
# and GoodFETMonitorApp.

import os

from .errors import *

def FacedancerUSBApp(verbose=0, quirks=None):
    """
    Convenience function that automatically creates a FacedancerApp
    based on the BOARD environment variable and some crude internal
    automagic.

    verbose: Sets the verbosity level of the relevant app. Increasing
        this from zero yields progressively more output.
    """
    return FacedancerApp.autodetect(verbose, quirks)


class FacedancerApp:
    app_name = "override this"
    app_num = 0x00

    @classmethod
    def autodetect(cls, verbose=0, quirks=None):
        """
        Convenience function that automatically creates the apporpriate
        sublass based on the BOARD environment variable and some crude internal
        automagic.

        verbose: Sets the verbosity level of the relevant app. Increasing
            this from zero yields progressively more output.
        """

        if 'BACKEND' in os.environ:
            backend_name = os.environ['BACKEND'].lower()
        else:
            backend_name = None

        # Iterate over each subclass of FacedancerApp until we find one
        # that seems appropriate.
        subclass = cls._find_appropriate_subclass(backend_name)

        if subclass:
            if verbose > 0:
                print("Using {} backend.".format(subclass.app_name))

            return subclass(verbose=verbose, quirks=quirks)
        else:
            raise DeviceNotFoundError()


    @classmethod
    def _find_appropriate_subclass(cls, backend_name):

        # Recursive case: if we have any subnodes, see if they are
        # feed them to this function.
        for subclass in cls.__subclasses__():

            # Check to see if the subnode has any appropriate children.
            appropriate_class = subclass._find_appropriate_subclass(backend_name)

            # If it does, that's our answer!
            if appropriate_class:
                return appropriate_class

        # Base case: check the current node.
        if cls.appropriate_for_environment(backend_name):
            return cls
        else:
            return None





    @classmethod
    def appropriate_for_environment(cls, backend_name=None):
        """
        Returns true if the current class is likely to be the appropriate
        class to connect to a facedancer given the board_name and other
        environmental factors.

        board: The name of the backend, as typically retreived from the BACKEND
            environment variable, or None to try figuring things out based
            on other environmental factors.
        """
        return False


    def __init__(self, device, verbose=0):
        self.device = device
        self.verbose = verbose

        self.init_commands()

        if self.verbose > 0:
            print(self.app_name, "initialized")

    def init_commands(self):
        pass

    def enable(self):
        pass
