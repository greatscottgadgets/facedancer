# USBInterface.py
#
# Contains class definition for USBInterface.

import struct
from .USB import *
from .USBClass import USBClass

class USBInterface(USBDescribable):
    DESCRIPTOR_TYPE_NUMBER = 0x4

    name = "generic USB interface"

    def __init__(self, interface_number, interface_alternate, interface_class,
            interface_subclass, interface_protocol, interface_string_index,
            verbose=0, endpoints=None, descriptors=None):

        self.number = interface_number
        self.alternate = interface_alternate

        # Legacy support: if interface_class is an integer, rather than a
        # USBClass object, create a wrapper object for it.
        if isinstance(interface_class, int):
            self.iclass = self._handle_legacy_interface_class(interface_class, descriptors)
        else:
            self.iclass = interface_class

        self.subclass = interface_subclass
        self.protocol = interface_protocol
        self.string_index = interface_string_index

        self.endpoints = []
        self.descriptors = descriptors if descriptors else {}

        self.verbose = verbose

        self.descriptors[USB.desc_type_interface] = self.get_descriptor

        if self.iclass and self.iclass.class_descriptor_number:
            descriptor = self.iclass.get_descriptor()

            if descriptor:
                self.descriptors[self.iclass.class_descriptor_number] = descriptor

        self.request_handlers = {
             6 : self.handle_get_descriptor_request,
            11 : self.handle_set_interface_request
        }

        self.configuration = None

        if endpoints:
            for endpoint in endpoints:
                self.add_endpoint(endpoint)

        self.device_class = None
        self.device_vendor = None


    def _handle_legacy_interface_class(self, interface_class, descriptors):
        """
        Constructs a USBClass object from a legacy informtion set.
        """

        iclass_desc_num = USB.interface_class_to_descriptor_type(interface_class)

        if iclass_desc_num and descriptors:
            descriptor = descriptors[iclass_desc_num]
        else:
            descriptor = None

        return USBClass(interface_class, descriptor, iclass_desc_num)


    @classmethod
    def from_binary_descriptor(cls, data):
        """
            Generates an interface object from a descriptor.
        """
        interface_number, alternate_setting, num_endpoints, interface_class, \
                interface_subclass, interface_protocol, interface_string_index \
                = struct.unpack("xxBBBBBBB", data)
        return cls(interface_number, alternate_setting, interface_class,
                   interface_subclass, interface_protocol, interface_string_index)



    def __repr__(self):
        endpoints = [endpoint.number for endpoint in self.endpoints]

        return "<USBInterface number={} alternate={} class={} subclass={} protocol={} string_index={} endpoints={}>".format(
                self.number, self.alternate, self.iclass, self.subclass, self.protocol, self.string_index, endpoints
        )


    def add_endpoint(self, endpoint):
        """
        Adds an endpoint the interface.
        """
        self.endpoints.append(endpoint)
        endpoint.set_interface(self)


    def set_class(self, iclass):
        """
        Sets the associated USBClass object for this Interface.
        """
        self.iclass = iclass

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
            print(self.name, ("received GET_DESCRIPTOR at interface req %d, index %d, " \
                    + "language 0x%04x, length %d") \
                    % (dtype, dindex, lang, n))

        # TODO: handle KeyError
        try:
            response = self.descriptors[dtype]
        except KeyError:
            self.configuration.device.maxusb_app.stall_ep0()

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
                self.iclass.class_number,
                self.subclass,
                self.protocol,
                self.string_index
        ])

        # If we have a class object, append its class descriptor...
        if self.iclass:
            descriptor = self.iclass.get_descriptor()
            if descriptor:
                d += descriptor

        # ... append each endpoint's endpoint descriptor.
        for e in self.endpoints:
            d += e.get_descriptor()

        return d

