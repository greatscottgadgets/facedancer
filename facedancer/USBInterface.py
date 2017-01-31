# USBInterface.py
#
# Contains class definition for USBInterface.

from .USB import *

class USBInterface:
    name = "generic USB interface"

    def __init__(self, interface_number, interface_alternate, interface_class,
            interface_subclass, interface_protocol, interface_string_index,
            verbose=0, endpoints=[], descriptors={}):

        self.number = interface_number
        self.alternate = interface_alternate
        self.iclass = interface_class
        self.subclass = interface_subclass
        self.protocol = interface_protocol
        self.string_index = interface_string_index

        self.endpoints = endpoints
        self.descriptors = descriptors

        self.verbose = verbose

        self.descriptors[USB.desc_type_interface] = self.get_descriptor

        self.request_handlers = {
             6 : self.handle_get_descriptor_request,
            11 : self.handle_set_interface_request
        }

        self.configuration = None

        for e in self.endpoints:
            e.set_interface(self)

        self.device_class = None
        self.device_vendor = None

    def set_configuration(self, config):
        self.configuration = config

    # USB 2.0 specification, section 9.4.3 (p 281 of pdf)
    # HACK: blatant copypasta from USBDevice pains me deeply
    def handle_get_descriptor_request(self, req):
        dtype  = (req.value >> 8) & 0xff
        dindex = req.value & 0xff
        lang   = req.index
        n      = req.length

        response = None

        if self.verbose > 2:
            print(self.name, ("received GET_DESCRIPTOR req %d, index %d, " \
                    + "language 0x%04x, length %d") \
                    % (dtype, dindex, lang, n))

        # TODO: handle KeyError
        response = self.descriptors[dtype]
        if callable(response):
            response = response(dindex)

        if response:
            n = min(n, len(response))
            self.configuration.device.maxusb_app.send_on_endpoint(0, response[:n])

            if self.verbose > 5:
                print(self.name, "sent", n, "bytes in response")

    def handle_set_interface_request(self, req):
        self.configuration.device.maxusb_app.stall_ep0()

    # Table 9-12 of USB 2.0 spec (pdf page 296)
    def get_descriptor(self):

        d = bytearray([
                9,          # length of descriptor in bytes
                4,          # descriptor type 4 == interface
                self.number,
                self.alternate,
                len(self.endpoints),
                self.iclass,
                self.subclass,
                self.protocol,
                self.string_index
        ])

        if self.iclass:
            iclass_desc_num = USB.interface_class_to_descriptor_type(self.iclass)
            if iclass_desc_num:
                desc = self.descriptors[iclass_desc_num]
                if callable(desc):
                    desc = desc(self.iclass)
                d += desc

        for e in self.endpoints:
            d += e.get_descriptor()

        return d

