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

# TODO: Remove this!
from .GoodFETMaxUSBApp import Facedancer, FacedancerCommand


# List all of the verbs supported by the MaxUSB app we're emulating.
READ  = 0x00
WRITE = 0x01
PEEK  = 0x02
POKE  = 0x03
SETUP = 0x10

# The application number for the MAXUSB App.
MAXUSB_APP = 0x40

class RaspdancerMaxUSBApp(MAXUSBApp):
    app_name = "MAXUSB"
    app_num = 0x40

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


    def __init__(self, device=None, verbose=0):

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
        self.read_register_cmd  = FacedancerCommand(self.app_num, 0x00, b'')
        self.write_register_cmd = FacedancerCommand(self.app_num, 0x00, b'')
        self.enable_app_cmd     = FacedancerCommand(self.app_num, 0x10, b'')
        self.ack_cmd            = FacedancerCommand(self.app_num, 0x00, b'\x01')

    def read_register(self, reg_num, ack=False):
        if self.verbose > 1:
            print(self.app_name, "reading register 0x%02x" % reg_num)

        self.read_register_cmd.data = bytearray([ reg_num << 3, 0 ])
        if ack:
            self.read_register_cmd.data[0] |= 1

        self.device.writecmd(self.read_register_cmd)

        resp = self.device.readcmd()

        if self.verbose > 2:
            print(self.app_name, "read register 0x%02x has value 0x%02x" %
                    (reg_num, resp.data[1]))

        return resp.data[1]

    def write_register(self, reg_num, value, ack=False):
        if self.verbose > 2:
            print(self.app_name, "writing register 0x%02x with value 0x%02x" %
                    (reg_num, value))

        self.write_register_cmd.data = bytearray([ (reg_num << 3) | 2, value ])
        if ack:
            self.write_register_cmd.data[0] |= 1

        self.device.writecmd(self.write_register_cmd)
        self.device.readcmd()


    def read_bytes(self, reg, n):
        if self.verbose > 2:
            print(self.app_name, "reading", n, "bytes from register", reg)

        data = bytes([ (reg << 3) ] + ([0] * n))
        cmd = FacedancerCommand(self.app_num, 0x00, data)

        self.device.writecmd(cmd)
        resp = self.device.readcmd()

        if self.verbose > 3:
            print(self.app_name, "read", len(resp.data) - 1, "bytes from register", reg)

        return resp.data[1:]

    def write_bytes(self, reg, data):
        data = bytes([ (reg << 3) | 3 ]) + data
        cmd = FacedancerCommand(self.app_num, 0x00, data)

        self.device.writecmd(cmd)
        self.device.readcmd() # null response

        if self.verbose > 3:
            print(self.app_name, "wrote", len(data) - 1, "bytes to register", reg)


class Raspdancer(Facedancer):
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

    def halt(self):
        """
            Halts communication with the MAXUSB.
        """
        print("HALT: Not yet implemented!")

    def reset(self):
        """
            Resets the connected MAXUSB chip.
        """
        self.gpio.setup(15,  self.gpio.OUT)
        self.gpio.output(15, self.gpio.LOW)
        self.gpio.output(15, self.gpio.HIGH)

    def read(self, n):
        print("READ: Not yet implemented!")

    def write(self, b):
        print("WRITE: Not yet implemented!")

    def readcmd(self):
        """
            Reads the result of a previous GreatFET command.
        """
        result = FacedancerCommand(MAXUSB_APP, self.last_verb, self.buffered_result)

        if self.verbose > 1:
            print("Facedancer Rx command:", result)

        return result

    def writecmd(self, c):
        """
            Executes a given GreatFET command, emualting an issue of the 
            command to the Facedancer's GoodFET.
        """

        handlers = {
            READ: self.issue_read,
            WRITE: self.issue_write,
            SETUP: self.issue_setup,
            PEEK: self.issue_peek,
            POKE: self.issue_poke
        }

        if self.verbose:
            print("Facedancer Tx command:", c)

        # If we have a function that handles the given command, execute it.
        if c.verb in handlers:
            handler = handlers[c.verb]

            self.buffered_result = handler(c.data)
            self.last_verb = c.verb

        # Otherwise, report that we don't support the given verb.
        else:
            print("VERB {}: currently unsupported!".format(c.verb))


    def issue_setup(self, data):
        """
            Sets up the Raspdancer to communicate with the MAX324x.
        """
        # pin15=GPIO22 is linked to MAX3420 -RST
        self.gpio.setup(15, self.gpio.OUT)
        self.gpio.output(15,self.gpio.LOW)
        self.gpio.output(15,self.gpio.HIGH)

        self.spi.openSPI(speed=26000000)

        return b''


    def issue_write(self, data):
        """
            Emulate the facedancer's write command, which blasts data
            directly over to the SPI bus.
        """
        if isinstance(data,str):
            data = [ord(x) for x in data]

        data = tuple(data)
        data = self.spi.transfer(data)

        return bytearray(data)


    def issue_read(self, data):
        """
            Emulate the facedancer's read command, which blasts data
            directly over to the SPI bus.
        """
        return self.issue_write(data)


    def issue_peek(self, data):
        """
            Emulate the facedancer's peek command.
        """

        # Currently, this command does nothing on the MSP430.
        return b''


    def issue_poke(self, data):
        """
            Emulate the facedancer's poke command.
        """

        # Currently, this command does nothing on the MSP430.
        return b''

