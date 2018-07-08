# USBInterface.py
#
# Contains class definition for USBInterface.

import struct
from .USB import *
from .USBClass import USBClass
from umap2.fuzz.helpers import mutable

class USBInterface(USBDescribable):
    name = "generic USB interface"

    def __init__(self, phy, interface_number, interface_alternate, interface_class,
            interface_subclass, interface_protocol, interface_string_index,
            verbose=0, endpoints=None, descriptors=None, cs_interfaces=None,
        usb_class=None, usb_vendor=None):
        
        super(USBInterface, self).__init__(phy)
        self.number = interface_number
        self.alternate = interface_alternate

        # Legacy support: if interface_class is an integer, rather than a
        # USBClass object, create a wrapper object for it.
        if isinstance(interface_class, int):
            self.iclass = self._handle_legacy_interface_class(interface_class, descriptors)
        else:
            self.iclass = interface_class

        self.verbose = verbose
        self.subclass = interface_subclass
        self.protocol = interface_protocol
        self.string_index = interface_string_index
        self.usb_class=usb_class
        self.usb_vendor=usb_vendor
        self.endpoints = endpoints if endpoints else []
        self.descriptors = descriptors if descriptors else {}
        self.cs_interfaces = cs_interfaces if cs_interfaces else []
        
        self.descriptors[DescriptorType.interface] = self.get_descriptor
        self.request_handlers = {
             6 : self.handle_get_descriptor_request,
            0xB : self.handle_set_interface_request
        } 
        
        self.configuration = None
        
        if self.iclass and self.iclass.class_descriptor_number:
            descriptor = self.iclass.get_descriptor()

            if descriptor:
                self.descriptors[self.iclass.class_descriptor_number] = descriptor

        '''
        if cendpoints:
            for endpoint in cendpoints:
                self.add_endpoint(endpoint)
        '''
        
        self.usb_class = usb_class
        self.usb_vendor = usb_vendor

        for e in self.endpoints:
            e.interface = self
            if self.usb_class is None:
                self.usb_class = e.usb_class
            if self.usb_vendor is None:
                self.usb_vendor = e.usb_vendor

        if self.usb_class:
            self.usb_class.interface = self
        if self.usb_vendor:
            self.usb_vendor.interface = self 
        
        #self.device_class = None
        #self.device_vendor = None

    def _handle_legacy_interface_class(self, interface_class, descriptors):
        """
        Constructs a USBClass object from a legacy informtion set.
        """

        iclass_desc_num = USB.interface_class_to_descriptor_type(interface_class)

        if iclass_desc_num and descriptors:
            descriptor = descriptors[iclass_desc_num]
        else:
            descriptor = None

        return USBClass(self.phy, interface_class, descriptor, iclass_desc_num)


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
            self.configuration.device.phy.stall_ep0()

        if callable(response):
            response = response(dindex)

        if response:
            n = min(n, len(response))
            self.configuration.device.phy.send_on_endpoint(0, response[:n])

            if self.verbose > 5:
                print(self.name, "sent", n, "bytes in response")

    def handle_set_interface_request(self, req):
        self.configuration.device.phy.stall_ep0()

    # Table 9-12 of USB 2.0 spec (pdf page 296)
    @mutable('interface_descriptor')
    def get_descriptor(self, usb_type='fullspeed', valid=False):

        bLength = 9
        bDescriptorType = DescriptorType.interface
        bNumEndpoints = len(self.endpoints) 
        d = struct.pack(
            "<BBBBBBBBB",
            bLength,  # length of descriptor in bytes
            bDescriptorType,  # descriptor type 4 == interface
            self.number,
            self.alternate,
            bNumEndpoints,
            #self.iclass,
            self.iclass.class_number,
            self.subclass,
            self.protocol,
            self.string_index
        ) 

        #if self.iclass:
        if self.iclass.class_number:
            #iclass_desc_num = USB.interface_class_to_descriptor_type(self.iclass)
            iclass_desc_num = USB.interface_class_to_descriptor_type(self.iclass.class_number)
            if iclass_desc_num:
                desc = self.descriptors[iclass_desc_num]
                if callable(desc):
                    desc = desc()
                d += desc

        for e in self.cs_interfaces:
            d += e.get_descriptor(usb_type, valid)

        for e in self.endpoints:
            d += e.get_descriptor(usb_type, valid)
        return d

