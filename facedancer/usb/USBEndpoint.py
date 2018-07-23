# USBEndpoint.py
#
# Contains class definition for USBEndpoint.

import struct
from .USB import *

class USBEndpoint(USBDescribable):
    name = 'Endpoint'
    DESCRIPTOR_TYPE_NUMBER = DescriptorType.endpoint

    DESCRIPTOR_TYPE_NUMBER      = 0x05

    direction_out               = 0x00
    direction_in                = 0x01

    transfer_type_control       = 0x00
    transfer_type_isochronous   = 0x01
    transfer_type_bulk          = 0x02
    transfer_type_interrupt     = 0x03

    sync_type_none              = 0x00
    sync_type_async             = 0x01
    sync_type_adaptive          = 0x02
    sync_type_synchronous       = 0x03

    usage_type_data             = 0x00
    usage_type_feedback         = 0x01
    usage_type_implicit_feedback = 0x02

    def __init__(self, phy, number, direction, transfer_type, sync_type,
            usage_type, max_packet_size, interval, handler=None, nak_callback=None, cs_endpoints=None,usb_class=None, usb_vendor=None):

        super(USBEndpoint, self).__init__(phy)

        self.number             = number
        self.direction          = direction
        self.transfer_type      = transfer_type
        self.sync_type          = sync_type
        self.usage_type         = usage_type
        self.max_packet_size    = max_packet_size
        self.interval           = interval
        self.handler            = handler
        self.interface          = None
        self.usb_class=usb_class
        self.usb_vendor=usb_vendor
        self.nak_callback       = nak_callback
        self.cs_endpoints = cs_endpoints if cs_endpoints else []
        self.address = (self.number & 0x0f) | (self.direction << 7)

        self.request_handlers   = {
                 0: self.handle_get_status,
                 1: self.handle_clear_feature_request,
        }

    @classmethod
    def from_binary_descriptor(cls, phy, data):
        """
        Creates an endpoint object from a description of that endpoint.
        """
        print("Endpoint")
        # Parse the core descriptor into its components...
        address, attributes, max_packet_size, interval = struct.unpack("xxBBHB", data)

        # ... and break down the packed fields.
        number        = address & 0x7F
        direction     = address >> 7
        transfer_type = attributes & 0b11
        sync_type     = attributes >> 2 & 0b1111
        usage_type    = attributes >> 4 & 0b11

        return cls(phy,number, direction, transfer_type, sync_type, usage_type,
                   max_packet_size, interval)


    def set_handler(self, handler):
        self.handler = handler

    def __repr__(self):
        # TODO: make these nice string representations
        transfer_type = self.transfer_type
        sync_type = self.sync_type
        usage_type = self.usage_type
        direction = "IN" if self.direction else "OUT"

        # TODO: handle high/superspeed; don't assume 1ms frames
        interval = self.interval

        return "<USBEndpoint number={} direction={} transfer_type={} sync_type={} usage_type={} max_packet_size={} inderval={}ms>".format(
            self.number, direction, transfer_type, sync_type, usage_type, self.max_packet_size, interval
        )

    def handle_get_status(self, req):
        self.info('in GET_STATUS of endpoint %d' % self.number)
        self.phy.send_on_endpoint(0, b'\x00\x00')
        
    def handle_clear_feature_request(self, req):
        self.info("received CLEAR_FEATURE request for endpoint %d with value %d", self.number, req.value)
        self.phy.send_on_endpoint(0, b'', False)

    def set_interface(self, interface):
        self.interface = interface

    # see Table 9-13 of USB 2.0 spec (pdf page 297)
    def get_descriptor(self, usb_type='fullspeed', valid=False): 
        attributes = (self.transfer_type & 0x03) \
                   | ((self.sync_type & 0x03) << 2) \
                   | ((self.usage_type & 0x03) << 4)

        bLength = 7
        bDescriptorType = 5
        wMaxPacketSize = self._get_max_packet_size(usb_type) 
        
        d = struct.pack(
            '<BBBBHB',
            bLength,
            bDescriptorType,
            self.address,
            attributes,
            wMaxPacketSize,
            self.interval
        ) 
        
        for cs in self.cs_endpoints:
            d += cs.get_descriptor() 
            
        return d

    def _get_max_packet_size(self, usb_type):
        if usb_type == 'highspeed':
            return self.max_packet_size
        if usb_type == 'lowspeed':
            return 64
        return self.max_packet_size

    def send_packet(self, data, blocking=False):
        dev = self.interface.configuration._device
        dev.phy.send_on_endpoint(self.number, data, blocking=blocking)

    def send(self, data):
        # Send the relevant data one packet at a time,
        # chunking if we're larger than the max packet size.
        # This matches the behavior of the MAX3420E.
        while data:
            packet = data[0:self.max_packet_size]
            data = data[self.max_packet_size:]

            self.send_packet(packet)

    def recv(self):
        dev = self.interface.configuration._device
        data = dev.phy.read_from_endpoint(self.number)
        return data

