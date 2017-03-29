# MAXUSBApp.py
#
# Contains class definition for MAXUSBApp.

import time

from ..core import FacedancerApp
from ..USB import *
from ..USBDevice import USBDeviceRequest

class MAXUSBApp(FacedancerApp):
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

    # TODO: Support a generic MaxUSB interface that doesn't
    # depend on any GoodFET details.

    @staticmethod
    def bytes_as_hex(b, delim=" "):
        return delim.join(["%02x" % x for x in b])


    # HACK: but given the limitations of the MAX chips, it seems necessary
    def send_on_endpoint(self, ep_num, data, blocking=False):
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
            print(self.app_name, "wrote", self.bytes_as_hex(data), "to endpoint",
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
            print(self.app_name, "read", self.bytes_as_hex(data), "from endpoint",
                    ep_num)

        return data

    def stall_ep0(self):
        if self.verbose > 0:
            print(self.app_name, "stalling endpoint 0")

        self.write_register(self.reg_ep_stalls, 0x23)


    def get_version(self):
        return self.read_register(self.reg_revision)


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



    def set_address(self, address):
        """
        Sets the device address of the Facedancer. Usually only used during
        initial configuration.

        address: The address that the Facedance should assume.
        """

        # The MAXUSB chip handles this for us, so we don't need to do anything.
        pass


    def configured(self, configuration):
        """
        Callback that's issued when a USBDevice is configured, e.g. by the
        SET_CONFIGRUATION request. Allows us to apply the new configuration.

        configuration: The configruation applied by the SET_CONFIG request.
        """

        # For the MAXUSB case, we don't need to do anything, though it might
        # be nice to print a message or store the active coniguration for
        # use by the USBDevice, etc. etc.
        pass
