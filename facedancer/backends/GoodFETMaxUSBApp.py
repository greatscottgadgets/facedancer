
import os
import sys
import time

from ..core import FacedancerApp
from ..backends.MAXUSBApp import MAXUSBApp
from ..USB import *
from ..USBDevice import USBDeviceRequest

# TODO: Move all functionality that doesn't explicitly depend on GoodFET
# into MaxUSBApp.
def bytes_as_hex(b, delim=" "):
    return delim.join(["%02x" % x for x in b])

class GoodfetMaxUSBApp(MAXUSBApp):

    app_name = "MAXUSB"
    app_num = 0x40

    reg_ep0_fifo                    = 0x00
    reg_ep1_out_fifo                = 0x01
    reg_ep2_in_fifo                 = 0x02
    reg_ep3_in_fifo                 = 0x03
    reg_setup_data_fifo             = 0x04
    reg_ep0_byte_count              = 0x05
    reg_ep1_out_byte_count          = 0x06
    reg_ep2_in_byte_count           = 0x07
    reg_ep3_in_byte_count           = 0x08
    reg_ep_stalls                   = 0x09
    reg_clr_togs                    = 0x0a
    reg_endpoint_irq                = 0x0b
    reg_endpoint_interrupt_enable   = 0x0c
    reg_usb_irq                     = 0x0d
    reg_usb_interrupt_enable        = 0x0e
    reg_usb_control                 = 0x0f
    reg_cpu_control                 = 0x10
    reg_pin_control                 = 0x11
    reg_revision                    = 0x12
    reg_function_address            = 0x13
    reg_io_pins                     = 0x14

    # bitmask values for reg_endpoint_irq = 0x0b
    is_setup_data_avail             = 0x20     # SUDAVIRQ
    is_in3_buffer_avail             = 0x10     # IN3BAVIRQ
    is_in2_buffer_avail             = 0x08     # IN2BAVIRQ
    is_out1_data_avail              = 0x04     # OUT1DAVIRQ
    is_out0_data_avail              = 0x02     # OUT0DAVIRQ
    is_in0_buffer_avail             = 0x01     # IN0BAVIRQ

    # bitmask values for reg_usb_control = 0x0f
    usb_control_vbgate              = 0x40
    usb_control_connect             = 0x08

    # bitmask values for reg_pin_control = 0x11
    interrupt_level                 = 0x08
    full_duplex                     = 0x10

    @classmethod
    def appropriate_for_environment(cls, backend_name):
        """
        Determines if the current environment seems appropriate
        for using the GoodFET::MaxUSB backend.
        """
        # Check: if we have a backend name other than greatfet,
        # the user is trying to use something else. Abort!
        if backend_name and backend_name != "goodfet":
            return False

        # If we're not explicitly trying to use something else,
        # see if there's a connected GreatFET.
        try:
            gf = GoodFETSerialPort()
            gf.close()
            return True
        except ImportError:
            sys.stderr.write("NOTE: Skipping GoodFET-based devices, as pyserial isn't installed.\n")
            return False
        except:
            return False


    def __init__(self, device=None, verbose=0):

        if device is None:
            serial = GoodFETSerialPort()
            device = Facedancer(serial, verbose=verbose)

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

    def get_version(self):
        return self.read_register(self.reg_revision)

    def ack_status_stage(self):
        if self.verbose > 5:
            print(self.app_name, "sending ack!")

        self.device.writecmd(self.ack_cmd)
        self.device.readcmd()

    def connect(self, usb_device):
        if self.read_register(self.reg_usb_control) & self.usb_control_connect:
            self.write_register(self.reg_usb_control, self.usb_control_vbgate)
            time.sleep(.1)

        self.write_register(self.reg_usb_control, self.usb_control_vbgate |
                self.usb_control_connect)

        self.connected_device = usb_device

        if self.verbose > 0:
            print(self.app_name, "connected device", self.connected_device.name)

    def disconnect(self):
        self.write_register(self.reg_usb_control, self.usb_control_vbgate)

        if self.verbose > 0:
            print(self.app_name, "disconnected device", self.connected_device.name)
        self.connected_device = None

    def clear_irq_bit(self, reg, bit):
        self.write_register(reg, bit)

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

    # HACK: but given the limitations of the MAX chips, it seems necessary
    def send_on_endpoint(self, ep_num, data):
        if ep_num == 0:
            fifo_reg = self.reg_ep0_fifo
            bc_reg = self.reg_ep0_byte_count
        elif ep_num == 2:
            fifo_reg = self.reg_ep2_in_fifo
            bc_reg = self.reg_ep2_in_byte_count
        elif ep_num == 3:
            fifo_reg = self.reg_ep3_in_fifo
            bc_reg = self.reg_ep3_in_byte_count
        else:
            raise ValueError('endpoint ' + str(ep_num) + ' not supported')

        # FIFO buffer is only 64 bytes, must loop
        while len(data) > 64:
            self.write_bytes(fifo_reg, data[:64])
            self.write_register(bc_reg, 64, ack=True)

            data = data[64:]

        self.write_bytes(fifo_reg, data)
        self.write_register(bc_reg, len(data), ack=True)

        if self.verbose > 1:
            print(self.app_name, "wrote", bytes_as_hex(data), "to endpoint",
                    ep_num)

    # HACK: but given the limitations of the MAX chips, it seems necessary
    def read_from_endpoint(self, ep_num):
        if ep_num != 1:
            return b''

        byte_count = self.read_register(self.reg_ep1_out_byte_count)
        if byte_count == 0:
            return b''

        data = self.read_bytes(self.reg_ep1_out_fifo, byte_count)

        if self.verbose > 1:
            print(self.app_name, "read", bytes_as_hex(data), "from endpoint",
                    ep_num)

        return data

    def stall_ep0(self):
        if self.verbose > 0:
            print(self.app_name, "stalling endpoint 0")

        self.write_register(self.reg_ep_stalls, 0x23)

    def service_irqs(self):
        while True:
            irq = self.read_register(self.reg_endpoint_irq)

            if self.verbose > 3:
                print(self.app_name, "read endpoint irq: 0x%02x" % irq)

            if self.verbose > 2:
                if irq & ~ (self.is_in0_buffer_avail \
                        | self.is_in2_buffer_avail | self.is_in3_buffer_avail):
                    print(self.app_name, "notable irq: 0x%02x" % irq)

            if irq & self.is_setup_data_avail:
                self.clear_irq_bit(self.reg_endpoint_irq, self.is_setup_data_avail)

                b = self.read_bytes(self.reg_setup_data_fifo, 8)
                if (irq & self.is_out0_data_avail) and (b[0] & 0x80 == 0x00):
                    data_bytes_len = b[6] + (b[7] << 8)
                    b += self.read_bytes(self.reg_ep0_fifo, data_bytes_len)
                req = USBDeviceRequest(b)
                self.connected_device.handle_request(req)

            if irq & self.is_out1_data_avail:
                data = self.read_from_endpoint(1)
                if data:
                    self.connected_device.handle_data_available(1, data)
                self.clear_irq_bit(self.reg_endpoint_irq, self.is_out1_data_avail)

            if irq & self.is_in2_buffer_avail:
                self.connected_device.handle_buffer_available(2)

            if irq & self.is_in3_buffer_avail:
                self.connected_device.handle_buffer_available(3)




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

    import serial

    port = os.environ.get('GOODFET') or "/dev/ttyUSB0"
    args = dict(port=port, baudrate=115200,
                parity=serial.PARITY_NONE, timeout=2)
    args.update(kwargs)
    return serial.Serial(**args)


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

