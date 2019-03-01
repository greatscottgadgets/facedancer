# USBInterface.py
#
# Contains class definition for USBInterface.

import struct
from .USB import *
from .USBClass import USBClass

class USBCSInterface(USBDescribable):
    name = "CSinterface"
    DESCRIPTOR_TYPE_NUMBER = DescriptorType.cs_interface

    def __init__(self, name, phy, cs_config):
        super(USBCSInterface, self).__init__(phy)
        self.name = name
        self.cs_config = cs_config
        self.descriptors = {}
        self.descriptors[DescriptorType.cs_interface] = self.get_descriptor

        self.request_handlers = {
             6 : self.handle_get_descriptor_request,
            0xb : self.handle_set_interface_request
        }

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
    def from_binary_descriptor(cls, phy, data):
        """
        Creates an endpoint object from a description of that endpoint.
        """
        print("CSInterface")
        # Parse the core descriptor into its components...
        length, descriptor_type = struct.unpack("BB", data[:2])
        cs_config = data[2:length]

        return cls("", phy, cs_config)


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

        self.info(("received GET_DESCRIPTOR at interface req %d, index %d, " \
                    + "language 0x%04x, length %d") \
                    % (dtype, dindex, lang, n))

        # TODO: handle KeyError
        try:
            response = self.descriptors[dtype]
        except KeyError:
            self.phy.stall_ep0()

        if callable(response):
            response = response(dindex)

        if response:
            n = min(n, len(response))
            self.phy.send_on_endpoint(0, response[:n])

            self.verbose("sent", n, "bytes in response")

    def handle_set_interface_request(self, req):
        self.phy.stall_ep0()
        self.info('Received SET_INTERFACE request')

    # Table 9-12 of USB 2.0 spec (pdf page 296)
    def get_descriptor(self, usb_type='fullspeed', valid=False):
        descriptor_type = DescriptorType.cs_interface
        length = len(self.cs_config) + 2
        response = struct.pack('BB', length & 0xff, descriptor_type) + self.cs_config
        return response

