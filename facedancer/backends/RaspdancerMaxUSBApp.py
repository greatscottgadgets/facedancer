#
# Raspdancer
#
# Implementation of the Facedacner API that supports direct access to the MAX324x
# chip via a RasPi's SoC SPI bus. Emulates talking to a Facedancer, but ignores
# the details of the GreatFET protocol.
#

import os
import sys
import time

from ..core import FacedancerApp
from ..backends.MAXUSBApp import MAXUSBApp
from ..USB import *
from ..USBDevice import USBDeviceRequest

class RaspdancerMaxUSBApp(MAXUSBApp):
    app_name = "MAXUSB"
    app_num = 0x00 # Not meaningful for us. TODO: Remove!

    @classmethod
    def appropriate_for_environment(cls, backend_name):
        """
        Determines if the current environment seems appropriate
        for using the GoodFET::MaxUSB backend.
        """

        # Only ever try Raspdancer backends if the backend is set to raspdancer;
        # we don't want to start randomly spamming a system's SPI bus.
        if backend_name != "raspdancer":
            return False

        # If we're not explicitly trying to use something else,
        # see if there's a connected GreatFET.
        try:
            rd = Raspdancer()
            return True
        except ImportError as e:
            sys.stderr.write("NOTE: Skipping Raspdancer devices, as prequisites aren't installed ({}).\n".format(e))
            return False
        except:
            return False


    def __init__(self, device=None, verbose=0, quirks=None):

        if device is None:
            device = Raspdancer(verbose=verbose)

        FacedancerApp.__init__(self, device, verbose)

        self.connected_device = None
        self.enable()

        if verbose > 0:
            rev = self.read_register(self.reg_revision)
            print(self.app_name, "revision", rev)

        # set duplex and negative INT level (from GoodFEDMAXUSB.py)
        self.write_register(self.reg_pin_control,
                self.full_duplex | self.interrupt_level)


    def init_commands(self):
        pass

    def enable(self):
        for i in range(3):
            self.device.set_up_comms()

        if self.verbose > 0:
            print(self.app_name, "enabled")

    def ack_status_stage(self, blocking=False):
        if self.verbose > 5:
            print(self.app_name, "sending ack!")

        self.device.transfer(b'\x01')


    def read_register(self, reg_num, ack=False):
        if self.verbose > 1:
            print(self.app_name, "reading register 0x%02x" % reg_num)

        data = bytearray([ reg_num << 3, 0 ])
        if ack:
            data[0] |= 1

        resp = self.device.transfer(data)

        if self.verbose > 2:
            print(self.app_name, "read register 0x%02x has value 0x%02x" %
                    (reg_num, resp[1]))

        return resp[1]

    def write_register(self, reg_num, value, ack=False):
        if self.verbose > 2:
            print(self.app_name, "writing register 0x%02x with value 0x%02x" %
                    (reg_num, value))

        data = bytearray([ (reg_num << 3) | 2, value ])
        if ack:
            data[0] |= 1

        self.device.transfer(data)


    def read_bytes(self, reg, n):
        if self.verbose > 2:
            print(self.app_name, "reading", n, "bytes from register", reg)

        data = bytes([ (reg << 3) ] + ([0] * n))
        resp = self.device.transfer(data)

        if self.verbose > 3:
            print(self.app_name, "read", len(resp) - 1, "bytes from register", reg)

        return resp[1:]

    def write_bytes(self, reg, data):
        data = bytes([ (reg << 3) | 3 ]) + data

        self.device.transfer(data)

        if self.verbose > 3:
            print(self.app_name, "wrote", len(data) - 1, "bytes to register", reg)


class Raspdancer(object):
    """
        Extended version of the Facedancer class that accepts a direct
        SPI connection to the MAX324x chip, as used by the Raspdancer.
    """

    def __init__(self, verbose=0):
        """
            Initializes our connection to the MAXUSB device.
        """

        import spi
        import RPi.GPIO as GPIO

        self.verbose = verbose
        self.buffered_result = b''
        self.last_verb = -1

        self.spi = spi
        self.gpio = GPIO

        self.gpio.setwarnings(False)
        self.gpio.setmode(self.gpio.BOARD)
        self.reset()

    def reset(self):
        """
            Resets the connected MAXUSB chip.
        """
        self.gpio.setup(15,  self.gpio.OUT)
        self.gpio.output(15, self.gpio.LOW)
        self.gpio.output(15, self.gpio.HIGH)


    def set_up_comms(self):
        """
            Sets up the Raspdancer to communicate with the MAX324x.
        """
        # pin15=GPIO22 is linked to MAX3420 -RST
        self.gpio.setup(15, self.gpio.OUT)
        self.gpio.output(15,self.gpio.LOW)
        self.gpio.output(15,self.gpio.HIGH)

        self.spi.openSPI(speed=26000000)


    def transfer(self, data):
        """
            Emulate the facedancer's write command, which blasts data
            directly over to the SPI bus.
        """
        if isinstance(data,str):
            data = [ord(x) for x in data]

        data = tuple(data)
        data = self.spi.transfer(data)

        return bytearray(data)
