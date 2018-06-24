# USBClass.py
#
# Contains class definition for USBClass, intended as a base class (in the OO
# sense) for implementing device classes (in the USB sense), eg, HID devices,
# mass storage devices.

class USBClass:

    name = "generic USB device class"

    Unspecified = 0x00
    Audio = 0x01
    CDC = 0x02
    HID = 0x03
    PID = 0x05
    Image = 0x06
    Printer = 0x07
    MassStorage = 0x08
    Hub = 0x09
    CDCData = 0x0a
    SmartCard = 0x0b
    ContentSecurity = 0x0d
    Video = 0x0e
    PHDC = 0x0f
    AudioVideo = 0x10
    Billboard = 0x11
    DiagnosticDevice = 0xdc
    WirelessController = 0xe0
    Miscellaneous = 0xed
    ApplicationSpecific = 0xfe
    VendorSpecific = 0xff
    
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

