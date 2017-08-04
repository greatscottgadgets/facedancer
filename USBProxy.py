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

import usb

class USBProxyVendor(USBVendor):
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


class USBProxyEndpoint(USBEndpoint):
    name = "USB Proxy endpoint"

    def __init__(self, libusb_endpoint, verbose=0):
        USBEndpoint.__init__(
            self,
            libusb_endpoint.bEndpointAddress & 0x0f,
            (libusb_endpoint.bEndpointAddress >> 8) & 0x01,
            libusb_endpoint.bmAttributes & 0x03,
            (libusb_endpoint.bmAttributes >> 2) & 0x03,
            (libusb_endpoint.bmAttributes >> 4) & 0x03,
            libusb_endpoint.wMaxPacketSize,
            libusb_endpoint.bInterval,
            self.handle_data_available      # handler function
        )

    def handle_data_available(self):
        pass


class USBProxyInterface(USBInterface):
    name = "USB Proxy interface"

    def __init__(self, libusb_interface, verbose=0):
        descriptors = { }
        endpoints = [USBProxyEndpoint(ep, verbose)
                     for ep in libusb_interface.endpoints()
                    ]

        # TODO: un-hardcode string index (last arg before "verbose")
        USBInterface.__init__(
                self,
                libusb_interface.bInterfaceNumber,          # interface number
                libusb_interface.bAlternateSetting,          # alternate setting
                libusb_interface.bInterfaceClass,       # interface class: vendor-specific
                libusb_interface.bInterfaceSubClass,       # subclass: vendor-specific
                libusb_interface.bInterfaceProtocol,       # protocol: vendor-specific
                libusb_interface.iInterface,          # string index
                verbose,
                endpoints,
                descriptors
        )


class USBProxyConfiguration(USBConfiguration):
    name = "USB Proxy configuration"

    def __init__(self, libusb_configuration, verbose=0):
        interfaces = [
            USBProxyInterface(interface, verbose)
            for interface in libusb_configuration.interfaces()
            ]

        USBConfiguration.__init__(
            self,
            libusb_configuration.index,
            libusb_configuration.iConfiguration,
            interfaces
        )


class USBProxyDevice(USBDevice):
    name = "USB Proxy device"

    def __init__(self, maxusb_app, idVendor, idProduct, verbose=0):
        libusb_device = usb.core.find(idVendor=idVendor, idProduct=idProduct)
        configurations = [
            USBProxyConfiguration(libusb_config, verbose)
            for libusb_config in libusb_device.configurations()
        ]

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
                configurations,
                verbose=verbose
        )

        self.device_vendor = USBProxyVendor()
        self.device_vendor.set_device(self)

