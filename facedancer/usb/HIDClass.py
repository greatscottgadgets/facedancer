# HIDClass.py
#

import struct
from .USB import *
from .USBClass import USBClass
from facedancer.fuzz.helpers import mutable

#
# FIXME: This should actually parse HID and subordinate descriptors e.g.
# for easy parsing during MITM attacks. To make things easy for now we just
# provide basic support for replaying these.
#

#
# FIXME: This should also implement any functions descended from USBClass.
#

class Requests(object):
    GET_REPORT = 0x01  # Mandatory
    GET_IDLE = 0x02
    GET_PROTOCOL = 0x03  # Ignored - only for boot device
    SET_REPORT = 0x09
    SET_IDLE = 0x0A
    SET_PROTOCOL = 0x0B  # Ignored - only for boot device

class HIDClass(USBClass):
    """
    Simple class representing a HID device function.
    """

    name = 'USBProControllerClass'

    def setup_local_handlers(self):
        self.local_handlers = {
            Requests.GET_REPORT: self.handle_get_report,
            Requests.GET_IDLE: self.handle_get_idle,
            Requests.SET_REPORT: self.handle_set_report,
            Requests.SET_IDLE: self.handle_set_idle,
        }

    @mutable('hid_get_report_response')
    def handle_get_report(self, req):
        response = b'\xff' * req.length
        return response

    @mutable('hid_get_idle_response')
    def handle_get_idle(self, req):
        return b''

    @mutable('hid_set_report_response')
    def handle_set_report(self, req):
        return b''

    @mutable('hid_set_idle_response')
    def handle_set_idle(self, req):
        return b''

    HID_CLASS_NUMBER            = 3
    DESCRIPTOR_TYPE_NUMBER = DescriptorType.hid

    def __init__(self, phy, raw_descriptor=None):
        super(HIDClass, self).__init__(phy)
        self.raw_descriptor = raw_descriptor
        self.class_number = self.HID_CLASS_NUMBER
        self.class_descriptor_number = self.DESCRIPTOR_TYPE_NUMBER


    @classmethod
    def from_binary_descriptor(cls, phy, data):
        """
        Creates an endpoint object from a description of that endpoint.
        """
        return cls(phy, data)


    def get_descriptor(self):
        return self.raw_descriptor


    def __repr__(self):
        return "<HIDClass descriptor={}>".format(self.raw_descriptor)
