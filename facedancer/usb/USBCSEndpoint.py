# USBEndpoint.py
#
# Contains class definition for USBCSEndpoint.

import struct
from facedancer.usb.USB import DescriptorType, USBDescribable
from facedancer.fuzz.helpers import mutable

class USBCSEndpoint(USBDescribable):
    name = 'CSEndpoint'

    def __init__(self, name, phy, cs_config):
        super(USBCSEndpoint, self).__init__(phy)
        self.name = name
        self.cs_config = cs_config
        self.interface = None
        self.usb_class = None

        self.request_handlers   = {
                 1: self.handle_clear_feature_request
        }

    def handle_clear_feature_request(self, req):
        self.info("received CLEAR_FEATURE request for endpoint", self.number,
                "with value", req.value)
        self.phy.send_on_endpoint(0, b'')

    def set_interface(self, interface):
        self.interface = interface

    # see Table 9-13 of USB 2.0 spec (pdf page 297)
    @mutable('usbcsendpoint_descriptor')
    def get_descriptor(self, usb_type='fullspeed', valid=False):
        descriptor_type = DescriptorType.cs_endpoint
        length = len(self.cs_config) + 2
        response = struct.pack('BB', length & 0xff, descriptor_type) + self.cs_config
        return response