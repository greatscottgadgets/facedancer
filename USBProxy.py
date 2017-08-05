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


class USBProxyDevice(USBDevice):
    name = "USB Proxy device"

    def __init__(self, maxusb_app, idVendor, idProduct, verbose=0):
        self.libusb_device = usb.core.find(idVendor=idVendor, idProduct=idProduct)
        # configurations = [
        #     USBProxyConfiguration(libusb_config, verbose)
        #     for libusb_config in libusb_device.configurations()
        # ]

        USBDevice.__init__(
                self,
                maxusb_app,
                0,                      # device class
                0,                      # device subclass
                0,                      # protocol release number
                64,                     # max packet size for endpoint 0
                0,                 # vendor id: HP
                0,                 # product id: HP50G
                0,                 # device revision
                "",              # manufacturer string
                "",        # product string
                "",                # serial number string
                verbose=verbose
        )

    def handle_request(self, req):
        if self.verbose > 3:
            print(self.name, "received request", req)
        if req.get_direction():
            # IN
            try:
                data = self.libusb_device.ctrl_transfer(req.request_type, req.request,
                                             req.value, req.index, req.length)
                print("<", data)
                self.send_control_message(data)
            except:
                self.maxusb_app.stall_ep0()
        else:
            # OUT
            if req.length:
                data = self.maxusb_app.read_from_endpoint(0)
                print(">",data)
            else:
                data = []
            if req.request == 5:
                # Intercept the SET_ADDRESS request
                self.handle_set_address_request(req)
                return
            try:
                self.libusb_device.ctrl_transfer(req.request_type, req.request,
                                             req.value, req.index, data)
            except:
                self.maxusb_app.stall_ep0()
    
    def handle_data_available(self, ep_num, data):
        pass
    
    def handle_buffer_available(self, ep_num):
        pass