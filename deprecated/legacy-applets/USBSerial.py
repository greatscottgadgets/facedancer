# USBFtdi.py

# Contains class definitions to implement a simple USB Serial chip,
# such as the one in the HP48G+ and HP50G graphing calculators.  See
# usb-serial.txt in the Linux documentation for more info.

import facedancer

from facedancer.USB import *
from facedancer.USBDevice import *
from facedancer.USBConfiguration import *
from facedancer.USBInterface import *
from facedancer.USBEndpoint import *
from facedancer.USBVendor import *


class USBSerialVendor(USBVendor):
    name = "USB Serial vendor"

    def setup_request_handlers(self):
        self.request_handlers = {
            # There are no vendor requests!
            #  0 : self.handle_reset_request,
            #  1 : self.handle_modem_ctrl_request,
            #  2 : self.handle_set_flow_ctrl_request,
            #  3 : self.handle_set_baud_rate_request,
            #  4 : self.handle_set_data_request,
            #  5 : self.handle_get_status_request,
            #  6 : self.handle_set_event_char_request,
            #  7 : self.handle_set_error_char_request,
            #  9 : self.handle_set_latency_timer_request,
            # 10 : self.handle_get_latency_timer_request
        }


class USBSerialInterface(USBInterface):
    name = "USB Serial interface"

    def __init__(self, verbose=0):
        descriptors = { }

        endpoints = [
            USBEndpoint(
                1,          # endpoint number
                USBEndpoint.direction_out,
                USBEndpoint.transfer_type_bulk,
                USBEndpoint.sync_type_none,
                USBEndpoint.usage_type_data,
                512,      # max packet size
                0,          # polling interval, see USB 2.0 spec Table 9-13
                self.handle_data_available      # handler function
            ),
            USBEndpoint(
                3,          # endpoint number
                USBEndpoint.direction_in,
                USBEndpoint.transfer_type_bulk,
                USBEndpoint.sync_type_none,
                USBEndpoint.usage_type_data,
                512,      # max packet size
                0,          # polling interval, see USB 2.0 spec Table 9-13
                None        # handler function
            )
        ]

        # TODO: un-hardcode string index (last arg before "verbose")
        USBInterface.__init__(
                self,
                0,          # interface number
                0,          # alternate setting
                USBClass(), # interface class: vendor-specific
                0xff,       # subclass: vendor-specific
                0xff,       # protocol: vendor-specific
                0,          # string index
                verbose,
                endpoints,
                descriptors
        )

    def handle_data_available(self, data):
        s=data;
        if self.verbose > 0:
            print(self.name, "received string", s)

        s = s.replace(b'\r', b'\r\n')
        s = s.upper()

        reply = s

        self.configuration.device.maxusb_app.send_on_endpoint(3, reply)


class USBSerialDevice(USBDevice):
    name = "USB Serial device"

    def __init__(self, maxusb_app, verbose=0):
        interface = USBSerialInterface(verbose=verbose)

        config = USBConfiguration(
                1,                                          # index
                "Serial config",                              # string desc
                [ interface ]                               # interfaces
        )

        USBDevice.__init__(
                self,
                maxusb_app,
                0,                      # device class
                0,                      # device subclass
                0,                      # protocol release number
                64,                     # max packet size for endpoint 0
                0x03f0,                 # vendor id: HP
                0x0121,                 # product id: HP50G
                0x0001,                 # device revision
                "GoodFET",              # manufacturer string
                "HP4X Emulator",        # product string
                "12345",                # serial number string
                [ config ],
                verbose=verbose
        )

        self.device_vendor = USBSerialVendor()
        self.device_vendor.set_device(self)

