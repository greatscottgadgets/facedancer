# HIDClass.py
#

import struct
from .USB import *
from .USBClass import USBClass

#
# FIXME: This should actually parse HID and subordinate descriptors e.g.
# for easy parsing during MITM attacks. To make things easy for now we just
# provide basic support for replaying these.
#

#
# FIXME: This should also implement any functions descended from USBClass.
#

class HIDClass(USBDescribable, USBClass):
    """
    Simple class representing a HID device function.
    """

    HID_CLASS_NUMBER            = 3
    DESCRIPTOR_TYPE_NUMBER      = 0x21

    def __init__(self, raw_descriptor):
        self.raw_descriptor = raw_descriptor
        self.class_number = self.HID_CLASS_NUMBER
        self.class_descriptor_number = self.DESCRIPTOR_TYPE_NUMBER


    @classmethod
    def from_binary_descriptor(cls, data):
        """
        Creates an endpoint object from a description of that endpoint.
        """
        return cls(data)


    def get_descriptor(self):
        return self.raw_descriptor


    def __repr__(self):
        return "<HIDClass descriptor={}>".format(self.raw_descriptor)
