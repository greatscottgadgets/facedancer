# USBPrinter.py

# Contains class definitions to implement a simple USB Printer
# such as a thermal receipt printer.
# Ubuntu Linux 18.04 creates /dev/usb/lp1 in response to this.
# echo "Hello" >/dev/usb/lp1

import facedancer

from facedancer.USB import *
from facedancer.USBDevice import *
from facedancer.USBConfiguration import *
from facedancer.USBInterface import *
from facedancer.USBEndpoint import *
from facedancer.USBVendor import *


class USBPrinterClass(USBClass):
    """ USB Printer Class """
    name = "USB Printer class"

    PRINTER_CLASS_NUMBER = 7
    DESCRIPTOR_TYPE_NUMBER = 0

    def __init__(self):
        super().__init__(self.PRINTER_CLASS_NUMBER, None, self.DESCRIPTOR_TYPE_NUMBER)

    def handle_get_device_id(self, req):
        """ Printer class request get device ID """
        self.interface.configuration.device.send_control_message(b'')

    def handle_get_port_status(self, req):
        """
        Printer class request get port status returns 1 byte
        bit 5=1:Paper Empty, 4=1:Selected, 3=1:No Error
        0x18 = Paper not empty, selected, no error
        """
        self.interface.configuration.device.send_control_message(b'\x18')

    def handle_soft_reset(self, req):
        """ Printer class request soft reset """
        self.interface.configuration.device.send_control_message(b'')

    def setup_request_handlers(self):
        self.request_handlers = {
            0 : self.handle_get_device_id,
            1 : self.handle_get_port_status,
            2 : self.handle_soft_reset,
            23: self.handle_soft_reset,
        }


class USBPrinterUniDirInterface(USBInterface):
    """
    Uni Directional Printer Interface
    Direction refers to communication between the printer and the host.
    It does not refer to the movement of the printer head.
    """
    name = "USB Printer Uni Dir interface"

    def __init__(self, verbose=0):
        descriptors = {}

        endpoints = [
            USBEndpoint(
                1,          # endpoint number
                USBEndpoint.direction_out,
                USBEndpoint.transfer_type_bulk,
                USBEndpoint.sync_type_none,
                USBEndpoint.usage_type_data,
                64,         # max packet size
                0,          # polling interval, see USB 2.0 spec Table 9-13
                self.handle_data_available      # handler function
            )
        ]

        iclass = USBPrinterClass()
        USBInterface.__init__(
            self,
            0,          # interface number
            0,          # alternate setting
            iclass,     # interface class: Printer
            1,          # subclass: Printer
            1,          # protocol: uni directional
            0,          # string index
            verbose,
            endpoints,
            descriptors
        )
        self.device_class = iclass
        self.device_class.set_interface(self)

    def handle_data_available(self, data):
        """ Called when data is received from host """
        s = data
        if self.verbose > 0:
            print(self.name, "received string", s)


class USBPrinterBiDirInterface(USBInterface):
    """
    Bi Directional Printer Interface
    Direction refers to communication between the printer and the host.
    It does not refer to the movement of the printer head.
    """
    name = "USB Printer Bi Dir interface"

    def __init__(self, verbose=0):
        descriptors = {}

        endpoints = [
            USBEndpoint(
                1,          # endpoint number
                USBEndpoint.direction_out,
                USBEndpoint.transfer_type_bulk,
                USBEndpoint.sync_type_none,
                USBEndpoint.usage_type_data,
                64,         # max packet size
                0,          # polling interval, see USB 2.0 spec Table 9-13
                self.handle_data_available      # handler function
            ),
            USBEndpoint(
                2,          # endpoint number
                USBEndpoint.direction_in,
                USBEndpoint.transfer_type_bulk,
                USBEndpoint.sync_type_none,
                USBEndpoint.usage_type_data,
                64,         # max packet size
                0,          # polling interval, see USB 2.0 spec Table 9-13
                None        # handler function
            )
        ]

        iclass = USBPrinterClass()
        USBInterface.__init__(
            self,
            0,          # interface number
            1,          # alternate setting
            iclass,     # interface class: Printer
            1,          # subclass: Printer
            2,          # protocol: Bidirectional
            0,          # string index
            verbose,
            endpoints,
            descriptors
        )
        self.device_class = iclass
        self.device_class.set_interface(self)

    def handle_data_available(self, data):
        """ Called when data is received from host """
        s = data
        if self.verbose > 0:
            print(self.name, "received string", s)


class USBPrinterDevice(USBDevice):
    """
    USB Printer device class
    """
    name = "USB Printer device"

    def __init__(self, maxusb_app, interface_options=0, verbose=0):

        if interface_options == 0:
            uni_interface = USBPrinterUniDirInterface(verbose=verbose)
            interfaces = [uni_interface]
        elif interface_options == 1:
            bi_interface = USBPrinterBiDirInterface(verbose=verbose)
            interfaces = [bi_interface]
        elif interface_options == 2:
            uni_interface = USBPrinterUniDirInterface(verbose=verbose)
            bi_interface = USBPrinterBiDirInterface(verbose=verbose)
            interfaces = [uni_interface, bi_interface]
        else:
            uni_interface = USBPrinterUniDirInterface(verbose=verbose)
            interfaces = [uni_interface]

        config = USBConfiguration(
            1,                      # index
            "",                     # string desc
            interfaces,             # interfaces
            0xC0,                   # self powered
            50,                     # max 100 mA
        )

        USBDevice.__init__(
            self,
            maxusb_app,
            0,                      # device class
            0,                      # device subclass
            0,                      # protocol release number
            64,                     # max packet size for endpoint 0
            0x0416,                 # vendor id: Winbond
            0x5011,                 # product id: thermal printer
            0x0001,                 # device revision
            "Printer",              # manufacturer string
            "USB Printer",          # product string
            "",                     # serial number string
            [config],
            verbose=verbose
        )
