# Facedancer.py
#
# TODO: Either make sure this is only used for GoodFET based facedancers, or
# clean up the GoodFET-specific part to improve neutrality.
#
# Contains class definitions for Facedancer, FacedancerCommand, FacedancerApp,
# and GoodFETMonitorApp.

import serial
import os

from .errors import *

def FacedancerUSBApp(verbose=0):
    """
    Convenience function that automatically creates a FacedancerApp
    based on the BOARD environment variable and some crude internal
    automagic.

    verbose: Sets the verbosity level of the relevant app. Increasing
        this from zero yields progressively more output.
    """
    return FacedancerApp.autodetect(verbose)


class FacedancerApp:
    app_name = "override this"
    app_num = 0x00

    @classmethod
    def autodetect(cls, verbose=0):
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

            return subclass(verbose=verbose)
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


class GoodFETMonitorApp(FacedancerApp):
    app_name = "GoodFET monitor"
    app_num = 0x00

    def read_byte(self, addr):
        d = [ addr & 0xff, addr >> 8 ]
        cmd = FacedancerCommand(self.app_num, 2, d)

        self.device.writecmd(cmd)
        resp = self.device.readcmd()

        return resp.data[0]

    def get_infostring(self):
        return bytes([ self.read_byte(0xff0), self.read_byte(0xff1) ])

    def get_clocking(self):
        return bytes([ self.read_byte(0x57), self.read_byte(0x56) ])

    def print_info(self):
        infostring = self.get_infostring()
        clocking = self.get_clocking()

        print("MCU", bytes_as_hex(infostring, delim=""))
        print("clocked at", bytes_as_hex(clocking, delim=""))

    def list_apps(self):
        cmd = FacedancerCommand(self.app_num, 0x82, b'\x01')
        self.device.writecmd(cmd)

        resp = self.device.readcmd()
        print("build date:", resp.data.decode("utf-8"))

        print("firmware apps:")
        while True:
            resp = self.device.readcmd()
            if len(resp.data) == 0:
                break
            print(resp.data.decode("utf-8"))

    def echo(self, s):
        b = bytes(s, encoding="utf-8")

        cmd = FacedancerCommand(self.app_num, 0x81, b)
        self.device.writecmd(cmd)

        resp = self.device.readcmd()

        return resp.data == b

    def announce_connected(self):
        cmd = FacedancerCommand(self.app_num, 0xb1, b'')
        self.device.writecmd(cmd)
        resp = self.device.readcmd()


def GoodFETSerialPort(**kwargs):
    "Return a Serial port using default values possibly overriden by caller"

    port = os.environ.get('GOODFET') or "/dev/ttyUSB0"
    args = dict(port=port, baudrate=115200,
                parity=serial.PARITY_NONE, timeout=2)
    args.update(kwargs)
    return serial.Serial(**args)
