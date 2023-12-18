# USBClass.py
#
# Contains class definition for USBClass, intended as a base class (in the OO
# sense) for implementing device classes (in the USB sense), eg, HID devices,
# mass storage devices.

class USBClass:

    name = "generic USB device class"

    # maps bRequest to handler function
    request_handlers = { }

    def __init__(self, class_number=0xff, descriptor=None, class_descriptor_number=0, verbose=0):
        self.interface = None
        self.verbose = verbose
        self.class_number = class_number
        self.descriptor = descriptor
        self.class_descriptor_number = class_descriptor_number

        self.setup_request_handlers()

    def set_interface(self, interface):
        self.interface = interface

    def setup_request_handlers(self):
        """To be overridden for subclasses to modify self.class_request_handlers"""
        pass

    def get_descriptor(self):
        return self.descriptor


    def __repr__(self):
        return "class {}".format(self.class_number)

