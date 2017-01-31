# Facedancer.py
#
# TODO: Either make sure this is only used for GoodFET based facedancers, or
# clean up the GoodFET-specific part to improve neutrality.
#
# Contains class definitions for Facedancer, FacedancerCommand, FacedancerApp,
# and GoodFETMonitorApp.

import serial
import os

class Facedancer:
    def __init__(self, serialport, verbose=0):
        self.serialport = serialport
        self.verbose = verbose

        self.reset()
        self.monitor_app = GoodFETMonitorApp(self, verbose=self.verbose)
        self.monitor_app.announce_connected()

    def halt(self):
        self.serialport.setRTS(1)
        self.serialport.setDTR(1)

    def reset(self):
        if self.verbose > 1:
            print("Facedancer resetting...")

        self.halt()
        self.serialport.setDTR(0)

        c = self.readcmd()

        if self.verbose > 0:
            print("Facedancer reset")

    def read(self, n):
        """Read raw bytes."""

        b = self.serialport.read(n)

        if self.verbose > 3:
            print("Facedancer received", len(b), "bytes;",
                    self.serialport.inWaiting(), "bytes remaining")

        if self.verbose > 2:
            print("Facedancer Rx:", bytes_as_hex(b))

        return b

    def readcmd(self):
        """Read a single command."""

        b = self.read(4)

        app = b[0]
        verb = b[1]
        n = b[2] + (b[3] << 8)

        if n > 0:
            data = self.read(n)
        else:
            data = b''

        if len(data) != n:
            raise ValueError('Facedancer expected ' + str(n) \
                    + ' bytes but received only ' + str(len(data)))

        cmd = FacedancerCommand(app, verb, data)

        if self.verbose > 1:
            print("Facedancer Rx command:", cmd)

        return cmd

    def write(self, b):
        """Write raw bytes."""

        if self.verbose > 2:
            print("Facedancer Tx:", bytes_as_hex(b))

        self.serialport.write(b)

    def writecmd(self, c):
        """Write a single command."""
        self.write(c.as_bytestring())

        if self.verbose > 1:
            print("Facedancer Tx command:", c)


class FacedancerCommand:
    def __init__(self, app=None, verb=None, data=None):
        self.app = app
        self.verb = verb
        self.data = data

    def __str__(self):
        s = "app 0x%02x, verb 0x%02x, len %d" % (self.app, self.verb,
                len(self.data))

        if len(self.data) > 0:
            s += ", data " + bytes_as_hex(self.data)

        return s

    def long_string(self):
        s = "app: " + str(self.app) + "\n" \
          + "verb: " + str(self.verb) + "\n" \
          + "len: " + str(len(self.data))

        if len(self.data) > 0:
            try:
                s += "\n" + self.data.decode("utf-8")
            except UnicodeDecodeError:
                s += "\n" + bytes_as_hex(self.data)

        return s

    def as_bytestring(self):
        n = len(self.data)

        b = bytearray(n + 4)
        b[0] = self.app
        b[1] = self.verb
        b[2] = n & 0xff
        b[3] = n >> 8
        b[4:] = self.data

        return b


class FacedancerApp:
    app_name = "override this"
    app_num = 0x00

    def __init__(self, device, verbose=0):
        self.device = device
        self.verbose = verbose

        self.init_commands()

        if self.verbose > 0:
            print(self.app_name, "initialized")

    def init_commands(self):
        pass

    def enable(self):
        #for i in range(3):
        #    self.device.writecmd(self.enable_app_cmd)
        #    self.device.readcmd()

        #if self.verbose > 0:
        #    print(self.app_name, "enabled")
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
